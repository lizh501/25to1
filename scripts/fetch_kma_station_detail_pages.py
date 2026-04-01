import argparse
import csv
import time
from pathlib import Path

import requests

from download_kma_station_fileset import fetch_with_retry


DETAIL_URL = "https://data.kma.go.kr/tmeta/stn/selectStnDetail.do"


def load_station_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fetch_detail_html(session: requests.Session, station_id: str) -> str:
    response = fetch_with_retry(
        session,
        "GET",
        DETAIL_URL,
        params={"pgmNo": "82", "isSelectStn": "Y", "stdStnNo": str(station_id)},
        timeout=60,
    )
    return response.text


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public KMA station detail pages for a list of station IDs.")
    parser.add_argument("--stations-csv", required=True)
    parser.add_argument("--output-dir", default="25to1/data/stage1/interim/kma_station_details")
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for quick bootstrap runs.")
    args = parser.parse_args()

    rows = load_station_rows(Path(args.stations_csv).resolve())
    if args.limit > 0:
        rows = rows[: args.limit]
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    for row in rows:
        source = row.get("source", "").strip() or "unknown"
        station_id = str(row["station_id"]).strip()
        output_path = output_dir / f"{source}_{station_id}.html"
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"SKIP {output_path.name}")
            continue
        html = fetch_detail_html(session, station_id)
        output_path.write_text(html, encoding="utf-8")
        print(f"WROTE {output_path}")
        time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
