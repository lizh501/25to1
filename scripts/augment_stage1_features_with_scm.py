import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject


DAY_NPZ_RE = re.compile(r"^A\d{7}\.npz$")


def modis_day_to_date(day: str):
    return datetime.strptime(day[1:], "%Y%j").date()


def month_key_from_day(day: str) -> str:
    return modis_day_to_date(day).strftime("%Y-%m")


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
    last_error = None
    for attempt in range(1, 11):
        try:
            np.savez_compressed(tmp_path, **payload)
            os.replace(tmp_path, path)
            return
        except PermissionError as exc:
            last_error = exc
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except PermissionError:
                    pass
            time.sleep(0.5 * attempt)
    raise PermissionError(f"Failed to replace {path} after retries: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add bootstrap SCM to existing simplified Stage-1 feature stacks.")
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--scm-manifest", default="25to1/data/stage1/processed/scm_bootstrap_q1_janfebtrain/manifest.json")
    parser.add_argument("--start-day", default="", help="Optional resume day like A2018182.")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    features_dir = Path(args.features_dir).resolve()
    daily_dir = Path(args.daily_dir).resolve()
    manifest_path = Path(args.scm_manifest).resolve()
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    month_map = {entry["month"]: entry for entry in entries if "month" in entry}
    day_map = {entry["day"]: entry for entry in entries if "day" in entry}

    updated = 0
    failed = 0
    for npz_path in sorted(features_dir.glob("A*.npz")):
        if not DAY_NPZ_RE.match(npz_path.name):
            print(f"SKIP {npz_path.name}: non-standard filename")
            continue

        day = npz_path.stem
        if args.start_day and day < args.start_day:
            continue

        if day in day_map:
            entry = day_map[day]
        else:
            month_key = month_key_from_day(day)
            entry = month_map.get(month_key)
        if entry is None:
            print(f"SKIP {day}: no SCM map found")
            continue

        lst_day_path = next((daily_dir / day).glob("*_lst_day_c.tif"))
        target_crs, target_transform, target_h, target_w = target_grid_from_lst(lst_day_path)

        with np.load(npz_path) as old:
            if args.skip_existing and "scm_bootstrap_c" in old.files:
                print(f"SKIP {day}: existing scm field")
                continue
            payload = {key: old[key].copy() for key in old.files}

        with rasterio.open(Path(entry["path"])) as ds:
            scm = ds.read(1).astype(np.float32)
            scm = np.where(scm == ds.nodata, np.nan, scm)
            scm_resampled = reproject_to_target(
                scm,
                ds.crs,
                ds.transform,
                (target_h, target_w),
                target_crs,
                target_transform,
                src_nodata=np.nan,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )

        payload["scm_bootstrap_c"] = scm_resampled.astype(np.float32)
        try:
            save_npz_atomic(npz_path, **payload)
        except PermissionError as exc:
            failed += 1
            print(f"FAIL {day}: {exc}")
            continue

        updated += 1
        print(f"UPDATED {day}: scm_mean={float(np.nanmean(scm_resampled)):.2f}C")

    print(f"Done. updated={updated} failed={failed}")


if __name__ == "__main__":
    main()
