import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform


def date_to_modis_day(date_text: str) -> str:
    dt = datetime.strptime(date_text, "%Y-%m-%d")
    return dt.strftime("A%Y%j")


def load_station_metadata(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_station_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_station_rows_from_paths(paths: list[Path]) -> dict[str, list[dict]]:
    tables: dict[str, list[dict]] = {}
    for path in paths:
        rows = load_station_rows(path)
        if not rows:
            continue
        source = rows[0]["source"]
        tables.setdefault(source, []).extend(rows)
    return tables


def target_rowcol(lst_day_path: Path, lon: float, lat: float) -> tuple[int, int]:
    with rasterio.open(lst_day_path) as ds:
        xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
        row, col = ds.index(xs[0], ys[0])
        return int(row), int(col)


def sample_npz_loaded(data, row: int, col: int) -> dict:
    out = {}
    for key in data.files:
        value = data[key]
        item = value[row, col]
        if np.issubdtype(value.dtype, np.integer):
            out[key] = int(item)
        else:
            out[key] = None if not np.isfinite(item) else float(item)
    return out


def sample_npz(npz_path: Path, row: int, col: int) -> dict:
    data = np.load(npz_path)
    return sample_npz_loaded(data, row, col)


def coerce_float(text: str) -> float | None:
    if text is None:
        return None
    text = text.strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_records(
    metadata_rows: list[dict],
    station_tables: dict[str, list[dict]],
    features_dir: Path,
    daily_dir: Path,
) -> list[dict]:
    day_dirs = sorted(path for path in daily_dir.iterdir() if path.is_dir())
    if not day_dirs:
        raise RuntimeError(f"No daily directories found in {daily_dir}")
    reference_lst_day_path = next(day_dirs[0].glob("*_lst_day_c.tif"))

    pixel_lookup: dict[tuple[str, str], tuple[int, int]] = {}
    meta_lookup: dict[tuple[str, str], dict] = {}
    rows_by_source_station: dict[tuple[str, str], list[dict]] = {}
    rows_by_day: dict[str, list[tuple[dict, dict]]] = {}

    for meta in metadata_rows:
        key = (meta["source"], meta["station_id"])
        meta_lookup[key] = meta
        pixel_lookup[key] = target_rowcol(reference_lst_day_path, float(meta["longitude"]), float(meta["latitude"]))

    for rows in station_tables.values():
        for row in rows:
            key = (row["source"], row["station_id"])
            rows_by_source_station.setdefault(key, []).append(row)

    for key, rows in rows_by_source_station.items():
        if key not in meta_lookup:
            continue
        meta = meta_lookup[key]
        for row in rows:
            modis_day = date_to_modis_day(row["date"])
            rows_by_day.setdefault(modis_day, []).append((meta, row))

    records = []

    for modis_day in sorted(rows_by_day.keys()):
        npz_path = features_dir / f"{modis_day}.npz"
        day_dir = daily_dir / modis_day
        if not npz_path.exists() or not day_dir.exists():
            continue
        data = np.load(npz_path)

        for meta, row in rows_by_day[modis_day]:
            source = meta["source"]
            station_id = meta["station_id"]
            px_row, px_col = pixel_lookup[(source, station_id)]
            features = sample_npz_loaded(data, px_row, px_col)
            record = {
                "source": source,
                "station_id": station_id,
                "station_name_ko": meta["station_name_ko"],
                "date": row["date"],
                "modis_day": modis_day,
                "latitude": float(meta["latitude"]),
                "longitude": float(meta["longitude"]),
                "elevation_m": float(meta["elevation_m"]) if meta["elevation_m"] else None,
                "pixel_row": px_row,
                "pixel_col": px_col,
                "station_avg_temp_c": coerce_float(row.get("avg_temp_c", "")),
                "station_min_temp_c": coerce_float(row.get("min_temp_c", "")),
                "station_max_temp_c": coerce_float(row.get("max_temp_c", "")),
                "station_daily_precip_mm": coerce_float(row.get("daily_precip_mm", "")),
            }
            if "mean_relative_humidity_pct" in row:
                record["station_mean_relative_humidity_pct"] = coerce_float(row.get("mean_relative_humidity_pct", ""))
            if "mean_station_pressure_hpa" in row:
                record["station_mean_station_pressure_hpa"] = coerce_float(row.get("mean_station_pressure_hpa", ""))
            if "sum_solar_mj_m2" in row:
                record["station_sum_solar_mj_m2"] = coerce_float(row.get("sum_solar_mj_m2", ""))
            if "mean_wind_speed_m_s" in row:
                record["station_mean_wind_speed_m_s"] = coerce_float(row.get("mean_wind_speed_m_s", ""))
            if "max_instant_wind_speed_m_s" in row:
                record["station_max_instant_wind_speed_m_s"] = coerce_float(row.get("max_instant_wind_speed_m_s", ""))

            record.update(features)
            records.append(record)

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build station-to-grid collocation samples for Stage-1 bootstrap.")
    parser.add_argument("--station-meta", default="25to1/data/stage1/processed/stations/station_metadata_bootstrap.csv")
    parser.add_argument("--asos", default="25to1/data/stage1/processed/stations/SURFACE_ASOS_100_DAY_2018_2018_2019_normalized.csv")
    parser.add_argument("--aws", default="25to1/data/stage1/processed/stations/SURFACE_AWS_116_DAY_2018_2018_2019_normalized.csv")
    parser.add_argument("--station-csvs", nargs="*", default=None, help="Optional explicit list of normalized station CSV files.")
    parser.add_argument("--station-csv-dir", default=None, help="Optional directory containing normalized station CSV files.")
    parser.add_argument("--station-csv-glob", default="*_normalized.csv", help="Glob used with --station-csv-dir.")
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/station_collocations")
    args = parser.parse_args()

    metadata_rows = load_station_metadata(Path(args.station_meta).resolve())
    if args.station_csvs:
        station_paths = [Path(item).resolve() for item in args.station_csvs]
    elif args.station_csv_dir:
        station_paths = sorted(Path(args.station_csv_dir).resolve().glob(args.station_csv_glob))
    else:
        station_paths = [Path(args.asos).resolve(), Path(args.aws).resolve()]
    station_tables = load_station_rows_from_paths(station_paths)

    records = build_records(
        metadata_rows,
        station_tables,
        Path(args.features_dir).resolve(),
        Path(args.daily_dir).resolve(),
    )

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "stage1_station_collocations_2018_01.csv"
    if not records:
        raise RuntimeError("No collocation records were built.")

    fieldnames = []
    for record in records:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    summary = {
        "rows": len(records),
        "sources": sorted({row["source"] for row in records}),
        "date_min": min(row["date"] for row in records),
        "date_max": max(row["date"] for row in records),
        "station_ids": sorted({row["station_id"] for row in records}),
        "output_csv": str(csv_path),
    }
    json_path = output_dir / "stage1_station_collocations_2018_01_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE {csv_path}")
    print(f"WROTE {json_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
