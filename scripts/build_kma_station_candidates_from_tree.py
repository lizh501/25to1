import argparse
import csv
import json
import re
from pathlib import Path


LEAF_RE = re.compile(r'name\s*:\s*"(?P<label>[^"]+)\s*",\s*stnNm\s*:\s*"(?P<name>[^"]*)"\s*,\s*stnId\s*:\s*"(?P<station_id>\d+)"')


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract KMA station candidate IDs from a saved station-group tree HTML snippet.")
    parser.add_argument("--tree-html", required=True)
    parser.add_argument("--source", required=True, help="Source label to stamp into output rows, e.g. aws or asos.")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    tree_path = Path(args.tree_html).resolve()
    html = tree_path.read_text(encoding="utf-8")

    rows = []
    seen = set()
    for match in LEAF_RE.finditer(html):
        station_id = match.group("station_id")
        if station_id == "0" or station_id in seen:
            continue
        seen.add(station_id)
        rows.append(
            {
                "source": args.source,
                "station_id": station_id,
                "station_name_hint": match.group("name"),
                "label": match.group("label"),
            }
        )

    output_csv = Path(args.output_csv).resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    output_json = Path(args.output_json).resolve() if args.output_json else output_csv.with_suffix(".json")
    output_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE {output_csv}")
    print(f"WROTE {output_json}")
    print(f"ROWS {len(rows)}")


if __name__ == "__main__":
    main()
