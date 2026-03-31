import argparse
import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


def extract_after_label(soup: BeautifulSoup, label_text: str) -> str:
    th = soup.find("th", string=lambda text: text and label_text in text)
    if th is None:
        return ""
    td = th.find_next("td")
    if td is None:
        return ""
    return td.get_text(" ", strip=True)


def parse_detail_html(path: Path, source: str) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    std_stn_no_match = re.search(r'name="stdStnNo" value="(\d+)"', path.read_text(encoding="utf-8"))
    if not std_stn_no_match:
        raise ValueError(f"Cannot find stdStnNo in {path}")

    station_id = std_stn_no_match.group(1)
    station_name = extract_after_label(soup, "지점명(한글)")
    station_name_en = extract_after_label(soup, "지점명(영문)")
    start_date = extract_after_label(soup, "관측개시일")
    elevation_text = extract_after_label(soup, "해발고도(m)")

    coords_match = re.search(
        r"위도\s*:\s*([0-9.]+).*?경도\s*:\s*([0-9.]+)",
        path.read_text(encoding="utf-8"),
        re.S,
    )
    if not coords_match:
        raise ValueError(f"Cannot find WGS84 coordinates in {path}")

    return {
        "source": source,
        "station_id": station_id,
        "station_name_ko": station_name,
        "station_name_en": station_name_en,
        "latitude": float(coords_match.group(1)),
        "longitude": float(coords_match.group(2)),
        "elevation_m": float(elevation_text) if elevation_text else None,
        "start_date": start_date,
        "detail_html": str(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compact KMA station metadata table from saved detail pages.")
    parser.add_argument("--asos-detail", default="25to1/data/stage1/interim/stn_detail_100.html")
    parser.add_argument("--aws-detail", default="25to1/data/stage1/interim/stn_detail_116.html")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/stations")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        parse_detail_html(Path(args.asos_detail).resolve(), "asos"),
        parse_detail_html(Path(args.aws_detail).resolve(), "aws"),
    ]

    csv_path = output_dir / "station_metadata_bootstrap.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
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

    json_path = output_dir / "station_metadata_bootstrap.json"
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE {csv_path}")
    print(f"WROTE {json_path}")
    for row in rows:
        print(
            f"{row['source']} station_id={row['station_id']} "
            f"lat={row['latitude']:.5f} lon={row['longitude']:.5f}"
        )


if __name__ == "__main__":
    main()
