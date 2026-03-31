import argparse
import json
from pathlib import Path

import rasterio
from rasterio.merge import merge
from rasterio.transform import array_bounds
from rasterio.windows import from_bounds


def load_bbox(config_path: Path) -> list[float]:
    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["region"]["bbox_wgs84"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Korea SRTM DEM mosaic clipped to the configured bbox.")
    parser.add_argument(
        "--input-dir",
        default="25to1/data/stage1/raw/srtm/unpacked",
        help="Directory containing extracted .hgt tiles.",
    )
    parser.add_argument(
        "--config",
        default="25to1/configs/stage1_data_config.example.json",
        help="Config JSON containing bbox_wgs84.",
    )
    parser.add_argument(
        "--output",
        default="25to1/data/stage1/processed/srtm_dem_korea_wgs84.tif",
        help="Output DEM GeoTIFF path.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    config_path = Path(args.config).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bbox = load_bbox(config_path)
    min_lon, min_lat, max_lon, max_lat = bbox

    tile_paths = sorted(input_dir.glob("*.hgt"))
    if not tile_paths:
        raise FileNotFoundError(f"No .hgt files found in {input_dir}")

    datasets = [rasterio.open(path) for path in tile_paths]
    try:
        mosaic, transform = merge(datasets)
    finally:
        for ds in datasets:
            ds.close()

    height = mosaic.shape[1]
    width = mosaic.shape[2]
    top = transform.f
    left = transform.c
    right = left + transform.a * width
    bottom = top + transform.e * height

    window = from_bounds(min_lon, min_lat, max_lon, max_lat, transform)
    row_off = max(0, int(window.row_off))
    col_off = max(0, int(window.col_off))
    row_end = min(height, int(window.row_off + window.height))
    col_end = min(width, int(window.col_off + window.width))

    clipped = mosaic[:, row_off:row_end, col_off:col_end]
    clipped_transform = rasterio.windows.transform(
        rasterio.windows.Window(col_off, row_off, col_end - col_off, row_end - row_off),
        transform,
    )

    profile = {
        "driver": "GTiff",
        "height": clipped.shape[1],
        "width": clipped.shape[2],
        "count": clipped.shape[0],
        "dtype": clipped.dtype,
        "crs": "EPSG:4326",
        "transform": clipped_transform,
        "compress": "deflate",
    }

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(clipped)

    bounds = array_bounds(clipped.shape[1], clipped.shape[2], clipped_transform)
    print(f"output={output_path}")
    print(f"shape={clipped.shape}")
    print(f"bounds={bounds}")


if __name__ == "__main__":
    main()
