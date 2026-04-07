import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def mean_available(frame: pd.DataFrame, cols: list[str]) -> pd.Series:
    arr = frame[cols].to_numpy(dtype=float)
    valid_counts = np.isfinite(arr).sum(axis=1)
    with np.errstate(all="ignore"):
        sums = np.nansum(arr, axis=1)
    out = np.full(arr.shape[0], np.nan, dtype=float)
    has_valid = valid_counts > 0
    out[has_valid] = sums[has_valid] / valid_counts[has_valid]
    out[~np.isfinite(out)] = np.nan
    return pd.Series(out, index=frame.index, dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a paper-closer MODIS-AT station dataset using previous-day and same-day LST observations."
    )
    parser.add_argument(
        "--collocations",
        default="25to1/data/stage1/processed/station_collocations_full65_jansep/stage1_station_collocations_2018_01.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="25to1/data/stage1/processed/modis_at_paperlike_dataset_jansep",
    )
    args = parser.parse_args()

    collocation_path = Path(args.collocations).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(collocation_path, encoding="utf-8")
    df["date"] = pd.to_datetime(df["date"])
    df["station_id"] = df["station_id"].astype(str)
    df = df.sort_values(["source", "station_id", "date"]).reset_index(drop=True)

    group_cols = ["source", "station_id"]
    prev_date = df.groupby(group_cols)["date"].shift(1)
    contiguous_prev = (df["date"] - prev_date).dt.days.eq(1)

    df["lst_prev_daytime_c"] = df.groupby(group_cols)["lst_day_c"].shift(1).where(contiguous_prev, np.nan)
    df["lst_prev_nighttime_c"] = df.groupby(group_cols)["lst_night_c"].shift(1).where(contiguous_prev, np.nan)
    df["valid_prev_day"] = df.groupby(group_cols)["valid_day"].shift(1).where(contiguous_prev, 0).fillna(0).astype(int)
    df["valid_prev_night"] = df.groupby(group_cols)["valid_night"].shift(1).where(contiguous_prev, 0).fillna(0).astype(int)

    df["lst_curr_daytime_c"] = pd.to_numeric(df["lst_day_c"], errors="coerce")
    df["lst_curr_nighttime_c"] = pd.to_numeric(df["lst_night_c"], errors="coerce")
    df["lat"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["lon"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["dem_m"] = pd.to_numeric(df["dem_m"], errors="coerce")
    df["aspect_deg"] = pd.to_numeric(df["aspect_deg"], errors="coerce")
    df["imp_proxy"] = pd.to_numeric(df["imp_proxy"], errors="coerce")
    df["ndvi"] = pd.to_numeric(df["ndvi"], errors="coerce")
    df["solar_incoming_w_m2"] = pd.to_numeric(df["solar_incoming_w_m2"], errors="coerce")
    df["target_station_avg_temp_c"] = pd.to_numeric(df["station_avg_temp_c"], errors="coerce")

    four_lst_cols = [
        "lst_prev_daytime_c",
        "lst_prev_nighttime_c",
        "lst_curr_daytime_c",
        "lst_curr_nighttime_c",
    ]
    df["lst_four_obs_mean_c"] = mean_available(df, four_lst_cols)
    df["split"] = np.where(df["source"] == "aws", "train", np.where(df["source"] == "asos", "validate", "other"))
    df["four_obs_valid_count"] = df[[
        "valid_prev_day",
        "valid_prev_night",
        "valid_day",
        "valid_night",
    ]].sum(axis=1)

    keep_cols = [
        "split",
        "source",
        "station_id",
        "station_name_ko",
        "date",
        "modis_day",
        "lat",
        "lon",
        "elevation_m",
        "pixel_row",
        "pixel_col",
        "target_station_avg_temp_c",
        "lst_prev_daytime_c",
        "lst_prev_nighttime_c",
        "lst_curr_daytime_c",
        "lst_curr_nighttime_c",
        "lst_four_obs_mean_c",
        "valid_prev_day",
        "valid_prev_night",
        "valid_day",
        "valid_night",
        "four_obs_valid_count",
        "solar_incoming_w_m2",
        "ndvi",
        "dem_m",
        "aspect_deg",
        "imp_proxy",
    ]
    out_df = df[keep_cols].copy()
    out_df = out_df[np.isfinite(out_df["target_station_avg_temp_c"])].reset_index(drop=True)

    csv_path = output_dir / "stage1_modis_at_paperlike_dataset.csv"
    out_df.to_csv(csv_path, index=False, encoding="utf-8")

    summary = {
        "input_collocations": str(collocation_path),
        "output_csv": str(csv_path),
        "rows": int(len(out_df)),
        "date_min": out_df["date"].min().strftime("%Y-%m-%d") if len(out_df) else None,
        "date_max": out_df["date"].max().strftime("%Y-%m-%d") if len(out_df) else None,
        "split_counts": out_df["split"].value_counts(dropna=False).to_dict(),
        "stations_by_split": {
            split: int(out_df.loc[out_df["split"] == split, "station_id"].nunique())
            for split in sorted(out_df["split"].unique())
        },
        "rows_with_all_four_lst": int((out_df["four_obs_valid_count"] == 4).sum()),
        "rows_with_any_lst": int((out_df["four_obs_valid_count"] > 0).sum()),
    }
    summary_path = output_dir / "stage1_modis_at_paperlike_dataset_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE {csv_path}")
    print(f"WROTE {summary_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
