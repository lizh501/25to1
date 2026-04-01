import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio


DAY_NPZ_RE = re.compile(r"^A\d{7}\.npz$")


def parse_modis_day(day: str) -> datetime:
    return datetime.strptime(day[1:], "%Y%j")


def iter_days(features_dir: Path, day: str, start_day: str) -> list[str]:
    if day:
        return [day]
    days = [
        path.stem
        for path in sorted(features_dir.glob("A*.npz"))
        if DAY_NPZ_RE.match(path.name)
    ]
    if start_day:
        days = [item for item in days if item >= start_day]
    return days


def classify_split(day_date: datetime, split_date: str) -> str:
    return "train" if day_date.date() < datetime.strptime(split_date, "%Y-%m-%d").date() else "test"


def build_records_for_day(
    day: str,
    features_dir: Path,
    labels_dir: Path,
    patch_size: int,
    stride: int,
    min_valid_frac: float,
    split_date: str,
) -> tuple[list[dict], dict]:
    valid_path = labels_dir / day / f"{day}_modis_at_bootstrap_valid.tif"
    label_path = labels_dir / day / f"{day}_modis_at_bootstrap_c.tif"
    npz_path = features_dir / f"{day}.npz"
    if not valid_path.exists() or not label_path.exists() or not npz_path.exists():
        return [], {"day": day, "patches": 0, "skipped": True}

    with rasterio.open(valid_path) as ds:
        valid = ds.read(1).astype(np.uint8)

    height, width = valid.shape
    day_date = parse_modis_day(day)
    split = classify_split(day_date, split_date)
    rows = []
    for row0 in range(0, max(height - patch_size + 1, 1), stride):
        row1 = row0 + patch_size
        if row1 > height:
            continue
        for col0 in range(0, max(width - patch_size + 1, 1), stride):
            col1 = col0 + patch_size
            if col1 > width:
                continue
            patch_valid = valid[row0:row1, col0:col1]
            valid_frac = float(patch_valid.mean())
            if valid_frac < min_valid_frac:
                continue
            rows.append(
                {
                    "day": day,
                    "date": day_date.strftime("%Y-%m-%d"),
                    "split": split,
                    "row0": row0,
                    "row1": row1,
                    "col0": col0,
                    "col1": col1,
                    "patch_size": patch_size,
                    "stride": stride,
                    "valid_frac": valid_frac,
                    "features_npz": str(npz_path),
                    "label_tif": str(label_path),
                    "valid_tif": str(valid_path),
                }
            )

    summary = {
        "day": day,
        "date": day_date.strftime("%Y-%m-%d"),
        "split": split,
        "patches": len(rows),
        "valid_frac_mean": None if not rows else float(np.mean([row["valid_frac"] for row in rows])),
        "valid_frac_min": None if not rows else float(np.min([row["valid_frac"] for row in rows])),
        "valid_frac_max": None if not rows else float(np.max([row["valid_frac"] for row in rows])),
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Stage-1 patch index from bootstrap MODIS-AT surrogate rasters.")
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--labels-dir", default="25to1/data/stage1/processed/modis_at_bootstrap_q1")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/stage1_patch_index_q1")
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--stride", type=int, default=64)
    parser.add_argument("--min-valid-frac", type=float, default=0.5)
    parser.add_argument("--split-date", default="2018-03-01")
    parser.add_argument("--day", default="")
    parser.add_argument("--start-day", default="")
    args = parser.parse_args()

    features_dir = Path(args.features_dir).resolve()
    labels_dir = Path(args.labels_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    day_summaries = []
    for day in iter_days(features_dir, args.day, args.start_day):
        rows, summary = build_records_for_day(
            day=day,
            features_dir=features_dir,
            labels_dir=labels_dir,
            patch_size=args.patch_size,
            stride=args.stride,
            min_valid_frac=args.min_valid_frac,
            split_date=args.split_date,
        )
        all_rows.extend(rows)
        day_summaries.append(summary)
        print(f"DAY {day}: patches={summary['patches']}")

    if not all_rows:
        raise RuntimeError("No patch records were generated.")

    csv_path = output_dir / "stage1_patch_index.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    train_patches = sum(1 for row in all_rows if row["split"] == "train")
    test_patches = sum(1 for row in all_rows if row["split"] == "test")
    summary = {
        "patch_size": args.patch_size,
        "stride": args.stride,
        "min_valid_frac": args.min_valid_frac,
        "split_date": args.split_date,
        "days_indexed": len({row["day"] for row in all_rows}),
        "date_min": min(row["date"] for row in all_rows),
        "date_max": max(row["date"] for row in all_rows),
        "patches_total": len(all_rows),
        "patches_train": train_patches,
        "patches_test": test_patches,
        "feature_source": str(features_dir),
        "label_source": str(labels_dir),
        "index_csv": str(csv_path),
        "day_summaries": day_summaries,
    }
    summary_path = output_dir / "stage1_patch_index_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE {csv_path}")
    print(f"WROTE {summary_path}")


if __name__ == "__main__":
    main()
