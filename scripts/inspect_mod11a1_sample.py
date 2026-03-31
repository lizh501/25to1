import argparse
from pathlib import Path

import numpy as np
from pyhdf.SD import SD, SDC


def read_dataset(hdf: SD, name: str) -> np.ndarray:
    return hdf.select(name)[:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect one MOD11A1 file and summarize key SDS fields.")
    parser.add_argument(
        "--file",
        default="25to1/data/stage1/raw/mod11a1/MOD11A1.A2018001.h28v05.061.2021316021443.hdf",
        help="Path to a MOD11A1 HDF file.",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    display_path = file_path.resolve()
    open_path = file_path
    if open_path.is_absolute():
        try:
            open_path = open_path.relative_to(Path.cwd())
        except ValueError:
            pass

    hdf = SD(str(open_path), SDC.READ)
    datasets = list(hdf.datasets().keys())
    print(f"file={display_path}")
    print(f"dataset_count={len(datasets)}")
    print("datasets=", datasets)

    lst_day = read_dataset(hdf, "LST_Day_1km").astype(np.float64)
    qc_day = read_dataset(hdf, "QC_Day")
    fill_value = 0
    valid = lst_day != fill_value
    lst_kelvin = np.where(valid, lst_day * 0.02, np.nan)
    lst_celsius = lst_kelvin - 273.15

    print(f"shape={lst_day.shape}")
    print(f"valid_pixels={int(np.isfinite(lst_celsius).sum())}")
    print(f"temp_c_min={np.nanmin(lst_celsius):.2f}")
    print(f"temp_c_mean={np.nanmean(lst_celsius):.2f}")
    print(f"temp_c_max={np.nanmax(lst_celsius):.2f}")
    print(f"qc_day_dtype={qc_day.dtype} qc_day_shape={qc_day.shape}")


if __name__ == "__main__":
    main()
