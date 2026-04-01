import argparse
import csv
import os
from pathlib import Path

import requests

from download_kma_station_fileset import (
    SOURCE_CONFIG,
    decode_purpose_labels,
    download_fileset,
    extract_nested_zip,
    login,
    request_purpose_popup,
    resolve_input_path,
    search_matching_fileset,
)
from stage1_common import load_env_file


def load_station_ids(path: Path, source: str) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    station_ids = []
    for row in rows:
        if row.get("source") != source:
            continue
        station_id = str(row["station_id"]).strip()
        if station_id and station_id not in station_ids:
            station_ids.append(station_id)
    return station_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-download KMA station filesets by station ID.")
    parser.add_argument("--source", choices=sorted(SOURCE_CONFIG.keys()), required=True)
    parser.add_argument("--stations-csv", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--frequency", choices=["day", "hr", "mi"], default="day")
    parser.add_argument("--month", type=int, default=0)
    parser.add_argument("--purpose-code", default="F00408")
    parser.add_argument("--env-file", default="25to1/configs/stage1_credentials.example.env")
    parser.add_argument("--output-dir", default="25to1/data/stage1/raw/stations")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    env_path = resolve_input_path(args.env_file)
    load_env_file(env_path)
    username = os.environ.get("KMA_USERNAME")
    password = os.environ.get("KMA_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing KMA_USERNAME / KMA_PASSWORD in environment")

    month = args.month or None
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    station_ids = load_station_ids(Path(args.stations_csv).resolve(), args.source)
    if args.limit > 0:
        station_ids = station_ids[: args.limit]

    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    login(session, username, password)

    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    for idx, station_id in enumerate(station_ids, start=1):
        target_prefix = f"SURFACE_{args.source.upper()}_{station_id}_{args.frequency.upper()}_{args.year:04d}_"
        existing_zip = next(output_dir.glob(f"{target_prefix}*.zip"), None)
        if args.skip_existing and existing_zip is not None:
            print(f"SKIP {idx}/{len(station_ids)} station_id={station_id} existing={existing_zip.name}")
            skipped.append(station_id)
            continue

        try:
            fileset_value = search_matching_fileset(
                session=session,
                source=args.source,
                station_id=station_id,
                frequency=args.frequency,
                year=args.year,
                month=month,
            )
            popup_payload, popup_html = request_purpose_popup(session, fileset_value)
            labels = decode_purpose_labels(popup_html)
            if not any(value == args.purpose_code for value, _ in labels):
                raise RuntimeError(f"Purpose code {args.purpose_code} not available for station_id={station_id}")

            response = download_fileset(session, popup_payload, args.purpose_code)
            file_name = Path(popup_payload["fileCoursNms"]).name
            outer_zip = output_dir / file_name
            outer_zip.write_bytes(response.content)

            if args.extract:
                extract_dir = output_dir / f"{args.source}_{args.frequency}_{args.year:04d}"
                if month is not None:
                    extract_dir = output_dir / f"{args.source}_{args.frequency}_{args.year:04d}_{month:02d}"
                extract_nested_zip(outer_zip, extract_dir)

            print(f"OK {idx}/{len(station_ids)} station_id={station_id} file={file_name}")
            succeeded.append(station_id)
        except Exception as exc:
            print(f"FAIL {idx}/{len(station_ids)} station_id={station_id} error={exc}")
            failed.append((station_id, str(exc)))
            try:
                login(session, username, password)
            except Exception:
                session = requests.Session()
                session.trust_env = False
                session.headers.update({"User-Agent": "Mozilla/5.0"})
                login(session, username, password)

    print(f"SUMMARY succeeded={len(succeeded)} skipped={len(skipped)} failed={len(failed)}")
    if failed:
        for station_id, error in failed[:20]:
            print(f"FAILED_STATION {station_id} {error}")


if __name__ == "__main__":
    main()
