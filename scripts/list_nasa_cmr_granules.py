import argparse
import json
from datetime import datetime
from pathlib import Path

import requests

from stage1_common import load_env_file


CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"


def iso_start(date_text: str) -> str:
    return datetime.fromisoformat(date_text).strftime("%Y-%m-%dT00:00:00Z")


def iso_end(date_text: str) -> str:
    return datetime.fromisoformat(date_text).strftime("%Y-%m-%dT23:59:59Z")


def choose_download_url(entry: dict) -> str | None:
    preferred_suffixes = (".hdf", ".h5", ".nc", ".nc4", ".tif", ".tiff")
    fallback_urls = []
    for link in entry.get("links", []):
        href = link.get("href")
        inherited = link.get("inherited", False)
        rel = link.get("rel", "")
        if inherited or not href:
            continue
        href_lower = href.lower()
        if href_lower.endswith(preferred_suffixes):
            return href
        if "data#" in rel and not href_lower.endswith((".jpg", ".jpeg", ".png", ".xml")):
            fallback_urls.append(href)
    if fallback_urls:
        return fallback_urls[0]
    return None


def fetch_cmr_page(params: dict) -> dict:
    response = requests.get(
        CMR_GRANULES_URL,
        params=params,
        timeout=60,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def fetch_all_entries(base_params: dict) -> list[dict]:
    page_num = 1
    all_entries = []
    while True:
        params = dict(base_params)
        params["page_num"] = page_num
        payload = fetch_cmr_page(params)
        entries = payload.get("feed", {}).get("entry", [])
        if not entries:
            break
        all_entries.extend(entries)
        if len(entries) < int(base_params["page_size"]):
            break
        page_num += 1
    return all_entries


def main() -> None:
    parser = argparse.ArgumentParser(description="List NASA CMR granules for a product and time window.")
    parser.add_argument("--short-name", required=True, help="Product short name, e.g. MOD11A1 or MCD12Q1.")
    parser.add_argument("--version", default="061", help="Product version, default 061.")
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--tiles", default="", help="Comma-separated MODIS tiles, e.g. h27v05,h28v05,h29v05")
    parser.add_argument("--bbox", default="", help="Optional W,S,E,N bounding box for non-MODIS products.")
    parser.add_argument("--provider", default="", help="Optional CMR provider filter.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument(
        "--env-file",
        default="25to1/configs/stage1_credentials.example.env",
        help="Optional env file. Used for consistency; listing does not require credentials.",
    )
    args = parser.parse_args()

    load_env_file(Path(args.env_file).resolve())

    params = {
        "short_name": args.short_name,
        "version": args.version,
        "temporal": f"{iso_start(args.start_date)},{iso_end(args.end_date)}",
        "page_size": 2000,
    }
    if args.provider:
        params["provider"] = args.provider
    if args.bbox:
        params["bounding_box"] = args.bbox

    entries = fetch_all_entries(params)
    tile_filters = {tile.strip() for tile in args.tiles.split(",") if tile.strip()}

    records = []
    for entry in entries:
        granule_id = entry.get("producer_granule_id", "")
        if tile_filters and not any(tile in granule_id for tile in tile_filters):
            continue
        records.append(
            {
                "granule_id": granule_id,
                "time_start": entry.get("time_start"),
                "time_end": entry.get("time_end"),
                "download_url": choose_download_url(entry),
            }
        )

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Product: {args.short_name} v{args.version}")
    print(f"Granules written: {len(records)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
