import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio


def parse_modis_day(day: str) -> str:
    return datetime.strptime(day[1:], "%Y%j").strftime("%Y-%m-%d")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a manifest.json by scanning existing Stage-1 daily label grids.")
    parser.add_argument("--labels-dir", required=True)
    parser.add_argument("--label-stem", default="modis_at_paperlike")
    args = parser.parse_args()

    labels_dir = Path(args.labels_dir).resolve()
    day_dirs = sorted(path for path in labels_dir.glob("A*") if path.is_dir())
    manifest = []
    for day_dir in day_dirs:
        day = day_dir.name
        pred_path = day_dir / f"{day}_{args.label_stem}_c.tif"
        valid_path = day_dir / f"{day}_{args.label_stem}_valid.tif"
        if not pred_path.exists() or not valid_path.exists():
            continue

        with rasterio.open(pred_path) as ds:
            pred = ds.read(1).astype(np.float32)
            nodata = ds.nodata
        with rasterio.open(valid_path) as ds:
            valid = ds.read(1).astype(np.uint8)

        if nodata is None:
            finite = pred[np.isfinite(pred)]
        else:
            finite = pred[pred != np.float32(nodata)]
        manifest.append(
            {
                "day": day,
                "date": parse_modis_day(day),
                "prediction_tif": str(pred_path),
                "valid_tif": str(valid_path),
                "valid_pixels": int(valid.sum()),
                "clipped_pixels": None,
                "pred_mean_c": None if finite.size == 0 else float(np.nanmean(finite)),
                "pred_min_c": None if finite.size == 0 else float(np.nanmin(finite)),
                "pred_max_c": None if finite.size == 0 else float(np.nanmax(finite)),
            }
        )

    summary = {
        "days_built": len(manifest),
        "output_dir": str(labels_dir),
        "manifest": manifest,
    }
    manifest_path = labels_dir / "manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {manifest_path}")
    print(json.dumps({"days_built": len(manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
