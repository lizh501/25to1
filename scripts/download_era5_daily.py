import argparse
from pathlib import Path

from stage1_common import load_env_file, load_json


def build_request(cfg: dict, year: int, months: list[int] | None = None) -> dict:
    bbox = cfg["region"]["bbox_wgs84"]
    month_values = months or list(range(1, 13))
    return {
        "product_type": "reanalysis",
        "variable": ["2m_temperature"],
        "year": [f"{year:04d}"],
        "month": [f"{month:02d}" for month in month_values],
        "day": [f"{day:02d}" for day in range(1, 32)],
        "daily_statistic": "daily_mean",
        "time_zone": "utc+00:00",
        "frequency": "1_hourly",
        "area": [bbox[3], bbox[0], bbox[1], bbox[2]],
        "format": "netcdf",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ERA5 daily statistics for Stage-1.")
    parser.add_argument(
        "--config",
        default="25to1/configs/stage1_data_config.example.json",
        help="Path to config JSON.",
    )
    parser.add_argument(
        "--env-file",
        default="25to1/configs/stage1_credentials.example.env",
        help="Path to env file.",
    )
    parser.add_argument("--year", type=int, required=True, help="Single year to download.")
    parser.add_argument(
        "--months",
        default="",
        help="Optional comma-separated months, e.g. 01 or 01,02,03. Empty means full year.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional explicit output path. Defaults to the stage1 raw era5 directory.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    env_path = Path(args.env_file).resolve()
    load_env_file(env_path)
    cfg = load_json(config_path)

    try:
        import cdsapi
    except ModuleNotFoundError:
        print("cdsapi is not installed.")
        print("Install it with: python -m pip install cdsapi")
        return

    months = [int(item) for item in args.months.split(",") if item.strip()] if args.months else None
    output_path = Path(args.output).resolve() if args.output else None
    if output_path is None:
        workspace_root = config_path.parents[2]
        suffix = f"_{args.months.replace(',', '-')}" if args.months else ""
        output_path = (
            workspace_root
            / cfg["paths"]["era5_daily"]
            / f"era5_daily_t2m_{args.year:04d}{suffix}.nc"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    request = build_request(cfg, args.year, months=months)
    period_label = f"{args.year}-{args.months}" if args.months else f"{args.year}"
    print(f"Downloading ERA5 daily mean T2M for {period_label} -> {output_path}")

    client = cdsapi.Client()
    client.retrieve(
        "derived-era5-single-levels-daily-statistics",
        request,
        str(output_path),
    )

    print("Download complete.")


if __name__ == "__main__":
    main()
