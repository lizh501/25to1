import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio


NODATA = -9999.0


def parse_modis_day(day: str) -> datetime:
    return datetime.strptime(day[1:], "%Y%j")


def collect_daily_paths(labels_dir: Path) -> list[tuple[str, Path, Path]]:
    items = []
    for day_dir in sorted(path for path in labels_dir.iterdir() if path.is_dir() and path.name.startswith("A")):
        pred_path = day_dir / f"{day_dir.name}_modis_at_bootstrap_c.tif"
        valid_path = day_dir / f"{day_dir.name}_modis_at_bootstrap_valid.tif"
        if pred_path.exists() and valid_path.exists():
            items.append((day_dir.name, pred_path, valid_path))
    return items


def load_daily_arrays(items: list[tuple[str, Path, Path]]) -> list[dict]:
    loaded = []
    for day, pred_path, valid_path in items:
        with rasterio.open(pred_path) as ds:
            pred = ds.read(1).astype(np.float32)
            profile = ds.profile.copy()
        with rasterio.open(valid_path) as ds:
            valid = ds.read(1).astype(np.uint8) > 0
        pred = np.where(valid, pred, np.nan)
        loaded.append(
            {
                "day": day,
                "date": parse_modis_day(day),
                "pred": pred,
                "valid": valid,
                "profile": profile,
            }
        )
    return loaded


def write_raster(path: Path, array: np.ndarray, profile: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array, 1)


def summarize_and_write(out_dir: Path, stem: str, scm: np.ndarray, valid_mask: np.ndarray, profile: dict) -> tuple[Path, Path, dict]:
    pred_out = out_dir / f"{stem}_scm_bootstrap_c.tif"
    valid_out = out_dir / f"{stem}_scm_bootstrap_valid.tif"

    pred_profile = profile.copy()
    pred_profile.update(dtype="float32", nodata=NODATA, count=1, compress="deflate")
    valid_profile = profile.copy()
    valid_profile.update(dtype="uint8", nodata=0, count=1, compress="deflate")

    write_raster(pred_out, scm, pred_profile)
    write_raster(valid_out, valid_mask.astype(np.uint8), valid_profile)

    finite = np.where(scm == NODATA, np.nan, scm)
    summary = {
        "path": str(pred_out),
        "valid_path": str(valid_out),
        "mean_c": float(np.nanmean(finite)),
        "min_c": float(np.nanmin(finite)),
        "max_c": float(np.nanmax(finite)),
        "valid_pixels": int(valid_mask.sum()),
    }
    return pred_out, valid_out, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a bootstrap SCM approximation from daily pseudo-label rasters.")
    parser.add_argument("--labels-dir", default="25to1/data/stage1/processed/modis_at_bootstrap_q1_janfebtrain")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/scm_bootstrap_q1_janfebtrain")
    parser.add_argument("--mode", choices=["monthly", "rolling"], default="monthly")
    parser.add_argument("--window-days", type=int, default=15, help="Used only when --mode rolling.")
    args = parser.parse_args()

    labels_dir = Path(args.labels_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    items = collect_daily_paths(labels_dir)
    loaded = load_daily_arrays(items)

    manifest = []
    if args.mode == "monthly":
        grouped = {}
        for item in loaded:
            grouped.setdefault(item["date"].strftime("%Y-%m"), []).append(item)

        for month_key, month_items in sorted(grouped.items()):
            sum_arr = np.zeros_like(month_items[0]["pred"], dtype=np.float64)
            count_arr = np.zeros_like(month_items[0]["pred"], dtype=np.uint16)
            for item in month_items:
                finite = np.isfinite(item["pred"])
                sum_arr[finite] += item["pred"][finite]
                count_arr[finite] += 1

            scm = np.full(sum_arr.shape, NODATA, dtype=np.float32)
            valid_month = count_arr > 0
            scm[valid_month] = (sum_arr[valid_month] / count_arr[valid_month]).astype(np.float32)

            out_dir = output_dir / month_key.replace("-", "_")
            _, _, summary = summarize_and_write(out_dir, month_key.replace("-", "_"), scm, valid_month, month_items[0]["profile"])
            summary.update({"month": month_key, "days_used": len(month_items)})
            manifest.append(summary)
            print(
                f"BUILT {month_key}: "
                f"days={len(month_items)} valid_pixels={summary['valid_pixels']} "
                f"mean_c={summary['mean_c']:.2f}"
            )
    else:
        half_window = max(args.window_days // 2, 0)
        for idx, item in enumerate(loaded):
            start = max(0, idx - half_window)
            end = min(len(loaded), idx + half_window + 1)
            win_items = loaded[start:end]
            sum_arr = np.zeros_like(item["pred"], dtype=np.float64)
            count_arr = np.zeros_like(item["pred"], dtype=np.uint16)
            for win_item in win_items:
                finite = np.isfinite(win_item["pred"])
                sum_arr[finite] += win_item["pred"][finite]
                count_arr[finite] += 1

            scm = np.full(sum_arr.shape, NODATA, dtype=np.float32)
            valid_day = count_arr > 0
            scm[valid_day] = (sum_arr[valid_day] / count_arr[valid_day]).astype(np.float32)

            day = item["day"]
            out_dir = output_dir / day
            _, _, summary = summarize_and_write(out_dir, day, scm, valid_day, item["profile"])
            summary.update(
                {
                    "day": day,
                    "date": item["date"].strftime("%Y-%m-%d"),
                    "window_days": len(win_items),
                }
            )
            manifest.append(summary)
            print(
                f"BUILT {day}: "
                f"window={len(win_items)} valid_pixels={summary['valid_pixels']} "
                f"mean_c={summary['mean_c']:.2f}"
            )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {manifest_path}")


if __name__ == "__main__":
    main()
