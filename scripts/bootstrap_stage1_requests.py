import argparse
from pathlib import Path

from stage1_common import load_env_file, load_json, modis_tiles_for_bbox


def main() -> None:
    parser = argparse.ArgumentParser(description="Print bootstrap download commands for Stage-1.")
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
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    load_env_file(Path(args.env_file).resolve())
    cfg = load_json(config_path)

    bbox = cfg["region"]["bbox_wgs84"]
    tiles = modis_tiles_for_bbox(bbox[0], bbox[1], bbox[2], bbox[3])
    bootstrap_start = cfg["time_ranges"]["bootstrap_start"]
    bootstrap_end = cfg["time_ranges"]["bootstrap_end"]
    bootstrap_year = bootstrap_start[:4]
    tiles_csv = ",".join(tiles)

    print("Bootstrap MODIS tiles:", tiles_csv)
    print("")
    print("1. Generate Stage-1 plan")
    print(
        "python 25to1/scripts/plan_stage1_downloads.py "
        "--config 25to1/configs/stage1_data_config.example.json "
        "--output 25to1/data/stage1/interim/stage1_download_plan.json"
    )
    print("")
    print("2. List MOD11A1 granules for the bootstrap year")
    print(
        "python 25to1/scripts/list_nasa_cmr_granules.py "
        f"--short-name MOD11A1 --version 061 --start-date {bootstrap_start} "
        f"--end-date {bootstrap_end} --tiles {tiles_csv} "
        "--output 25to1/data/stage1/interim/mod11a1_bootstrap_2018.json"
    )
    print("")
    print("3. List MCD12Q1 annual granules")
    print(
        "python 25to1/scripts/list_nasa_cmr_granules.py "
        f"--short-name MCD12Q1 --version 061 --start-date {bootstrap_year}-01-01 "
        f"--end-date {bootstrap_year}-12-31 --tiles {tiles_csv} "
        "--output 25to1/data/stage1/interim/mcd12q1_bootstrap_2018.json"
    )
    print("")
    print("4. Download ERA5 daily mean T2M for the bootstrap year")
    print(
        f"python 25to1/scripts/download_era5_daily.py --year {bootstrap_year} "
        "--config 25to1/configs/stage1_data_config.example.json"
    )
    print("")
    print("5. SRTM and KMA still need account-backed access or manual portal download")


if __name__ == "__main__":
    main()
