import argparse
import json
import re
from datetime import datetime, date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject


DAY_NPZ_RE = re.compile(r"^A\d{7}\.npz$")


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


def load_manifest(path: Path) -> list[dict]:
    p = path
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return json.loads(Path(p).read_text(encoding="utf-8"))


def modis_day_to_date(day: str) -> date:
    return datetime.strptime(day[1:], "%Y%j").date()


def find_ndvi_entry(entries: list[dict], target_date: date) -> dict | None:
    for entry in entries:
        start = date.fromisoformat(entry["start_date"])
        end = date.fromisoformat(entry["end_date"])
        if start <= target_date <= end:
            return entry
    return None

def target_grid_from_lst(day_path: Path):
    with rasterio.open(day_path) as ds:
        return ds.crs, ds.transform, ds.height, ds.width


def main() -> None:
    parser = argparse.ArgumentParser(description="Add NDVI to existing simplified Stage-1 feature stacks.")
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--ndvi-manifest", default="25to1/data/stage1/processed/ndvi_composites/manifest.json")
    args = parser.parse_args()

    features_dir = Path(args.features_dir).resolve()
    daily_dir = Path(args.daily_dir).resolve()
    ndvi_manifest_path = Path(args.ndvi_manifest).resolve()
    ndvi_entries = load_manifest(ndvi_manifest_path)
    data_root = ndvi_manifest_path.parents[3]

    updated = 0
    for npz_path in sorted(features_dir.glob("A*.npz")):
        if not DAY_NPZ_RE.match(npz_path.name):
            print(f"SKIP {npz_path.name}: non-standard filename")
            continue

        day = npz_path.stem
        day_date = modis_day_to_date(day)
        ndvi_entry = find_ndvi_entry(ndvi_entries, day_date)
        if ndvi_entry is None:
            print(f"SKIP {day}: no NDVI composite found")
            continue

        lst_day_path = next((daily_dir / day).glob("*_lst_day_c.tif"))
        target_crs, target_transform, target_h, target_w = target_grid_from_lst(lst_day_path)

        ndvi_path = data_root / ndvi_entry["path"]
        with rasterio.open(ndvi_path) as ds:
            ndvi = ds.read(1).astype(np.float32)
            ndvi = np.where(ndvi == ds.nodata, np.nan, ndvi)
            ndvi_resampled = reproject_to_target(
                ndvi,
                ds.crs,
                ds.transform,
                (target_h, target_w),
                target_crs,
                target_transform,
                src_nodata=np.nan,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )

        old = np.load(npz_path)
        payload = {key: old[key] for key in old.files}
        payload["ndvi"] = ndvi_resampled.astype(np.float32)
        np.savez_compressed(npz_path, **payload)
        updated += 1
        print(f"UPDATED {day}: ndvi_mean={float(np.nanmean(ndvi_resampled)):.4f}")

    print(f"Done. updated={updated}")


if __name__ == "__main__":
    main()
