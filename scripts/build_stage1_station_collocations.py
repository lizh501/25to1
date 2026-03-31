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


def target_rowcol(lst_day_path: Path, lon: float, lat: float) -> tuple[int, int]:
    with rasterio.open(lst_day_path) as ds:
        xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
        row, col = ds.index(xs[0], ys[0])
        return int(row), int(col)


def sample_npz(npz_path: Path, row: int, col: int) -> dict:
    data = np.load(npz_path)
    out = {}
    for key in data.files:
        value = data[key]
        item = value[row, col]
        if np.issubdtype(value.dtype, np.integer):
            out[key] = int(item)
        else:
            out[key] = None if not np.isfinite(item) else float(item)
    return out


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
    station_lookup = {(row["source"], row["station_id"]): row for rows in station_tables.values() for row in rows}
    records = []

    for meta in metadata_rows:
        source = meta["source"]
        station_id = meta["station_id"]
        rows = station_tables[source]
        lon = float(meta["longitude"])
        lat = float(meta["latitude"])

        for row in rows:
            if row["station_id"] != station_id:
                continue

            modis_day = date_to_modis_day(row["date"])
            npz_path = features_dir / f"{modis_day}.npz"
            day_dir = daily_dir / modis_day
            if not npz_path.exists() or not day_dir.exists():
                continue

            lst_day_path = next(day_dir.glob("*_lst_day_c.tif"))
            px_row, px_col = target_rowcol(lst_day_path, lon, lat)
            features = sample_npz(npz_path, px_row, px_col)
            record = {
                "source": source,
                "station_id": station_id,
                "station_name_ko": meta["station_name_ko"],
                "date": row["date"],
                "modis_day": modis_day,
                "latitude": lat,
                "longitude": lon,
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
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/station_collocations")
    args = parser.parse_args()

    metadata_rows = load_station_metadata(Path(args.station_meta).resolve())
    station_tables = {
        "asos": load_station_rows(Path(args.asos).resolve()),
        "aws": load_station_rows(Path(args.aws).resolve()),
    }

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
