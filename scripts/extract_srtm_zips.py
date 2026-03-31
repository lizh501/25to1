import argparse
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract downloaded SRTM zip files.")
    parser.add_argument(
        "--input-dir",
        default="25to1/data/stage1/raw/srtm",
        help="Directory containing downloaded SRTM zip files.",
    )
    parser.add_argument(
        "--output-dir",
        default="25to1/data/stage1/raw/srtm/unpacked",
        help="Directory to write extracted HGT files.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_files = sorted(input_dir.glob("*.zip"))
    extracted = 0
    skipped = 0
    for zip_path in zip_files:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.namelist()
            if not members:
                skipped += 1
                print(f"SKIP empty zip: {zip_path.name}")
                continue
            for member in members:
                target = output_dir / Path(member).name
                if target.exists():
                    skipped += 1
                    print(f"SKIP exists: {target.name}")
                    continue
                print(f"EXTRACT {zip_path.name} -> {target.name}")
                with zf.open(member) as src, target.open("wb") as dst:
                    dst.write(src.read())
                extracted += 1

    print(f"Done. zip_files={len(zip_files)} extracted={extracted} skipped={skipped} output_dir={output_dir}")


if __name__ == "__main__":
    main()
