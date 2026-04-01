import argparse
import csv
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
from sklearn.preprocessing import OneHotEncoder


TARGET = "station_avg_temp_c"
DATE_COL = "date"
SOURCE_COL = "source"
STATION_COL = "station_id"

GRID_FEATURES = [
    "era5_t2m_c",
    "dem_m",
    "slope_deg",
    "aspect_deg",
    "imp_proxy",
    "lc_type1_majority",
    "lst_day_c",
    "lst_night_c",
    "lst_mean_c",
    "ndvi",
    "solar_incoming_w_m2",
    "valid_day",
    "valid_night",
    "valid_mean",
]

CATEGORICAL_FEATURES = [SOURCE_COL]


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df[np.isfinite(df[TARGET])]
    df[STATION_COL] = df[STATION_COL].astype(str)
    return df


def time_split(df: pd.DataFrame, split_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_ts = pd.Timestamp(split_date)
    train_df = df[df[DATE_COL] < split_ts].copy()
    test_df = df[df[DATE_COL] >= split_ts].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Time split produced an empty train or test set.")
    return train_df, test_df


def station_holdout_split(df: pd.DataFrame, holdout_station_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    holdout_station_id = str(holdout_station_id)
    train_df = df[df[STATION_COL] != holdout_station_id].copy()
    test_df = df[df[STATION_COL] == holdout_station_id].copy()
    if train_df.empty or test_df.empty:
        raise ValueError(f"Station holdout split produced an empty train or test set for station_id={holdout_station_id}.")
    return train_df, test_df


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": rmse(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
    }


def baseline_era5_metrics(test_df: pd.DataFrame) -> dict:
    y_true = test_df[TARGET].to_numpy(dtype=float)
    y_pred = test_df["era5_t2m_c"].to_numpy(dtype=float)
    return metrics_dict(y_true, y_pred)


def build_preprocessor(categorical_features: list[str]) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    transformers = [("num", numeric_pipeline, GRID_FEATURES)]
    if categorical_features:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore", drop="if_binary")),
            ]
        )
        transformers.append(("cat", categorical_pipeline, categorical_features))
    return ColumnTransformer(transformers=transformers)


def train_and_eval(
    model_name: str,
    estimator,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    output_dir: Path,
    categorical_features: list[str],
) -> dict:
    features = GRID_FEATURES + categorical_features
    X_train = train_df[features]
    y_train = train_df[TARGET].to_numpy(dtype=float)
    X_test = test_df[features]
    y_test = test_df[TARGET].to_numpy(dtype=float)

    pipeline = Pipeline(
        steps=[
            ("preprocess", build_preprocessor(categorical_features)),
            ("model", estimator),
        ]
    )
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    metrics = metrics_dict(y_test, preds)

    model_path = output_dir / f"{model_name}.joblib"
    joblib.dump(pipeline, model_path)

    pred_rows = []
    for _, row in test_df.reset_index(drop=True).iterrows():
        pred_rows.append(
            {
                "date": row[DATE_COL].strftime("%Y-%m-%d"),
                "source": row[SOURCE_COL],
                "station_id": str(row[STATION_COL]),
                "target_station_avg_temp_c": float(row[TARGET]),
                "pred_station_avg_temp_c": float(preds[len(pred_rows)]),
                "era5_t2m_c": float(row["era5_t2m_c"]),
                "lst_mean_c": None if not np.isfinite(row["lst_mean_c"]) else float(row["lst_mean_c"]),
            }
        )

    pred_path = output_dir / f"{model_name}_predictions.csv"
    with pred_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(pred_rows[0].keys()))
        writer.writeheader()
        writer.writerows(pred_rows)

    metrics["model_path"] = str(model_path)
    metrics["predictions_csv"] = str(pred_path)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a bootstrap Stage-1 station baseline from January 2018 collocations.")
    parser.add_argument(
        "--collocations",
        default="25to1/data/stage1/processed/station_collocations/stage1_station_collocations_2018_01.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="25to1/data/stage1/models/station_baseline_jan2018",
    )
    parser.add_argument(
        "--split-date",
        default="2018-01-21",
        help="Train on dates before this day, test on this day and later.",
    )
    parser.add_argument(
        "--split-mode",
        choices=["time", "station_holdout"],
        default="time",
        help="Evaluation split mode.",
    )
    parser.add_argument(
        "--holdout-station-id",
        default=None,
        help="Station ID used as the test set when --split-mode station_holdout.",
    )
    args = parser.parse_args()

    collocation_path = Path(args.collocations).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(collocation_path)
    if args.split_mode == "time":
        train_df, test_df = time_split(df, args.split_date)
        split_summary = {
            "split_mode": "time",
            "split_date": args.split_date,
            "train_date_min": train_df[DATE_COL].min().strftime("%Y-%m-%d"),
            "train_date_max": train_df[DATE_COL].max().strftime("%Y-%m-%d"),
            "test_date_min": test_df[DATE_COL].min().strftime("%Y-%m-%d"),
            "test_date_max": test_df[DATE_COL].max().strftime("%Y-%m-%d"),
        }
    else:
        if not args.holdout_station_id:
            raise ValueError("--holdout-station-id is required when --split-mode station_holdout.")
        train_df, test_df = station_holdout_split(df, args.holdout_station_id)
        split_summary = {
            "split_mode": "station_holdout",
            "holdout_station_id": str(args.holdout_station_id),
            "train_station_ids": sorted(train_df[STATION_COL].astype(str).unique().tolist()),
            "test_station_ids": sorted(test_df[STATION_COL].astype(str).unique().tolist()),
            "train_date_min": train_df[DATE_COL].min().strftime("%Y-%m-%d"),
            "train_date_max": train_df[DATE_COL].max().strftime("%Y-%m-%d"),
            "test_date_min": test_df[DATE_COL].min().strftime("%Y-%m-%d"),
            "test_date_max": test_df[DATE_COL].max().strftime("%Y-%m-%d"),
        }

    summary = {
        "dataset": str(collocation_path),
        "target": TARGET,
        "feature_columns": {
            "grid_only": GRID_FEATURES,
            "grid_plus_source": GRID_FEATURES + CATEGORICAL_FEATURES,
        },
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        **split_summary,
        "baselines": {},
    }

    summary["baselines"]["era5_only"] = baseline_era5_metrics(test_df)
    summary["baselines"]["linear_regression"] = train_and_eval(
        "linear_regression",
        LinearRegression(),
        train_df,
        test_df,
        output_dir,
        CATEGORICAL_FEATURES,
    )
    summary["baselines"]["random_forest"] = train_and_eval(
        "random_forest",
        RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            min_samples_leaf=2,
        ),
        train_df,
        test_df,
        output_dir,
        CATEGORICAL_FEATURES,
    )
    summary["baselines"]["linear_regression_grid_only"] = train_and_eval(
        "linear_regression_grid_only",
        LinearRegression(),
        train_df,
        test_df,
        output_dir,
        [],
    )
    summary["baselines"]["random_forest_grid_only"] = train_and_eval(
        "random_forest_grid_only",
        RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            min_samples_leaf=2,
        ),
        train_df,
        test_df,
        output_dir,
        [],
    )

    summary_path = output_dir / "metrics_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"WROTE {summary_path}")


if __name__ == "__main__":
    main()
