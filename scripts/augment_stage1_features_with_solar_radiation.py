import argparse
import os
import re
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from netCDF4 import Dataset, num2date
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject


WGS84 = CRS.from_epsg(4326)
DAY_NPZ_RE = re.compile(r"^A\d{7}\.npz$")


def openable_path(path: Path) -> Path:
    p = path
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return p


def modis_day_to_date(day: str):
    return datetime.strptime(day[1:], "%Y%j").date()


def build_era5_transform(lons: np.ndarray, lats: np.ndarray):
    lon_res = float(np.median(np.diff(lons)))
    lat_res = float(np.median(np.abs(np.diff(lats))))
    left = float(lons.min() - lon_res / 2.0)
    right = float(lons.max() + lon_res / 2.0)
    bottom = float(lats.min() - lat_res / 2.0)
    top = float(lats.max() + lat_res / 2.0)
    return from_bounds(left, bottom, right, top, len(lons), len(lats))


def load_era5_monthly(path: Path, variable: str):
    ds = Dataset(str(openable_path(path)))
    values = ds.variables[variable][:]
    lats = ds.variables["latitude"][:]
    lons = ds.variables["longitude"][:]
    times = num2date(ds.variables["valid_time"][:], ds.variables["valid_time"].units)
    transform = build_era5_transform(lons, lats)
    date_to_idx = {datetime(t.year, t.month, t.day).date(): i for i, t in enumerate(times)}
    return ds, values, transform, date_to_idx


def load_era5_collection(paths: list[Path], variable: str):
    items = []
    date_index: dict = {}
    for path in paths:
        ds, values, transform, date_to_idx = load_era5_monthly(path, variable)
        item = {
            "path": path,
            "ds": ds,
            "values": values,
            "transform": transform,
            "date_to_idx": date_to_idx,
        }
        items.append(item)
        for dt, idx in date_to_idx.items():
            date_index[dt] = (item, idx)
    return items, date_index


def reproject_to_target(
    source_array: np.ndarray,
    source_crs,
    source_transform,
    target_shape: tuple[int, int],
    target_crs,
    target_transform,
    src_nodata,
    dst_nodata,
    resampling: Resampling,
) -> np.ndarray:
    dst = np.full(target_shape, dst_nodata, dtype=np.float32)
    reproject(
        source=source_array,
        destination=dst,
        src_transform=source_transform,
        src_crs=source_crs,
        src_nodata=src_nodata,
        dst_transform=target_transform,
        dst_crs=target_crs,
        dst_nodata=dst_nodata,
        resampling=resampling,
    )
    return dst


def target_grid_from_lst(day_path: Path):
    with rasterio.open(day_path) as ds:
        return ds.crs, ds.transform, ds.height, ds.width


def save_npz_atomic(path: Path, **payload) -> None:
    tmp_path = path.with_name(path.name + ".tmp.npz")
    np.savez_compressed(tmp_path, **payload)
    last_error = None
    for _ in range(10):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.5)
    raise last_error


def main() -> None:
    parser = argparse.ArgumentParser(description="Add incoming solar radiation features to Stage-1 daily npz stacks.")
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--solar", default="25to1/data/stage1/raw/solar_radiation/era5_daily_ssrd_2018_01.nc")
    parser.add_argument("--solar-dir", default="", help="Optional directory containing monthly solar NetCDF files.")
    parser.add_argument("--solar-glob", default="era5_daily_ssrd_*.nc", help="Glob used with --solar-dir.")
    parser.add_argument("--variable", default="ssrd", help="NetCDF variable name, default: ssrd")
    parser.add_argument("--skip-existing", action="store_true", help="Skip npz files that already contain solar fields.")
    parser.add_argument("--start-day", default="", help="Optional start day like A2018201 for resume runs.")
    args = parser.parse_args()

    features_dir = Path(args.features_dir).resolve()
    daily_dir = Path(args.daily_dir).resolve()
    if args.solar_dir:
        solar_paths = sorted(Path(args.solar_dir).resolve().glob(args.solar_glob))
    else:
        solar_paths = [Path(args.solar).resolve()]
    solar_items, solar_date_index = load_era5_collection(solar_paths, args.variable)

    updated = 0
    failed = 0
    for npz_path in sorted(features_dir.glob("A*.npz")):
        if not DAY_NPZ_RE.match(npz_path.name):
            print(f"SKIP {npz_path.name}: non-standard filename")
            continue

        day = npz_path.stem
        if args.start_day and day < args.start_day:
            continue
        day_date = modis_day_to_date(day)
        if day_date not in solar_date_index:
            print(f"SKIP {day}: no solar match in provided files")
            continue

        lst_day_path = next((daily_dir / day).glob("*_lst_day_c.tif"))
        target_crs, target_transform, target_h, target_w = target_grid_from_lst(lst_day_path)

        solar_item, solar_idx = solar_date_index[day_date]
        solar_day = solar_item["values"][solar_idx, :, :].astype(np.float32)
        solar_j_m2_day = reproject_to_target(
            solar_day,
            WGS84,
            solar_item["transform"],
            (target_h, target_w),
            target_crs,
            target_transform,
            src_nodata=None,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
        solar_w_m2_mean = solar_j_m2_day / 86400.0

        with np.load(npz_path) as old:
            if args.skip_existing and "solar_incoming_j_m2_day" in old.files and "solar_incoming_w_m2" in old.files:
                print(f"SKIP {day}: existing solar fields")
                continue
            # Copy arrays into memory before overwriting the same npz on Windows.
            payload = {key: old[key].copy() for key in old.files}
        payload["solar_incoming_j_m2_day"] = solar_j_m2_day.astype(np.float32)
        payload["solar_incoming_w_m2"] = solar_w_m2_mean.astype(np.float32)
        try:
            save_npz_atomic(npz_path, **payload)
        except PermissionError as exc:
            failed += 1
            print(f"FAIL {day}: {exc}")
            continue
        updated += 1
        print(
            f"UPDATED {day}: "
            f"solar_day_mean={float(np.nanmean(solar_j_m2_day)):.1f} J/m2/day "
            f"solar_flux_mean={float(np.nanmean(solar_w_m2_mean)):.2f} W/m2"
        )

    for item in solar_items:
        item["ds"].close()
    print(f"Done. updated={updated} failed={failed}")


if __name__ == "__main__":
    main()
