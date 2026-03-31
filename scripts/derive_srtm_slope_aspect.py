import argparse
from pathlib import Path

import numpy as np
import rasterio


EARTH_RADIUS_M = 6371007.181


def compute_metrics(dem: np.ndarray, transform) -> tuple[np.ndarray, np.ndarray]:
    z = dem.astype(np.float32)
    pixel_deg_x = transform.a
    pixel_deg_y = abs(transform.e)
    height, width = z.shape

    row_indices = np.arange(height, dtype=np.float32)
    lat_centers = transform.f + (row_indices + 0.5) * transform.e
    meters_per_deg_lat = (2.0 * np.pi * EARTH_RADIUS_M) / 360.0
    meters_per_deg_lon = meters_per_deg_lat * np.cos(np.deg2rad(lat_centers))

    dx_m = np.maximum(meters_per_deg_lon * pixel_deg_x, 1e-6)
    dy_m = max(meters_per_deg_lat * pixel_deg_y, 1e-6)

    dz_dy = np.gradient(z, axis=0) / dy_m
    dz_dx = np.gradient(z, axis=1) / dx_m[:, None]

    slope = np.degrees(np.arctan(np.sqrt(dz_dx ** 2 + dz_dy ** 2))).astype(np.float32)

    # 0=N, 90=E, 180=S, 270=W
    aspect = (np.degrees(np.arctan2(dz_dx, -dz_dy)) + 360.0) % 360.0
    aspect = aspect.astype(np.float32)

    return slope, aspect


def write_geotiff(path: Path, arr: np.ndarray, profile: dict, nodata: float) -> None:
    profile = dict(profile)
    profile.update(dtype="float32", count=1, nodata=nodata, compress="deflate")
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype(np.float32), 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive slope and aspect from the Korea SRTM DEM.")
    parser.add_argument(
        "--dem",
        default="25to1/data/stage1/processed/srtm_dem_korea_wgs84.tif",
        help="Input DEM GeoTIFF.",
    )
    parser.add_argument(
        "--slope-output",
        default="25to1/data/stage1/processed/srtm_slope_korea_wgs84.tif",
        help="Output slope GeoTIFF.",
    )
    parser.add_argument(
        "--aspect-output",
        default="25to1/data/stage1/processed/srtm_aspect_korea_wgs84.tif",
        help="Output aspect GeoTIFF.",
    )
    args = parser.parse_args()

    dem_path = Path(args.dem).resolve()
    slope_path = Path(args.slope_output).resolve()
    aspect_path = Path(args.aspect_output).resolve()
    slope_path.parent.mkdir(parents=True, exist_ok=True)
    aspect_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(dem_path) as src:
        dem = src.read(1)
        profile = src.profile
        transform = src.transform
        nodata = src.nodata

    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)

    slope, aspect = compute_metrics(dem, transform)
    slope = np.where(np.isfinite(slope), slope, -9999).astype(np.float32)
    aspect = np.where(np.isfinite(aspect), aspect, -9999).astype(np.float32)

    write_geotiff(slope_path, slope, profile, -9999)
    write_geotiff(aspect_path, aspect, profile, -9999)

    print(f"slope={slope_path}")
    print(f"aspect={aspect_path}")
    print(f"slope_range=({float(np.nanmin(np.where(slope == -9999, np.nan, slope))):.3f}, {float(np.nanmax(np.where(slope == -9999, np.nan, slope))):.3f})")
    print(f"aspect_range=({float(np.nanmin(np.where(aspect == -9999, np.nan, aspect))):.3f}, {float(np.nanmax(np.where(aspect == -9999, np.nan, aspect))):.3f})")


if __name__ == "__main__":
    main()
