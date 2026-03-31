import argparse
import json
import os
from pathlib import Path


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def check_paths(root: Path, cfg: dict) -> None:
    print_section("Paths")
    for name, rel in cfg["paths"].items():
        abs_path = (root / rel).resolve()
        exists = abs_path.exists()
        files = count_files(abs_path)
        status = "OK" if exists else "MISSING"
        print(f"{name:16} {status:8} files={files:4d} path={abs_path}")


def check_credentials(cfg: dict) -> None:
    print_section("Credentials")
    for group_name, env_names in cfg["credentials"].items():
        values = []
        for env_name in env_names:
            present = bool(os.environ.get(env_name))
            values.append(f"{env_name}={'SET' if present else 'MISSING'}")
        print(f"{group_name:12} " + ", ".join(values))


def check_datasets(cfg: dict) -> None:
    print_section("Datasets")
    for name, meta in cfg["datasets"].items():
        required = "yes" if meta.get("required") else "no"
        source = meta.get("source") or "TBD"
        notes = meta.get("notes", "")
        print(f"{name:16} required={required:3} source={source}")
        if notes:
            print(f"  note: {notes}")


def print_next_actions() -> None:
    print_section("Next Actions")
    print("1. Fill environment variables from configs/stage1_credentials.example.env")
    print("2. Download a bootstrap subset first: 2018 only")
    print("3. Verify MODIS, ERA5, DEM and land-cover can be co-registered")
    print("4. Only then expand to full 2000-2020 range")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Stage-1 data readiness.")
    parser.add_argument(
        "--config",
        default="25to1/configs/stage1_data_config.example.json",
        help="Path to the Stage-1 data config JSON."
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    workspace_root = config_path.parents[2]
    cfg = load_config(config_path)

    print(f"Config: {config_path}")
    print(f"Workspace root: {workspace_root}")
    print(f"Region: {cfg['region']['name']} bbox={cfg['region']['bbox_wgs84']}")
    print(f"Bootstrap range: {cfg['time_ranges']['bootstrap_start']} -> {cfg['time_ranges']['bootstrap_end']}")

    check_paths(workspace_root, cfg)
    check_credentials(cfg)
    check_datasets(cfg)
    print_next_actions()


if __name__ == "__main__":
    main()
