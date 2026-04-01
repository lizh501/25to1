import argparse
import csv
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_keep_items(values: list[str]) -> set[tuple[str, str]]:
    keep: set[tuple[str, str]] = set()
    for value in values:
        if ":" not in value:
            raise ValueError(f"Expected source:station_id, got {value}")
        source, station_id = value.split(":", 1)
        keep.add((source.strip(), station_id.strip()))
    return keep


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a combined subset station-metadata CSV for selected source/station pairs.")
    parser.add_argument("--inputs", nargs="+", required=True, help="One or more metadata CSV files.")
    parser.add_argument("--keep", nargs="+", required=True, help="Pairs like asos:108 aws:116")
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    keep_pairs = parse_keep_items(args.keep)
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in args.inputs:
        for row in load_rows(Path(item)):
            key = (row["source"], row["station_id"])
            if key in keep_pairs and key not in seen:
                rows.append(row)
                seen.add(key)

    missing = sorted(keep_pairs - seen)
    if missing:
        raise RuntimeError(f"Missing requested metadata rows: {missing}")

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"WROTE {output_csv.resolve()}")
    print(f"ROWS {len(rows)}")


if __name__ == "__main__":
    main()
