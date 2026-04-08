import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from normalize_kma_daily_station_csv import normalize_csv


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    return (Path(__file__).resolve().parents[2] / path).resolve()


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_metadata_subset(metadata_master: Path, station_ids: list[str], output_csv: Path) -> dict:
    meta = pd.read_csv(metadata_master, dtype={"station_id": str})
    subset = meta[meta["station_id"].isin(station_ids)].drop_duplicates(["source", "station_id"]).copy()
    subset = subset.sort_values(["source", "station_id"]).reset_index(drop=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(output_csv, index=False, encoding="utf-8")
    return {
        "rows": int(len(subset)),
        "station_ids": subset["station_id"].astype(str).tolist(),
        "output_csv": str(output_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an incremental Stage-1 AWS expansion chunk: download, normalize, subset metadata, and merge collocations."
    )
    parser.add_argument("--metadata-master", default="25to1/data/stage1/processed/stations/station_metadata_aws576.csv")
    parser.add_argument("--stations-csv", default="25to1/data/stage1/processed/stations/station_metadata_aws576.csv")
    parser.add_argument("--year", type=int, default=2018)
    parser.add_argument("--frequency", choices=["day", "hr", "mi"], default="day")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--run-name", default="")
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--download-output-dir", default="25to1/data/stage1/raw/stations")
    parser.add_argument("--env-file", default="25to1/configs/stage1_credentials.example.env")
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--merge-existing-csv", default="")
    parser.add_argument("--collocation-output-dir", required=True)
    parser.add_argument("--runs-root", default="25to1/data/stage1/processed/aws_incremental_runs")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-normalize", action="store_true")
    parser.add_argument("--skip-collocation", action="store_true")
    args = parser.parse_args()

    python_exe = resolve_path(args.python_exe) if args.python_exe.lower().endswith(".exe") or ":" in args.python_exe else Path(args.python_exe)
    run_name = args.run_name or f"aws_y{args.year}_{args.frequency}_offset{args.offset}_limit{args.limit}"
    runs_root = resolve_path(args.runs_root)
    run_dir = runs_root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    download_result_json = run_dir / "download_result.json"
    normalized_dir = run_dir / "normalized"
    metadata_subset_csv = run_dir / "station_metadata_subset.csv"
    summary_json = run_dir / "pipeline_summary.json"

    if not args.skip_download:
        download_command = [
            str(python_exe),
            str(resolve_path("25to1/scripts/download_kma_station_batch.py")),
            "--source",
            "aws",
            "--stations-csv",
            str(resolve_path(args.stations_csv)),
            "--year",
            str(args.year),
            "--frequency",
            args.frequency,
            "--extract",
            "--skip-existing",
            "--offset",
            str(args.offset),
            "--limit",
            str(args.limit),
            "--env-file",
            str(resolve_path(args.env_file)),
            "--output-dir",
            str(resolve_path(args.download_output_dir)),
            "--result-json",
            str(download_result_json),
        ]
        run_command(download_command)
    elif not download_result_json.exists():
        raise RuntimeError(f"Missing prior download result JSON: {download_result_json}")

    download_result = load_json(download_result_json)
    selected_station_ids = sorted(
        {
            *download_result.get("succeeded", []),
            *download_result.get("skipped", []),
        }
    )
    if not selected_station_ids:
        raise RuntimeError("No succeeded or skipped station IDs found for this chunk.")

    metadata_summary = build_metadata_subset(resolve_path(args.metadata_master), selected_station_ids, metadata_subset_csv)

    raw_csv_dir = resolve_path(args.download_output_dir) / f"aws_{args.frequency}_{args.year:04d}"
    raw_csv_paths = []
    missing_raw_station_ids = []
    for station_id in selected_station_ids:
        path = raw_csv_dir / f"SURFACE_AWS_{station_id}_{args.frequency.upper()}_{args.year:04d}_{args.year:04d}_{args.year + 1:04d}.csv"
        if path.exists():
            raw_csv_paths.append(path)
        else:
            missing_raw_station_ids.append(station_id)

    normalized_manifest = []
    if not args.skip_normalize:
        normalized_dir.mkdir(parents=True, exist_ok=True)
        for input_path in raw_csv_paths:
            output_path = normalized_dir / f"{input_path.stem}_normalized.csv"
            if output_path.exists() and output_path.stat().st_size > 0:
                normalized_manifest.append(
                    {
                        "source": "aws",
                        "input_csv": str(input_path),
                        "output_csv": str(output_path),
                        "rows": None,
                        "skipped_existing": True,
                    }
                )
                continue
            normalized_manifest.append(normalize_csv(input_path, normalized_dir))
        write_json(run_dir / "normalized_manifest.json", {"files": normalized_manifest})
    elif not normalized_dir.exists():
        raise RuntimeError(f"Missing normalized directory for skip-normalize run: {normalized_dir}")

    normalized_paths = sorted(normalized_dir.glob("SURFACE_AWS_*_normalized.csv"))
    if not normalized_paths:
        raise RuntimeError("No normalized AWS station CSVs found for this chunk.")

    collocation_output_dir = resolve_path(args.collocation_output_dir)
    if not args.skip_collocation:
        command = [
            str(python_exe),
            str(resolve_path("25to1/scripts/build_stage1_station_collocations.py")),
            "--station-meta",
            str(metadata_subset_csv),
            "--station-csv-dir",
            str(normalized_dir),
            "--station-csv-glob",
            "SURFACE_AWS_*_normalized.csv",
            "--features-dir",
            str(resolve_path(args.features_dir)),
            "--daily-dir",
            str(resolve_path(args.daily_dir)),
            "--output-dir",
            str(collocation_output_dir),
        ]
        if args.merge_existing_csv:
            command.extend(["--merge-existing-csv", str(resolve_path(args.merge_existing_csv))])
        run_command(command)

    collocation_summary_path = collocation_output_dir / "stage1_station_collocations_2018_01_summary.json"
    collocation_summary = load_json(collocation_summary_path) if collocation_summary_path.exists() else {}

    summary = {
        "run_name": run_name,
        "year": args.year,
        "frequency": args.frequency,
        "offset": args.offset,
        "limit": args.limit,
        "download_result_json": str(download_result_json),
        "selected_station_ids": selected_station_ids,
        "selected_station_count": len(selected_station_ids),
        "missing_raw_station_ids": missing_raw_station_ids,
        "normalized_csv_count": len(normalized_paths),
        "metadata_summary": metadata_summary,
        "collocation_output_dir": str(collocation_output_dir),
        "collocation_summary": collocation_summary,
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"WROTE {summary_json}")


if __name__ == "__main__":
    main()
