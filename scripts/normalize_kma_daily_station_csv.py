import argparse
import csv
import json
from pathlib import Path


ASOS_FIELD_MAP = {
    "지점": "station_id",
    "일시": "date",
    "평균기온(°C)": "avg_temp_c",
    "최저기온(°C)": "min_temp_c",
    "최저기온 시각(hhmi)": "min_temp_time_hhmi",
    "최고기온(°C)": "max_temp_c",
    "최고기온 시각(hhmi)": "max_temp_time_hhmi",
    "일강수량(mm)": "daily_precip_mm",
    "평균 풍속(m/s)": "mean_wind_speed_m_s",
    "평균 상대습도(%)": "mean_relative_humidity_pct",
    "평균 현지기압(hPa)": "mean_station_pressure_hpa",
    "합계 일사(MJ/m2)": "sum_solar_mj_m2",
}

AWS_FIELD_MAP = {
    "지점": "station_id",
    "일시": "date",
    "평균기온(°C)": "avg_temp_c",
    "최저기온(°C)": "min_temp_c",
    "최저기온 시각(hhmi)": "min_temp_time_hhmi",
    "최고기온(°C)": "max_temp_c",
    "최고기온 시각(hhmi)": "max_temp_time_hhmi",
    "일강수량(mm)": "daily_precip_mm",
    "최대 순간 풍속(m/s)": "max_instant_wind_speed_m_s",
    "최대 순간풍속 시각(hhmi)": "max_instant_wind_time_hhmi",
    "평균 풍속(m/s)": "mean_wind_speed_m_s",
    "최대 순간 풍속 풍향(deg)": "max_instant_wind_dir_deg",
}

OPTIONAL_SOURCE_FIELDS = {
    "asos": {"합계 일사(MJ/m2)"},
    "aws": set(),
}


def detect_source(path: Path) -> str:
    name = path.name.upper()
    if "ASOS" in name:
        return "asos"
    if "AWS" in name:
        return "aws"
    raise ValueError(f"Cannot infer source from filename: {path.name}")


def normalize_csv(input_path: Path, output_dir: Path) -> dict:
    source = detect_source(input_path)
    field_map = ASOS_FIELD_MAP if source == "asos" else AWS_FIELD_MAP
    optional_fields = OPTIONAL_SOURCE_FIELDS.get(source, set())

    with input_path.open("r", encoding="cp949", newline="") as src:
        reader = csv.DictReader(src)
        missing = [name for name in field_map if name not in reader.fieldnames and name not in optional_fields]
        if missing:
            raise KeyError(f"Missing expected columns in {input_path.name}: {missing}")

        output_path = output_dir / f"{input_path.stem}_normalized.csv"
        output_dir.mkdir(parents=True, exist_ok=True)
        fieldnames = ["source"] + list(field_map.values())
        rows = 0

        with output_path.open("w", encoding="utf-8", newline="") as dst:
            writer = csv.DictWriter(dst, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                out = {"source": source}
                for src_name, dst_name in field_map.items():
                    out[dst_name] = row.get(src_name, "") if src_name in reader.fieldnames else ""
                writer.writerow(out)
                rows += 1

    return {
        "source": source,
        "input_csv": str(input_path),
        "output_csv": str(output_path),
        "rows": rows,
        "columns": fieldnames,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize downloaded KMA daily station CSV files into UTF-8 core tables.")
    parser.add_argument("--input", nargs="*", default=[], help="One or more KMA daily CSV files.")
    parser.add_argument(
        "--input-dir",
        nargs="*",
        default=[],
        help="One or more directories to scan recursively for CSV files.",
    )
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/stations")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    inputs = [Path(item).resolve() for item in args.input]
    for item in args.input_dir:
        inputs.extend(sorted(Path(item).resolve().rglob("*.csv")))
    inputs = sorted({path for path in inputs if path.suffix.lower() == ".csv"})
    if not inputs:
        raise RuntimeError("No input CSV files were provided.")

    manifest = []
    for input_path in inputs:
        meta = normalize_csv(input_path, output_dir)
        manifest.append(meta)
        print(f"NORMALIZED {input_path.name}: rows={meta['rows']} -> {meta['output_csv']}")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"MANIFEST {manifest_path}")


if __name__ == "__main__":
    main()
