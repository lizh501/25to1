import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio


NODATA = -9999.0


def parse_modis_day(day: str) -> datetime:
    return datetime.strptime(day[1:], "%Y%j")


def doy365(dt: datetime) -> int | None:
    if dt.month == 2 and dt.day == 29:
        return None
    doy = dt.timetuple().tm_yday
    if is_leap_year(dt.year) and dt.month > 2:
        doy -= 1
    return doy


def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def collect_daily_items(labels_dir: Path, features_dir: Path | None) -> list[dict]:
    items = []
    for day_dir in sorted(path for path in labels_dir.iterdir() if path.is_dir() and path.name.startswith("A")):
        day = day_dir.name
        dt = parse_modis_day(day)
        doy = doy365(dt)
        if doy is None:
            continue

        pred_path = day_dir / f"{day}_modis_at_bootstrap_c.tif"
        valid_path = day_dir / f"{day}_modis_at_bootstrap_valid.tif"
        if not pred_path.exists() or not valid_path.exists():
            continue

        feature_path = features_dir / f"{day}.npz" if features_dir else None
        if features_dir and not feature_path.exists():
            continue

        items.append(
            {
                "day": day,
                "date": dt,
                "doy": doy,
                "pred_path": pred_path,
                "valid_path": valid_path,
                "feature_path": feature_path,
            }
        )
    return items


def load_item_arrays(item: dict) -> dict:
    with rasterio.open(item["pred_path"]) as ds:
        pred = ds.read(1).astype(np.float32)
        profile = ds.profile.copy()
    with rasterio.open(item["valid_path"]) as ds:
        valid = ds.read(1).astype(np.uint8) > 0
    pred = np.where(valid, pred, np.nan)

    era5 = None
    if item["feature_path"] is not None:
        with np.load(item["feature_path"]) as data:
            era5 = data["era5_t2m_c"].astype(np.float32)

    return {
        **item,
        "pred": pred,
        "valid": valid,
        "profile": profile,
        "era5": era5,
    }


def nanmean_stack(stack: np.ndarray) -> np.ndarray:
    valid_counts = np.isfinite(stack).sum(axis=0)
    sums = np.nansum(stack, axis=0)
    out = np.full(stack.shape[1:], np.nan, dtype=np.float32)
    mask = valid_counts > 0
    out[mask] = (sums[mask] / valid_counts[mask]).astype(np.float32)
    return out


def nanstd_stack(stack: np.ndarray) -> np.ndarray:
    mean = nanmean_stack(stack)
    out = np.full(stack.shape[1:], np.nan, dtype=np.float32)
    valid_counts = np.isfinite(stack).sum(axis=0)
    mask = valid_counts > 1
    if not np.any(mask):
        return out
    centered = stack - mean[None, :, :]
    centered[~np.isfinite(stack)] = np.nan
    var = np.nansum(centered**2, axis=0)
    out[mask] = np.sqrt(var[mask] / (valid_counts[mask] - 1)).astype(np.float32)
    return out


def circular_window_indices(center_idx: int, half_window: int, size: int) -> list[int]:
    return [((center_idx + offset) % size) for offset in range(-half_window, half_window + 1)]


