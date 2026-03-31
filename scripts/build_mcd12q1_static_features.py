import argparse
import json
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
MCD12_PIXELS = 2400
MCD12_PIXEL_SIZE = MODIS_TILE_SIZE_M / MCD12_PIXELS
MODIS_CRS = CRS.from_proj4("+proj=sinu +R=6371007.181 +nadgrids=@null +wktext +units=m +no_defs")
URBAN_CLASS = 13
FILL_VALUE = 255


def load_bbox(config_path: Path) -> list[float]:
    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["region"]["bbox_wgs84"]


def parse_hv(tile: str) -> tuple[int, int]:
    return int(tile[1:3]), int(tile[4:6])


def file_tile(path: Path) -> str:
    return path.name.split(".")[2]


def read_lc_type1(path: Path) -> np.ndarray:
    open_path = path
    if open_path.is_absolute():
        try:
            open_path = open_path.relative_to(Path.cwd())
        except ValueError:
            pass
    hdf = SD(str(open_path), SDC.READ)
    return hdf.select("LC_Type1")[:]


def tile_transform(h: int, v: int, pixel_size: float) -> Affine:
    left = MODIS_XMIN + h * MODIS_TILE_SIZE_M
    top = MODIS_YMAX - v * MODIS_TILE_SIZE_M
    return Affine(pixel_size, 0.0, left, 0.0, -pixel_size, top)


def mosaic_tiles(input_dir: Path) -> tuple[np.ndarray, Affine]:
    tile_to_path = {file_tile(path): path for path in sorted(input_dir.glob("MCD12Q1.A*.hdf"))}
    tile_ids = sorted(tile_to_path)
    hs = sorted({parse_hv(tile)[0] for tile in tile_ids})
    vs = sorted({parse_hv(tile)[1] for tile in tile_ids})
    sample = read_lc_type1(next(iter(tile_to_path.values())))
    out = np.full((len(vs) * sample.shape[0], len(hs) * sample.shape[1]), FILL_VALUE, dtype=sample.dtype)

    for tile, path in tile_to_path.items():
        h, v = parse_hv(tile)
        arr = read_lc_type1(path)
        row = vs.index(v)
        col = hs.index(h)
        y0 = row * arr.shape[0]
        x0 = col * arr.shape[1]
        out[y0:y0 + arr.shape[0], x0:x0 + arr.shape[1]] = arr

    transform = tile_transform(min(hs), min(vs), MCD12_PIXEL_SIZE)
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


def aggregate_to_1km(lc_500m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h = (lc_500m.shape[0] // 2) * 2
    w = (lc_500m.shape[1] // 2) * 2
    arr = lc_500m[:h, :w].reshape(h // 2, 2, w // 2, 2)

    valid = arr != FILL_VALUE
    urban = (arr == URBAN_CLASS) & valid
    valid_count = valid.sum(axis=(1, 3))
    urban_count = urban.sum(axis=(1, 3))

    imp_proxy = np.full(valid_count.shape, -9999.0, dtype=np.float32)
    np.divide(
        urban_count.astype(np.float32),
        valid_count.astype(np.float32),
        out=imp_proxy,
        where=valid_count > 0,
    )
    imp_proxy[valid_count == 0] = -9999.0

    lc_majority = np.full(valid_count.shape, FILL_VALUE, dtype=np.uint8)
    flat = arr.reshape(h // 2, w // 2, 4)
    for i in range(flat.shape[0]):
        for j in range(flat.shape[1]):
            vals = flat[i, j]
            vals = vals[vals != FILL_VALUE]
            if vals.size == 0:
                continue
            counts = np.bincount(vals, minlength=256)
            lc_majority[i, j] = np.argmax(counts[1:18]) + 1

    return imp_proxy, lc_majority


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
    parser = argparse.ArgumentParser(description="Build Korea MCD12Q1 static features and a 1-km urban fraction proxy.")
    parser.add_argument("--input-dir", default="25to1/data/stage1/raw/mcd12q1")
    parser.add_argument("--config", default="25to1/configs/stage1_data_config.example.json")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    config_path = Path(args.config).resolve()
    output_dir = Path(args.output_dir).resolve()
    bbox = load_bbox(config_path)

    lc_500m_full, transform_500m_full = mosaic_tiles(input_dir)
    lc_500m_clip, transform_500m_clip = clip_array(lc_500m_full, transform_500m_full, bbox)
    imp_proxy_1km, lc_majority_1km = aggregate_to_1km(lc_500m_clip)
    transform_1km = transform_500m_clip * Affine.scale(2.0, 2.0)

    write_tif(output_dir / "mcd12q1_lc_type1_korea_500m.tif", lc_500m_clip.astype(np.uint8), transform_500m_clip, "uint8", FILL_VALUE)
    write_tif(output_dir / "mcd12q1_imp_proxy_korea_1km.tif", imp_proxy_1km.astype(np.float32), transform_1km, "float32", -9999.0)
    write_tif(output_dir / "mcd12q1_lc_type1_majority_korea_1km.tif", lc_majority_1km.astype(np.uint8), transform_1km, "uint8", FILL_VALUE)

    valid_imp = imp_proxy_1km[imp_proxy_1km != -9999.0]
    unique_classes = np.unique(lc_500m_clip[lc_500m_clip != FILL_VALUE])
    print(f"lc500m_shape={lc_500m_clip.shape}")
    print(f"imp1km_shape={imp_proxy_1km.shape}")
    print(f"lc_classes={unique_classes.tolist()}")
    print(f"imp_proxy_range=({float(valid_imp.min()):.2f}, {float(valid_imp.max()):.2f})")
    print(f"urban_pixels_500m={(lc_500m_clip == URBAN_CLASS).sum()}")


if __name__ == "__main__":
    main()
