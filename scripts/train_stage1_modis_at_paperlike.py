import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline


TARGET = "target_station_avg_temp_c"
FEATURES = [
    "lst_prev_daytime_c",
    "lst_prev_nighttime_c",
    "lst_curr_daytime_c",
    "lst_curr_nighttime_c",
    "solar_incoming_w_m2",
    "ndvi",
    "lat",
    "lon",
    "dem_m",
    "aspect_deg",
    "imp_proxy",
]


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": rmse(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
    }


def mean_available(frame: pd.DataFrame, cols: list[str]) -> np.ndarray:
    arr = frame[cols].to_numpy(dtype=float)
    valid_counts = np.isfinite(arr).sum(axis=1)
    with np.errstate(all="ignore"):
        sums = np.nansum(arr, axis=1)
    out = np.full(arr.shape[0], np.nan, dtype=float)
    has_valid = valid_counts > 0
    out[has_valid] = sums[has_valid] / valid_counts[has_valid]
    return out


def build_pipeline(model_kind: str) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))]),
                FEATURES,
            )
        ]
    )
    if model_kind == "linear_regression":
        model = LinearRegression()
    elif model_kind == "random_forest":
        model = RandomForestRegressor(
            n_estimators=300,
            random_state=42,
            min_samples_leaf=2,
            n_jobs=-1,
        )
    else:
        raise ValueError(model_kind)
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a paper-closer Stage-1 MODIS-AT label model with AWS-train/ASOS-validate splits.")
    parser.add_argument(
        "--dataset",
        default="25to1/data/stage1/processed/modis_at_paperlike_dataset_jansep/stage1_modis_at_paperlike_dataset.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="25to1/data/stage1/models/modis_at_paperlike_jansep",
    )
    parser.add_argument(
        "--pooled-split-date",
        default="2018-07-01",
        help="Additional all-station time-split diagnostic.",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(dataset_path, encoding="utf-8")
    train_df = df[df["split"] == "train"].copy()
    validate_df = df[df["split"] == "validate"].copy()
    if train_df.empty or validate_df.empty:
        raise RuntimeError("Expected both train (AWS) and validate (ASOS) splits to be non-empty.")

    y_train = train_df[TARGET].to_numpy(dtype=float)
    y_validate = validate_df[TARGET].to_numpy(dtype=float)

    summary = {
        "dataset": str(dataset_path),
        "target": TARGET,
        "feature_columns": FEATURES,
        "train_rows": int(len(train_df)),
        "validate_rows": int(len(validate_df)),
        "train_station_count": int(train_df["station_id"].astype(str).nunique()),
        "validate_station_count": int(validate_df["station_id"].astype(str).nunique()),
        "train_date_min": str(train_df["date"].min()),
        "train_date_max": str(train_df["date"].max()),
        "validate_date_min": str(validate_df["date"].min()),
        "validate_date_max": str(validate_df["date"].max()),
        "baselines": {},
    }

    same_day_mean = mean_available(validate_df, ["lst_curr_daytime_c", "lst_curr_nighttime_c"])
    valid_same_day = np.isfinite(same_day_mean)
    summary["baselines"]["same_day_lst_mean"] = {
        **metrics_dict(y_validate[valid_same_day], same_day_mean[valid_same_day]),
        "valid_rows": int(valid_same_day.sum()),
    }

    four_obs_mean = validate_df["lst_four_obs_mean_c"].to_numpy(dtype=float)
    valid_four = np.isfinite(four_obs_mean)
    summary["baselines"]["four_obs_lst_mean"] = {
        **metrics_dict(y_validate[valid_four], four_obs_mean[valid_four]),
        "valid_rows": int(valid_four.sum()),
    }

    for model_kind in ["linear_regression", "random_forest"]:
        pipeline = build_pipeline(model_kind)
        pipeline.fit(train_df[FEATURES], y_train)
        preds = pipeline.predict(validate_df[FEATURES])
        metrics = metrics_dict(y_validate, preds)
        model_path = output_dir / f"{model_kind}.joblib"
        joblib.dump(pipeline, model_path)
        pred_path = output_dir / f"{model_kind}_validate_predictions.csv"
        pred_df = validate_df[["source", "station_id", "date", TARGET]].copy()
        pred_df["prediction_c"] = preds
        pred_df.to_csv(pred_path, index=False, encoding="utf-8")
        summary["baselines"][model_kind] = {
            **metrics,
            "model_path": str(model_path),
            "predictions_csv": str(pred_path),
        }

    df["date"] = pd.to_datetime(df["date"])
    pooled_train = df[df["date"] < pd.Timestamp(args.pooled_split_date)].copy()
    pooled_test = df[df["date"] >= pd.Timestamp(args.pooled_split_date)].copy()
    pooled_summary = {
        "split_date": args.pooled_split_date,
        "train_rows": int(len(pooled_train)),
        "test_rows": int(len(pooled_test)),
        "train_station_count": int(pooled_train["station_id"].astype(str).nunique()),
        "test_station_count": int(pooled_test["station_id"].astype(str).nunique()),
        "baselines": {},
    }
    pooled_same_day = mean_available(pooled_test, ["lst_curr_daytime_c", "lst_curr_nighttime_c"])
    valid_pooled_same_day = np.isfinite(pooled_same_day)
    pooled_summary["baselines"]["same_day_lst_mean"] = {
        **metrics_dict(pooled_test[TARGET].to_numpy(dtype=float)[valid_pooled_same_day], pooled_same_day[valid_pooled_same_day]),
        "valid_rows": int(valid_pooled_same_day.sum()),
    }
    pooled_four = pooled_test["lst_four_obs_mean_c"].to_numpy(dtype=float)
    valid_pooled_four = np.isfinite(pooled_four)
    pooled_summary["baselines"]["four_obs_lst_mean"] = {
        **metrics_dict(pooled_test[TARGET].to_numpy(dtype=float)[valid_pooled_four], pooled_four[valid_pooled_four]),
        "valid_rows": int(valid_pooled_four.sum()),
    }
    for model_kind in ["linear_regression", "random_forest"]:
        pipeline = build_pipeline(model_kind)
        pipeline.fit(pooled_train[FEATURES], pooled_train[TARGET].to_numpy(dtype=float))
        preds = pipeline.predict(pooled_test[FEATURES])
        pooled_summary["baselines"][model_kind] = metrics_dict(
            pooled_test[TARGET].to_numpy(dtype=float),
            preds,
        )
    summary["pooled_time_split"] = pooled_summary

    summary_path = output_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"WROTE {summary_path}")


if __name__ == "__main__":
    main()