def smooth_doy_maps(doy_maps: np.ndarray, window_size: int) -> np.ndarray:
    half_window = max(window_size // 2, 0)
    smoothed = np.full_like(doy_maps, np.nan, dtype=np.float32)
    size = doy_maps.shape[0]
    for idx in range(size):
        indices = circular_window_indices(idx, half_window, size)
        smoothed[idx] = nanmean_stack(doy_maps[indices])
    return smoothed


def fill_missing_with_temporal_neighbors(doy_maps: np.ndarray, window_size: int) -> np.ndarray:
    half_window = max(window_size // 2, 0)
    filled = doy_maps.copy()
    size = filled.shape[0]
    for idx in range(size):
        missing = ~np.isfinite(filled[idx])
        if not np.any(missing):
            continue
        indices = circular_window_indices(idx, half_window, size)
        candidate = nanmean_stack(filled[indices])
        filled[idx][missing] = candidate[missing]
    return filled


def build_doy_climatology(loaded_items: list[dict], smooth_window: int, fill_iterations: int) -> tuple[np.ndarray, dict]:
    first = loaded_items[0]
    height, width = first["pred"].shape
    raw_maps = np.full((365, height, width), np.nan, dtype=np.float32)
    day_counts = np.zeros(365, dtype=np.int32)

    grouped: dict[int, list[np.ndarray]] = {}
    for item in loaded_items:
        grouped.setdefault(item["doy"], []).append(item["pred"])

    for doy in range(1, 366):
        arrays = grouped.get(doy, [])
        if arrays:
            stack = np.stack(arrays, axis=0)
            raw_maps[doy - 1] = nanmean_stack(stack)
            day_counts[doy - 1] = len(arrays)

    smoothed = smooth_doy_maps(raw_maps, smooth_window)
    filled = smoothed.copy()
    for _ in range(fill_iterations):
        filled = fill_missing_with_temporal_neighbors(filled, smooth_window)
        filled = smooth_doy_maps(filled, smooth_window)

    summary = {
        "doy_with_raw_observations": int((day_counts > 0).sum()),
        "raw_day_counts": day_counts.tolist(),
        "smooth_window": smooth_window,
        "fill_iterations": fill_iterations,
    }
    return filled, summary


def build_era5_calendar_stats(loaded_items: list[dict]) -> tuple[np.ndarray | None, np.ndarray | None]:
    era5_items = [item for item in loaded_items if item["era5"] is not None]
    if not era5_items:
        return None, None

    first = era5_items[0]
    height, width = first["era5"].shape
    mean_maps = np.full((365, height, width), np.nan, dtype=np.float32)
    std_maps = np.full((365, height, width), np.nan, dtype=np.float32)

    grouped: dict[int, list[np.ndarray]] = {}
    for item in era5_items:
        grouped.setdefault(item["doy"], []).append(item["era5"])

    for doy in range(1, 366):
        arrays = grouped.get(doy, [])
        if not arrays:
            continue
        stack = np.stack(arrays, axis=0)
        mean_maps[doy - 1] = nanmean_stack(stack)
        std_maps[doy - 1] = nanstd_stack(stack)
    return mean_maps, std_maps


def standardize_with_era5(climatology_maps: np.ndarray, era5_mean: np.ndarray | None, era5_std: np.ndarray | None) -> np.ndarray:
    if era5_mean is None or era5_std is None:
        return climatology_maps
    out = np.full_like(climatology_maps, np.nan, dtype=np.float32)
    valid = np.isfinite(climatology_maps) & np.isfinite(era5_mean) & np.isfinite(era5_std) & (era5_std > 0)
    out[valid] = ((climatology_maps[valid] - era5_mean[valid]) / era5_std[valid]).astype(np.float32)
    return out


def write_doy_rasters(output_dir: Path, maps: np.ndarray, profile: dict, stem_prefix: str) -> list[dict]:
    manifest = []
    pred_profile = profile.copy()
    pred_profile.update(dtype="float32", nodata=NODATA, count=1, compress="deflate")

    for doy in range(1, 366):
        arr = maps[doy - 1].copy()
        valid = np.isfinite(arr)
        arr[~valid] = NODATA
        doy_dir = output_dir / f"doy_{doy:03d}"
        doy_dir.mkdir(parents=True, exist_ok=True)
        out_path = doy_dir / f"{stem_prefix}_doy_{doy:03d}.tif"
        with rasterio.open(out_path, "w", **pred_profile) as dst:
            dst.write(arr.astype(np.float32), 1)
        manifest.append(
            {
                "doy": doy,
                "path": str(out_path),
                "valid_pixels": int(valid.sum()),
                "mean": float(np.nanmean(maps[doy - 1])) if np.any(valid) else None,
                "min": float(np.nanmin(maps[doy - 1])) if np.any(valid) else None,
                "max": float(np.nanmax(maps[doy - 1])) if np.any(valid) else None,
            }
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a paper-like Stage-1 SCM scaffold from long-timeseries MODIS-AT daily rasters."
    )
    parser.add_argument("--labels-dir", required=True, help="Daily MODIS-AT label directory with AYYYYDDD subfolders.")
    parser.add_argument("--features-dir", default="", help="Optional simplified-feature directory for ERA5 calendar-day standardization.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--smooth-window", type=int, default=11)
    parser.add_argument("--fill-iterations", type=int, default=10)
    parser.add_argument(
        "--output-mode",
        choices=["climatology", "anomaly_standardized", "both"],
        default="both",
        help="Whether to write raw climatology maps, ERA5-standardized maps, or both.",
    )
    args = parser.parse_args()

    labels_dir = Path(args.labels_dir).resolve()
    features_dir = Path(args.features_dir).resolve() if args.features_dir else None
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    items = collect_daily_items(labels_dir, features_dir)
    if not items:
        raise RuntimeError(f"No daily label items found in {labels_dir}")

    loaded_items = [load_item_arrays(item) for item in items]
    climatology_maps, climatology_summary = build_doy_climatology(
        loaded_items,
        smooth_window=args.smooth_window,
        fill_iterations=args.fill_iterations,
    )
    era5_mean, era5_std = build_era5_calendar_stats(loaded_items)
    anomaly_maps = standardize_with_era5(climatology_maps, era5_mean, era5_std)

    profile = loaded_items[0]["profile"]
    manifest = {
        "labels_dir": str(labels_dir),
        "features_dir": str(features_dir) if features_dir else None,
        "daily_items": len(loaded_items),
        "date_min": loaded_items[0]["date"].strftime("%Y-%m-%d"),
        "date_max": loaded_items[-1]["date"].strftime("%Y-%m-%d"),
        "climatology_summary": climatology_summary,
        "outputs": {},
    }

    if args.output_mode in {"climatology", "both"}:
        climatology_dir = output_dir / "climatology_365"
        manifest["outputs"]["climatology_365"] = write_doy_rasters(climatology_dir, climatology_maps, profile, "scm_climatology")
    if args.output_mode in {"anomaly_standardized", "both"}:
        anomaly_dir = output_dir / "anomaly_standardized_365"
        manifest["outputs"]["anomaly_standardized_365"] = write_doy_rasters(
            anomaly_dir,
            anomaly_maps,
            profile,
            "scm_anomaly_standardized",
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"WROTE {manifest_path}")


if __name__ == "__main__":
    main()
