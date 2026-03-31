import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyhdf.SD import SD, SDC
from rasterio.crs import CRS
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds


MODIS_TILE_SIZE_M = 1111950.5196666666
MODIS_XMIN = -20015109.354
MODIS_YMAX = 10007554.677
MODIS_PIXELS = 1200
MODIS_PIXEL_SIZE = MODIS_TILE_SIZE_M / MODIS_PIXELS
MODIS_CRS = CRS.from_proj4("+proj=sinu +R=6371007.181 +nadgrids=@null +wktext +units=m +no_defs")
NDVI_FILL = -3000


def load_bbox(config_path: Path) -> list[float]:
    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["region"]["bbox_wgs84"]


def parse_hv(tile: str) -> tuple[int, int]:
    return int(tile[1:3]), int(tile[4:6])


def file_day_tile(path: Path) -> tuple[str, str]:
    parts = path.name.split(".")
    return parts[1], parts[2]


def group_files(input_dir: Path) -> dict[str, dict[str, Path]]:
    grouped: dict[str, dict[str, Path]] = defaultdict(dict)
    for path in sorted(input_dir.glob("MOD13A2.A*.hdf")):
        day, tile = file_day_tile(path)
        grouped[day][tile] = path
    return grouped


def openable_path(path: Path) -> Path:
    p = path
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return p


def read_ndvi(path: Path) -> np.ndarray:
    hdf = SD(str(openable_path(path)), SDC.READ)
    arr = hdf.select("1 km 16 days NDVI")[:].astype(np.float32)
    arr = np.where(arr == NDVI_FILL, np.nan, arr / 10000.0)
    return arr


def tile_transform(h: int, v: int) -> Affine:
    left = MODIS_XMIN + h * MODIS_TILE_SIZE_M
    top = MODIS_YMAX - v * MODIS_TILE_SIZE_M
    return Affine(MODIS_PIXEL_SIZE, 0.0, left, 0.0, -MODIS_PIXEL_SIZE, top)


def mosaic_tiles(tile_to_path: dict[str, Path]) -> tuple[np.ndarray, Affine]:
    tile_ids = sorted(tile_to_path)
    hs = sorted({parse_hv(tile)[0] for tile in tile_ids})
    vs = sorted({parse_hv(tile)[1] for tile in tile_ids})
    sample = read_ndvi(next(iter(tile_to_path.values())))
    out = np.full((len(vs) * sample.shape[0], len(hs) * sample.shape[1]), np.nan, dtype=np.float32)

    for tile, path in tile_to_path.items():
        h, v = parse_hv(tile)
        arr = read_ndvi(path)
        row = vs.index(v)
        col = hs.index(h)
        y0 = row * arr.shape[0]
        x0 = col * arr.shape[1]
        out[y0:y0 + arr.shape[0], x0:x0 + arr.shape[1]] = arr

    transform = tile_transform(min(hs), min(vs))
    return out, transform


def clip_array(arr: np.ndarray, transform: Affine, bbox_wgs84: list[float]) -> tuple[np.ndarray, Affine]:
    left, bottom, right, top = transform_bounds(CRS.from_epsg(4326), MODIS_CRS, *bbox_wgs84, densify_pts=21)
    window = from_bounds(left, bottom, right, top, transform)
    row_off = max(0, int(np.floor(window.row_off)))
    col_off = max(0, int(np.floor(window.col_off)))
    row_end = min(arr.shape[0], int(np.ceil(window.row_off + window.height)))
    col_end = min(arr.shape[1], int(np.ceil(window.col_off + window.width)))
    clipped = arr[row_off:row_end, col_off:col_end]
    clipped_transform = rasterio.windows.transform(
        rasterio.windows.Window(col_off, row_off, col_end - col_off, row_end - row_off),
        transform,
    )
    return clipped, clipped_transform


def write_tif(path: Path, arr: np.ndarray, transform: Affine) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = np.where(np.isfinite(arr), arr, -9999).astype(np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=out.shape[0],
        width=out.shape[1],
        count=1,
        dtype="float32",
        crs=MODIS_CRS,
        transform=transform,
        nodata=-9999.0,
        compress="deflate",
    ) as dst:
        dst.write(out, 1)


def day_code_to_date(day_code: str) -> datetime:
    return datetime.strptime(day_code[1:], "%Y%j")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Korea-clipped MOD13A2 NDVI composites.")
    parser.add_argument("--input-dir", default="25to1/data/stage1/raw/ndvi")
    parser.add_argument("--config", default="25to1/configs/stage1_data_config.example.json")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/ndvi_composites")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    config_path = Path(args.config).resolve()
    output_dir = Path(args.output_dir).resolve()
    bbox = load_bbox(config_path)
    grouped = group_files(input_dir)

    manifest = []
    for day_code in sorted(grouped):
        tile_map = grouped[day_code]
        if len(tile_map) != 3:
            print(f"SKIP {day_code}: expected 3 tiles, got {len(tile_map)}")
            continue
        arr, transform = mosaic_tiles(tile_map)
        arr, transform = clip_array(arr, transform, bbox)
        out_path = output_dir / f"{day_code}_ndvi.tif"
        write_tif(out_path, arr, transform)

        start = day_code_to_date(day_code).date()
        end = (day_code_to_date(day_code) + timedelta(days=15)).date()
        valid = arr[np.isfinite(arr)]
        manifest.append(
            {
                "day_code": day_code,
                "start_date": str(start),
                "end_date": str(end),
                "path": str(out_path.relative_to(output_dir.parent.parent.parent)),
                "shape": [int(arr.shape[0]), int(arr.shape[1])],
                "ndvi_mean": float(valid.mean()) if valid.size else None,
            }
        )
        print(f"BUILT {day_code}: shape={arr.shape} ndvi_mean={float(valid.mean()):.4f}")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Done. composites={len(manifest)} manifest={manifest_path}")


if __name__ == "__main__":
    main()
