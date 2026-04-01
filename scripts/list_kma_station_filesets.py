import argparse
import csv
import re
from pathlib import Path

import requests

from download_kma_station_fileset import (
    SOURCE_CONFIG,
    fetch_with_retry,
    login,
    parse_fileset_values,
    resolve_input_path,
)
from stage1_common import load_env_file


FILE_RE = re.compile(
    r"^SURFACE_(?P<source>ASOS|AWS)_(?P<station_id>\d+)_(?P<frequency>DAY|HR|MI)_(?P<start>[\d-]+)_(?P<end>[\d-]+)_.+"
)


def parse_file_record(page_idx: int, value: str) -> dict | None:
    parts = value.split("^")
    if len(parts) != 4:
        return None
    file_size_mb, fileset_sn, file_path, fileset_dtl_sn = parts
    file_name = Path(file_path).name
    match = FILE_RE.match(file_name)
    record = {
        "page_index": page_idx,
        "file_size_mb": file_size_mb,
        "fileset_sn": fileset_sn,
        "fileset_dtl_sn": fileset_dtl_sn,
        "file_path": file_path,
        "file_name": file_name,
        "source": "",
        "station_id": "",
        "frequency": "",
        "start_token": "",
        "end_token": "",
    }
    if match:
        record.update(
            {
                "source": match.group("source").lower(),
                "station_id": match.group("station_id"),
                "frequency": match.group("frequency").lower(),
                "start_token": match.group("start"),
                "end_token": match.group("end"),
            }
        )
    return record


def collect_filesets(session: requests.Session, source: str, max_pages: int) -> list[dict]:
    page_url = SOURCE_CONFIG[source]["page_url"]
    records: list[dict] = []
    for page_idx in range(1, max_pages + 1):
        response = fetch_with_retry(
            session,
            "GET",
            f"{page_url}&pageIndex={page_idx}",
            timeout=60,
        )
        values = parse_fileset_values(response.text)
        if not values:
            break
        for value in values:
            record = parse_file_record(page_idx, value)
            if record:
                records.append(record)
    return records


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="List available KMA ASOS/AWS filesets from the official portal.")
    parser.add_argument("--source", choices=sorted(SOURCE_CONFIG.keys()), required=True)
    parser.add_argument("--env-file", default="25to1/configs/stage1_credentials.example.env")
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    env_path = resolve_input_path(args.env_file)
    load_env_file(env_path)

    import os

    username = os.environ.get("KMA_USERNAME")
    password = os.environ.get("KMA_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing KMA_USERNAME / KMA_PASSWORD in environment")

    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    login(session, username, password)
    records = collect_filesets(session, args.source, args.max_pages)

    output_csv = Path(args.output_csv).resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output_csv, records)

    unique_station_ids = sorted({row["station_id"] for row in records if row["station_id"]})
    print(f"WROTE {output_csv}")
    print(f"ROWS {len(records)}")
    print(f"UNIQUE_STATIONS {len(unique_station_ids)}")
    if unique_station_ids:
        print("STATION_IDS " + ",".join(unique_station_ids[:50]))


if __name__ == "__main__":
    main()
