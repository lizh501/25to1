import argparse
import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


DETAIL_RE = re.compile(r"(?P<source>[a-z]+)_(?P<station_id>\d+)\.html$", re.I)


def extract_after_label(soup: BeautifulSoup, label_text: str) -> str:
    th = soup.find("th", string=lambda text: text and label_text in text)
    if th is None:
        return ""
    td = th.find_next("td")
    if td is None:
        return ""
    return td.get_text(" ", strip=True)


def parse_detail_html(path: Path) -> dict:
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    file_match = DETAIL_RE.search(path.name)
    source = file_match.group("source").lower() if file_match else ""
    station_id = file_match.group("station_id") if file_match else ""

    id_match = re.search(r'name="stdStnNo"\s+value="(\d+)"', html)
    if id_match:
        station_id = id_match.group(1)

    station_name_ko = extract_after_label(soup, "지점명(한글)")
    station_name_en = extract_after_label(soup, "지점명(영문)")
    start_date = (
        extract_after_label(soup, "관측시작일")
        or extract_after_label(soup, "관측개시일")
        or extract_after_label(soup, "관측시작")
    )
    elevation_text = extract_after_label(soup, "해발고도(m)")

    coords_match = re.search(r"좌표\(WGS84\).*?위도\s*:\s*([0-9.]+).*?경도\s*:\s*([0-9.]+)", html, re.S)
    if not coords_match:
        raise ValueError(f"Cannot find WGS84 coordinates in {path}")

    return {
        "source": source,
        "station_id": station_id,
        "station_name_ko": station_name_ko,
        "station_name_en": station_name_en,
        "latitude": float(coords_match.group(1)),
        "longitude": float(coords_match.group(2)),
        "elevation_m": float(elevation_text) if elevation_text else None,
        "start_date": start_date,
        "detail_html": str(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a UTF-8 station metadata table from saved KMA station detail pages.")
    parser.add_argument("--detail-dir", default="25to1/data/stage1/interim/kma_station_details")
    parser.add_argument("--output-csv", default="25to1/data/stage1/processed/stations/station_metadata_batch.csv")
    parser.add_argument("--output-json", default="25to1/data/stage1/processed/stations/station_metadata_batch.json")
    parser.add_argument(
        "--invalid-log",
        default="",
        help="Optional path to write skipped HTML files and parse errors.",
    )
    args = parser.parse_args()

    detail_dir = Path(args.detail_dir)
    html_paths = sorted(detail_dir.glob("*.html"))
    if not html_paths:
        raise RuntimeError(f"No HTML files found in {detail_dir.resolve()}")

    rows = []
    invalid_rows = []
    for path in html_paths:
        try:
            rows.append(parse_detail_html(path))
        except Exception as exc:
            invalid_rows.append(
                {
                    "detail_html": str(path),
                    "error": str(exc),
                }
            )

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source",
                "station_id",
                "station_name_ko",
                "station_name_en",
                "latitude",
                "longitude",
                "elevation_m",
                "start_date",
                "detail_html",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    output_json = Path(args.output_json)
    output_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.invalid_log:
        invalid_log = Path(args.invalid_log)
        invalid_log.parent.mkdir(parents=True, exist_ok=True)
        invalid_log.write_text(json.dumps(invalid_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE {output_csv.resolve()}")
    print(f"WROTE {output_json.resolve()}")
    print(f"ROWS {len(rows)}")
    print(f"SKIPPED {len(invalid_rows)}")


if __name__ == "__main__":
    main()
