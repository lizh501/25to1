import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import rasterio
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline


TARGET = "station_avg_temp_c"
DATE_COL = "date"
DAY_NPZ_RE = re.compile(r"^A\d{7}\.npz$")
NODATA = -9999.0

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


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": rmse(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
    }


def load_collocations(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df[np.isfinite(df[TARGET])].copy()
    return df


def build_model(model_kind: str) -> Pipeline:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, GRID_FEATURES),
        ]
    )
    if model_kind == "linear_regression":
        estimator = LinearRegression()
    elif model_kind == "random_forest":
        estimator = RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            min_samples_leaf=2,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Unsupported model kind: {model_kind}")
    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("model", estimator),
        ]
    )


def parse_modis_day(day: str) -> datetime:
    return datetime.strptime(day[1:], "%Y%j")


def iter_days(features_dir: Path, day: str, start_day: str) -> list[str]:
    if day:
        return [day]
    days = [
        path.stem
        for path in sorted(features_dir.glob("A*.npz"))
        if DAY_NPZ_RE.match(path.name)
    ]
    if start_day:
        days = [item for item in days if item >= start_day]
    return days


def find_reference_raster(daily_dir: Path, day: str) -> Path:
    return next((daily_dir / day).glob("*_lst_day_c.tif"))


def build_prediction_mask(data) -> np.ndarray:
    valid_mask = data["valid_mean"].astype(np.uint8) > 0
    dem = data["dem_m"].astype(np.float32)
    lc = data["lc_type1_majority"].astype(np.float32)
    mask = valid_mask.copy()
    mask &= np.isfinite(dem)
    mask &= dem > -10000.0
    mask &= np.isfinite(lc)
    mask &= lc >= 0.0
    return mask


