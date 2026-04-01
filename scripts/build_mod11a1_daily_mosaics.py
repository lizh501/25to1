import argparse
import json
from collections import defaultdict
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
    for path in sorted(input_dir.glob("MOD11A1.A*.hdf")):
        day, tile = file_day_tile(path)
        grouped[day][tile] = path
    return grouped


def read_sds(path: Path, name: str) -> tuple[np.ndarray, dict]:
    open_path = path
    if open_path.is_absolute():
        try:
            open_path = open_path.relative_to(Path.cwd())
        except ValueError:
            pass
    hdf = SD(str(open_path), SDC.READ)
    sds = hdf.select(name)
    data = sds[:]
    attrs = sds.attributes()
    return data, attrs


def tile_transform(h: int, v: int) -> Affine:
    left = MODIS_XMIN + h * MODIS_TILE_SIZE_M
    top = MODIS_YMAX - v * MODIS_TILE_SIZE_M
    return Affine(MODIS_PIXEL_SIZE, 0.0, left, 0.0, -MODIS_PIXEL_SIZE, top)


def mosaic_tiles(tile_to_path: dict[str, Path], sds_name: str) -> tuple[np.ndarray, Affine, dict]:
    tile_ids = sorted(tile_to_path)
    hs = sorted({parse_hv(tile)[0] for tile in tile_ids})
    vs = sorted({parse_hv(tile)[1] for tile in tile_ids})

    sample, attrs = read_sds(next(iter(tile_to_path.values())), sds_name)
    out = np.full((len(vs) * sample.shape[0], len(hs) * sample.shape[1]), 0, dtype=sample.dtype)

    for tile, path in tile_to_path.items():
        h, v = parse_hv(tile)
        arr, _ = read_sds(path, sds_name)
        row = vs.index(v)
        col = hs.index(h)
        y0 = row * arr.shape[0]
        x0 = col * arr.shape[1]
        out[y0:y0 + arr.shape[0], x0:x0 + arr.shape[1]] = arr

    transform = tile_transform(min(hs), min(vs))
    return out, transform, attrs


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


def convert_lst_to_celsius(raw: np.ndarray, attrs: dict) -> np.ndarray:
    fill_value = attrs.get("_FillValue", 0)
    scale_factor = attrs.get("scale_factor", 0.02)
    out = raw.astype(np.float32)
    out = np.where(out == fill_value, np.nan, out * scale_factor - 273.15)
    return out


def write_tif(path: Path, arr: np.ndarray, transform: Affine, dtype: str, nodata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=arr.shape[0],
        width=arr.shape[1],
        count=1,
        dtype=dtype,
        crs=MODIS_CRS,
        transform=transform,
        nodata=nodata,
        compress="deflate",
    ) as dst:
        dst.write(arr, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily MOD11A1 mosaics for Korea bootstrap data.")
    parser.add_argument("--input-dir", default="25to1/data/stage1/raw/mod11a1")
    parser.add_argument("--config", default="25to1/configs/stage1_data_config.example.json")
    parser.add_argument("--output-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--day", default="", help="Optional single day like A2018001")
    parser.add_argument("--start-day", default="", help="Optional inclusive start day like A2018032")
    parser.add_argument("--skip-existing", action="store_true", help="Skip days whose output rasters already exist.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    config_path = Path(args.config).resolve()
    output_dir = Path(args.output_dir).resolve()
    bbox = load_bbox(config_path)
    grouped = group_files(input_dir)

    days = [args.day] if args.day else sorted(grouped)
    if args.start_day:
        days = [day for day in days if day >= args.start_day]
    built = 0
    skipped = 0
    for day in days:
        tile_map = grouped.get(day, {})
        if len(tile_map) != 3:
            skipped += 1
            print(f"SKIP {day}: expected 3 tiles, got {len(tile_map)}")
            continue

        day_dir = output_dir / day
        expected_outputs = [
            day_dir / f"{day}_lst_day_c.tif",
            day_dir / f"{day}_qc_day.tif",
            day_dir / f"{day}_lst_night_c.tif",
            day_dir / f"{day}_qc_night.tif",
        ]
        if args.skip_existing and all(path.exists() for path in expected_outputs):
            skipped += 1
            print(f"SKIP {day}: existing outputs")
            continue

        raw_day, transform, day_attrs = mosaic_tiles(tile_map, "LST_Day_1km")
        qc_day, _, _ = mosaic_tiles(tile_map, "QC_Day")
        raw_night, _, night_attrs = mosaic_tiles(tile_map, "LST_Night_1km")
        qc_night, _, _ = mosaic_tiles(tile_map, "QC_Night")

        day_c = convert_lst_to_celsius(raw_day, day_attrs)
        night_c = convert_lst_to_celsius(raw_night, night_attrs)

        day_c, day_transform = clip_array(day_c, transform, bbox)
        qc_day, qc_day_transform = clip_array(qc_day, transform, bbox)
        night_c, night_transform = clip_array(night_c, transform, bbox)
        qc_night, qc_night_transform = clip_array(qc_night, transform, bbox)

        write_tif(day_dir / f"{day}_lst_day_c.tif", np.where(np.isfinite(day_c), day_c, -9999).astype(np.float32), day_transform, "float32", -9999)
        write_tif(day_dir / f"{day}_qc_day.tif", qc_day.astype(np.uint8), qc_day_transform, "uint8", 255)
        write_tif(day_dir / f"{day}_lst_night_c.tif", np.where(np.isfinite(night_c), night_c, -9999).astype(np.float32), night_transform, "float32", -9999)
        write_tif(day_dir / f"{day}_qc_night.tif", qc_night.astype(np.uint8), qc_night_transform, "uint8", 255)

        built += 1
        print(
            f"BUILT {day}: shape={day_c.shape} "
            f"day_mean={float(np.nanmean(day_c)):.2f}C night_mean={float(np.nanmean(night_c)):.2f}C"
        )

    print(f"Done. built={built} skipped={skipped} output_dir={output_dir}")


if __name__ == "__main__":
    main()
