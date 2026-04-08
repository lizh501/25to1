import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy
from rasterio.warp import transform


DAY_NPZ_RE = re.compile(r"^A\d{7}\.npz$")
NODATA = -9999.0
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


def parse_modis_day(day: str) -> datetime:
    return datetime.strptime(day[1:], "%Y%j")


def format_modis_day(dt: datetime) -> str:
    return dt.strftime("A%Y%j")


def iter_days(features_dir: Path, day: str, start_day: str, end_day: str) -> list[str]:
    if day:
        return [day]
    days = [
        path.stem
        for path in sorted(features_dir.glob("A*.npz"))
        if DAY_NPZ_RE.match(path.name)
    ]
    if start_day:
        days = [item for item in days if item >= start_day]
    if end_day:
        days = [item for item in days if item <= end_day]
    return days


def find_reference_raster(daily_dir: Path, day: str) -> Path:
    return next((daily_dir / day).glob("*_lst_day_c.tif"))


def latlon_cache_path(cache_dir: Path, day: str) -> Path:
    return cache_dir / f"{day}_latlon_cache.npz"


def compute_latlon_grids(reference_path: Path, cache_path: Path) -> tuple[np.ndarray, np.ndarray]:
    if cache_path.exists():
        with np.load(cache_path) as data:
            return data["lat"], data["lon"]

    with rasterio.open(reference_path) as ds:
        rows, cols = np.indices((ds.height, ds.width), dtype=np.int32)
        xs, ys = xy(ds.transform, rows, cols, offset="center")
        xs = np.asarray(xs, dtype=np.float64).reshape(-1)
        ys = np.asarray(ys, dtype=np.float64).reshape(-1)
        lons, lats = transform(ds.crs, "EPSG:4326", xs.tolist(), ys.tolist())
        lat = np.asarray(lats, dtype=np.float32).reshape(ds.height, ds.width)
        lon = np.asarray(lons, dtype=np.float32).reshape(ds.height, ds.width)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache_path, lat=lat, lon=lon)
    return lat, lon


