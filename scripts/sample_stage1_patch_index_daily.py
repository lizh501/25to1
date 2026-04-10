import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample a Stage-1 patch index with a fixed within-day stride.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--keep-every", type=int, default=20)
    args = parser.parse_args()

    input_csv = Path(args.input_csv).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = sorted(reader, key=lambda row: (row["day"], int(row["row0"]), int(row["col0"])))
        fieldnames = list(reader.fieldnames or [])

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["day"]].append(row)

    sampled = []
    day_summaries = []
    for day in sorted(grouped):
        items = grouped[day]
        kept = items[:: args.keep_every]
        sampled.extend(kept)
        train_count = sum(1 for row in kept if row["split"] == "train")
        test_count = sum(1 for row in kept if row["split"] == "test")
        day_summaries.append(
            {
                "day": day,
                "patches_original": len(items),
                "patches_sampled": len(kept),
                "patches_train": train_count,
                "patches_test": test_count,
            }
        )

    csv_path = output_dir / "stage1_patch_index.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sampled)

    summary = {
        "source_csv": str(input_csv),
        "index_csv": str(csv_path),
        "patches_total": len(sampled),
        "patches_train": sum(1 for row in sampled if row["split"] == "train"),
        "patches_test": sum(1 for row in sampled if row["split"] == "test"),
        "days_indexed": len(grouped),
        "date_min": min(row["date"] for row in sampled),
        "date_max": max(row["date"] for row in sampled),
        "sampling_rule": f"keep every {args.keep_every}th patch within each day after sorting by day,row0,col0",
        "day_summaries": day_summaries,
    }
    summary_path = output_dir / "stage1_patch_index_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {csv_path}")
    print(f"WROTE {summary_path}")


if __name__ == "__main__":
    main()