def predict_day_raster(
    npz_path: Path,
    daily_dir: Path,
    day: str,
    model: Pipeline,
    output_dir: Path,
    chunk_size: int,
) -> dict:
    with np.load(npz_path) as data:
        shape = data["valid_mean"].shape
        prediction_mask = build_prediction_mask(data)
        valid_indices = np.flatnonzero(prediction_mask.reshape(-1))
        pred_flat = np.full(shape[0] * shape[1], NODATA, dtype=np.float32)

        if len(valid_indices) > 0:
            feature_arrays = {}
            for key in GRID_FEATURES:
                arr = data[key].astype(np.float32, copy=True) if data[key].dtype.kind in "iu" else data[key].copy()
                if key == "dem_m":
                    arr = arr.astype(np.float32, copy=False)
                    arr[arr <= -10000.0] = np.nan
                elif key == "lc_type1_majority":
                    arr = arr.astype(np.float32, copy=False)
                    arr[arr < 0.0] = np.nan
                feature_arrays[key] = arr.reshape(-1)
            for start in range(0, len(valid_indices), chunk_size):
                idx = valid_indices[start : start + chunk_size]
                frame = pd.DataFrame(
                    {key: feature_arrays[key][idx] for key in GRID_FEATURES},
                    columns=GRID_FEATURES,
                )
                preds = model.predict(frame).astype(np.float32)
                pred_flat[idx] = preds

    prediction = pred_flat.reshape(shape)
    reference_path = find_reference_raster(daily_dir, day)
    with rasterio.open(reference_path) as ref:
        profile = ref.profile.copy()

    profile.update(dtype="float32", count=1, compress="deflate", nodata=NODATA)
    day_output_dir = output_dir / day
    day_output_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = day_output_dir / f"{day}_modis_at_bootstrap_c.tif"
    valid_path = day_output_dir / f"{day}_modis_at_bootstrap_valid.tif"

    with rasterio.open(prediction_path, "w", **profile) as dst:
        dst.write(prediction, 1)

    valid_profile = profile.copy()
    valid_profile.update(dtype="uint8", nodata=0, compress="deflate")
    with rasterio.open(valid_path, "w", **valid_profile) as dst:
        dst.write(prediction_mask.astype(np.uint8), 1)

    finite_values = prediction[prediction != NODATA]
    return {
        "day": day,
        "date": parse_modis_day(day).strftime("%Y-%m-%d"),
        "prediction_tif": str(prediction_path),
        "valid_tif": str(valid_path),
        "valid_pixels": int(prediction_mask.sum()),
        "pred_mean_c": None if finite_values.size == 0 else float(np.nanmean(finite_values)),
        "pred_min_c": None if finite_values.size == 0 else float(np.nanmin(finite_values)),
        "pred_max_c": None if finite_values.size == 0 else float(np.nanmax(finite_values)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a bootstrap MODIS-derived AT surrogate and apply it to daily 1-km feature stacks.")
    parser.add_argument(
        "--collocations",
        default="25to1/data/stage1/processed/station_collocations_full65_q1/stage1_station_collocations_2018_01.csv",
    )
    parser.add_argument(
        "--features-dir",
        default="25to1/data/stage1/processed/stage1_simplified_features",
    )
    parser.add_argument(
        "--daily-dir",
        default="25to1/data/stage1/interim/mod11a1_daily",
    )
    parser.add_argument(
        "--model-dir",
        default="25to1/data/stage1/models/modis_at_bootstrap_q1",
    )
    parser.add_argument(
        "--output-dir",
        default="25to1/data/stage1/processed/modis_at_bootstrap_q1",
    )
    parser.add_argument(
        "--model-kind",
        choices=["linear_regression", "random_forest"],
        default="linear_regression",
    )
    parser.add_argument("--chunk-size", type=int, default=250000)
    parser.add_argument("--day", default="", help="Optional single MODIS day like A2018001.")
    parser.add_argument("--start-day", default="", help="Optional resume day like A2018060.")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    collocations_path = Path(args.collocations).resolve()
    features_dir = Path(args.features_dir).resolve()
    daily_dir = Path(args.daily_dir).resolve()
    model_dir = Path(args.model_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_collocations(collocations_path)
    model = build_model(args.model_kind)
    X_train = df[GRID_FEATURES]
    y_train = df[TARGET].to_numpy(dtype=float)
    model.fit(X_train, y_train)
    train_preds = model.predict(X_train)

    model_path = model_dir / f"{args.model_kind}_grid_only.joblib"
    joblib.dump(model, model_path)

    training_summary = {
        "dataset": str(collocations_path),
        "target": TARGET,
        "feature_columns": GRID_FEATURES,
        "model_kind": args.model_kind,
        "train_rows": int(len(df)),
        "date_min": df[DATE_COL].min().strftime("%Y-%m-%d"),
        "date_max": df[DATE_COL].max().strftime("%Y-%m-%d"),
        "train_metrics": metrics_dict(y_train, train_preds),
        "model_path": str(model_path),
    }
    training_summary_path = model_dir / "training_summary.json"
    training_summary_path.write_text(json.dumps(training_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest = []
    for day in iter_days(features_dir, args.day, args.start_day):
        npz_path = features_dir / f"{day}.npz"
        if not npz_path.exists():
            print(f"SKIP {day}: missing npz")
            continue
        prediction_path = output_dir / day / f"{day}_modis_at_bootstrap_c.tif"
        if args.skip_existing and prediction_path.exists():
            print(f"SKIP {day}: existing prediction")
            continue
        item = predict_day_raster(
            npz_path=npz_path,
            daily_dir=daily_dir,
            day=day,
            model=model,
            output_dir=output_dir,
            chunk_size=args.chunk_size,
        )
        manifest.append(item)
        print(
            f"BUILT {day}: "
            f"valid_pixels={item['valid_pixels']} "
            f"pred_mean={item['pred_mean_c']:.2f}C"
        )

    manifest_path = output_dir / "manifest.json"
    summary = {
        "model_kind": args.model_kind,
        "model_path": str(model_path),
        "days_built": len(manifest),
        "output_dir": str(output_dir),
        "manifest": manifest,
    }
    manifest_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE {training_summary_path}")
    print(f"WROTE {manifest_path}")


if __name__ == "__main__":
    main()