def build_prediction_mask(curr_data, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    dem = curr_data["dem_m"].astype(np.float32)
    aspect = curr_data["aspect_deg"].astype(np.float32)
    imp = curr_data["imp_proxy"].astype(np.float32)
    mask = np.isfinite(lat) & np.isfinite(lon)
    mask &= np.isfinite(dem) & (dem > -10000.0)
    mask &= np.isfinite(aspect)
    mask &= np.isfinite(imp)
    return mask


def load_prev_day_arrays(features_dir: Path, day: str) -> tuple[np.ndarray, np.ndarray]:
    prev_day = format_modis_day(parse_modis_day(day) - timedelta(days=1))
    prev_path = features_dir / f"{prev_day}.npz"
    if not prev_path.exists():
        return None, None
    with np.load(prev_path) as data:
        return data["lst_day_c"].astype(np.float32), data["lst_night_c"].astype(np.float32)


def predict_day_raster(
    model,
    features_dir: Path,
    daily_dir: Path,
    output_dir: Path,
    cache_dir: Path,
    day: str,
    chunk_size: int,
    clip_min: float | None,
    clip_max: float | None,
) -> dict:
    npz_path = features_dir / f"{day}.npz"
    with np.load(npz_path) as curr_data:
        curr_payload = {key: curr_data[key].copy() for key in curr_data.files}

    prev_day_lsts = load_prev_day_arrays(features_dir, day)
    lst_prev_day, lst_prev_night = prev_day_lsts
    if lst_prev_day is None:
        lst_prev_day = np.full_like(curr_payload["lst_day_c"], np.nan, dtype=np.float32)
        lst_prev_night = np.full_like(curr_payload["lst_night_c"], np.nan, dtype=np.float32)

    reference_path = find_reference_raster(daily_dir, day)
    lat, lon = compute_latlon_grids(reference_path, latlon_cache_path(cache_dir, day))
    prediction_mask = build_prediction_mask(curr_payload, lat, lon)

    flat_idx = np.flatnonzero(prediction_mask.reshape(-1))
    pred_flat = np.full(prediction_mask.size, NODATA, dtype=np.float32)

    feature_arrays = {
        "lst_prev_daytime_c": lst_prev_day.reshape(-1),
        "lst_prev_nighttime_c": lst_prev_night.reshape(-1),
        "lst_curr_daytime_c": curr_payload["lst_day_c"].reshape(-1),
        "lst_curr_nighttime_c": curr_payload["lst_night_c"].reshape(-1),
        "solar_incoming_w_m2": curr_payload["solar_incoming_w_m2"].reshape(-1),
        "ndvi": curr_payload["ndvi"].reshape(-1),
        "lat": lat.reshape(-1),
        "lon": lon.reshape(-1),
        "dem_m": curr_payload["dem_m"].reshape(-1),
        "aspect_deg": curr_payload["aspect_deg"].reshape(-1),
        "imp_proxy": curr_payload["imp_proxy"].reshape(-1),
    }

    for start in range(0, len(flat_idx), chunk_size):
        idx = flat_idx[start : start + chunk_size]
        frame = pd.DataFrame({key: feature_arrays[key][idx] for key in FEATURES}, columns=FEATURES)
        preds = model.predict(frame).astype(np.float32)
        pred_flat[idx] = preds

    prediction = pred_flat.reshape(prediction_mask.shape)
    finite_mask = prediction != NODATA
    clipped_pixels = 0
    if finite_mask.any() and (clip_min is not None or clip_max is not None):
        finite_values = prediction[finite_mask]
        original = finite_values.copy()
        if clip_min is not None:
            finite_values = np.maximum(finite_values, np.float32(clip_min))
        if clip_max is not None:
            finite_values = np.minimum(finite_values, np.float32(clip_max))
        clipped_pixels = int(np.count_nonzero(finite_values != original))
        prediction[finite_mask] = finite_values

    with rasterio.open(reference_path) as ref:
        profile = ref.profile.copy()

    pred_profile = profile.copy()
    pred_profile.update(dtype="float32", count=1, nodata=NODATA, compress="deflate")
    valid_profile = profile.copy()
    valid_profile.update(dtype="uint8", count=1, nodata=0, compress="deflate")

    day_output_dir = output_dir / day
    day_output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = day_output_dir / f"{day}_modis_at_paperlike_c.tif"
    valid_path = day_output_dir / f"{day}_modis_at_paperlike_valid.tif"

    with rasterio.open(pred_path, "w", **pred_profile) as dst:
        dst.write(prediction, 1)
    with rasterio.open(valid_path, "w", **valid_profile) as dst:
        dst.write(prediction_mask.astype(np.uint8), 1)

    finite = prediction[prediction != NODATA]
    return {
        "day": day,
        "date": parse_modis_day(day).strftime("%Y-%m-%d"),
        "prediction_tif": str(pred_path),
        "valid_tif": str(valid_path),
        "valid_pixels": int(prediction_mask.sum()),
        "clipped_pixels": clipped_pixels,
        "pred_mean_c": None if finite.size == 0 else float(np.nanmean(finite)),
        "pred_min_c": None if finite.size == 0 else float(np.nanmin(finite)),
        "pred_max_c": None if finite.size == 0 else float(np.nanmax(finite)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily 1-km paper-like MODIS-AT grids from a trained station-level model.")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--features-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-dir", default="25to1/data/stage1/interim/latlon_cache")
    parser.add_argument("--chunk-size", type=int, default=250000)
    parser.add_argument("--day", default="")
    parser.add_argument("--start-day", default="")
    parser.add_argument("--end-day", default="")
    parser.add_argument("--clip-min", type=float, default=None)
    parser.add_argument("--clip-max", type=float, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    model = joblib.load(Path(args.model_path).resolve())
    features_dir = Path(args.features_dir).resolve()
    daily_dir = Path(args.daily_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    cache_dir = Path(args.cache_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for day in iter_days(features_dir, args.day, args.start_day, args.end_day):
        pred_path = output_dir / day / f"{day}_modis_at_paperlike_c.tif"
        if args.skip_existing and pred_path.exists():
            print(f"SKIP {day}: existing prediction")
            continue
        item = predict_day_raster(
            model=model,
            features_dir=features_dir,
            daily_dir=daily_dir,
            output_dir=output_dir,
            cache_dir=cache_dir,
            day=day,
            chunk_size=args.chunk_size,
            clip_min=args.clip_min,
            clip_max=args.clip_max,
        )
        manifest.append(item)
        print(
            f"BUILT {day}: valid_pixels={item['valid_pixels']} "
            f"pred_mean={item['pred_mean_c']:.2f}C "
            f"clipped_pixels={item['clipped_pixels']}"
        )

    manifest_path = output_dir / "manifest.json"
    summary = {
        "model_path": str(Path(args.model_path).resolve()),
        "days_built": len(manifest),
        "output_dir": str(output_dir),
        "manifest": manifest,
    }
    manifest_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {manifest_path}")


if __name__ == "__main__":
    main()
