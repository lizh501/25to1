import argparse
import json
from pathlib import Path

from stage1_common import (
    load_env_file,
    load_json,
    modis_tiles_for_bbox,
    workspace_root_from_config,
)


def build_plan(config_path: Path, env_path: Path | None) -> dict:
    if env_path:
        load_env_file(env_path)

    cfg = load_json(config_path)
    workspace_root = workspace_root_from_config(config_path)
    bbox = cfg["region"]["bbox_wgs84"]
    tiles = modis_tiles_for_bbox(
        min_lon=bbox[0],
        min_lat=bbox[1],
        max_lon=bbox[2],
        max_lat=bbox[3],
    )

    plan = {
        "project": cfg["project"],
        "region": cfg["region"],
        "time_ranges": cfg["time_ranges"],
        "modis_tiles": tiles,
        "bootstrap_recommendation": {
            "time_range": [
                cfg["time_ranges"]["bootstrap_start"],
                cfg["time_ranges"]["bootstrap_end"],
            ],
            "datasets": ["mod11a1", "era5_daily", "mcd12q1", "srtm"],
        },
        "paths": {
            name: str((workspace_root / rel).resolve())
            for name, rel in cfg["paths"].items()
        },
        "credentials_present": {
            env_name: bool(__import__("os").environ.get(env_name))
            for group in cfg["credentials"].values()
            for env_name in group
        },
    }
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Stage-1 download plan.")
    parser.add_argument(
        "--config",
        default="25to1/configs/stage1_data_config.example.json",
        help="Path to config JSON.",
    )
    parser.add_argument(
        "--env-file",
        default="25to1/configs/stage1_credentials.example.env",
        help="Path to env file to preload before checking credentials.",
    )
    parser.add_argument(
        "--output",
        default="25to1/data/stage1/interim/stage1_download_plan.json",
        help="Path to the generated plan JSON.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    env_path = Path(args.env_file).resolve() if args.env_file else None
    output_path = Path(args.output).resolve()

    plan = build_plan(config_path, env_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote plan: {output_path}")
    print(f"MODIS tiles for region: {', '.join(plan['modis_tiles'])}")
    print("Bootstrap datasets: " + ", ".join(plan["bootstrap_recommendation"]["datasets"]))


if __name__ == "__main__":
    main()
