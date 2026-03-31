import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from netCDF4 import Dataset, num2date
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject


WGS84 = CRS.from_epsg(4326)


def parse_modis_day(day_code: str) -> datetime:
    return datetime.strptime(day_code[1:], "%Y%j")


def openable_path(path: Path) -> Path:
    p = path
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return p


def read_raster(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        profile = {
            "crs": ds.crs,
            "transform": ds.transform,
            "width": ds.width,
            "height": ds.height,
            "nodata": ds.nodata,
            "bounds": ds.bounds,
        }
    return arr, profile


def reproject_to_target(
    source_array: np.ndarray,
    source_crs,
    source_transform,
    target_shape: tuple[int, int],
    target_crs,
    target_transform,
    src_nodata,
    dst_nodata,
    resampling: Resampling,
) -> np.ndarray:
    dst = np.full(target_shape, dst_nodata, dtype=np.float32 if np.issubdtype(source_array.dtype, np.floating) else source_array.dtype)
    reproject(
        source=source_array,
        destination=dst,
        src_transform=source_transform,
        src_crs=source_crs,
        src_nodata=src_nodata,
        dst_transform=target_transform,
        dst_crs=target_crs,
        dst_nodata=dst_nodata,
        resampling=resampling,
    )
    return dst


def build_era5_transform(lons: np.ndarray, lats: np.ndarray):
    lon_res = float(np.median(np.diff(lons)))
    lat_res = float(np.median(np.abs(np.diff(lats))))
    left = float(lons.min() - lon_res / 2.0)
    right = float(lons.max() + lon_res / 2.0)
    bottom = float(lats.min() - lat_res / 2.0)
    top = float(lats.max() + lat_res / 2.0)
    return from_bounds(left, bottom, right, top, len(lons), len(lats))


def load_era5_monthly(path: Path):
    ds = Dataset(str(openable_path(path)))
    t2m = ds.variables["t2m"][:]
    lats = ds.variables["latitude"][:]
    lons = ds.variables["longitude"][:]
    times = num2date(ds.variables["valid_time"][:], ds.variables["valid_time"].units)
    transform = build_era5_transform(lons, lats)
    date_to_idx = {datetime(t.year, t.month, t.day).date(): i for i, t in enumerate(times)}
    return ds, t2m, lats, lons, transform, date_to_idx


def nanmean_two(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan, dtype=np.float32)
    a_valid = np.isfinite(a)
    b_valid = np.isfinite(b)
    both = a_valid & b_valid
    only_a = a_valid & ~b_valid
    only_b = ~a_valid & b_valid
    out[both] = (a[both] + b[both]) / 2.0
    out[only_a] = a[only_a]
    out[only_b] = b[only_b]
    return out


def save_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def rebuild_manifest(output_dir: Path) -> list[dict]:
    manifest = []
    for npz_path in sorted(output_dir.glob("A*.npz")):
        day = npz_path.stem
        day_date = parse_modis_day(day).date()
        data = np.load(npz_path)
        valid_mean = data["valid_mean"]
        era5 = data["era5_t2m_c"].astype(np.float32)
        lst_mean = data["lst_mean_c"].astype(np.float32)
        manifest.append(
            {
                "day": day,
                "date": str(day_date),
                "npz": str(npz_path.relative_to(output_dir.parent.parent.parent)),
                "shape": [int(valid_mean.shape[0]), int(valid_mean.shape[1])],
                "lst_mean_valid_pixels": int(valid_mean.sum()),
                "era5_mean_c": float(np.nanmean(era5)),
                "lst_mean_c_mean": float(np.nanmean(lst_mean)),
            }
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build simplified Stage-1 daily feature stacks on the MOD11A1 grid.")
    parser.add_argument("--daily-dir", default="25to1/data/stage1/interim/mod11a1_daily")
    parser.add_argument("--era5", default="25to1/data/stage1/raw/era5_daily/era5_daily_t2m_2018_01.nc")
    parser.add_argument("--dem", default="25to1/data/stage1/processed/srtm_dem_korea_wgs84.tif")
    parser.add_argument("--slope", default="25to1/data/stage1/processed/srtm_slope_korea_wgs84.tif")
    parser.add_argument("--aspect", default="25to1/data/stage1/processed/srtm_aspect_korea_wgs84.tif")
    parser.add_argument("--imp", default="25to1/data/stage1/processed/mcd12q1_imp_proxy_korea_1km.tif")
    parser.add_argument("--lc", default="25to1/data/stage1/processed/mcd12q1_lc_type1_majority_korea_1km.tif")
    parser.add_argument("--output-dir", default="25to1/data/stage1/processed/stage1_simplified_features")
    parser.add_argument("--day", default="", help="Optional single MODIS day code like A2018001")
    parser.add_argument("--start-day", default="", help="Optional start day like A2018022 for resume runs.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip days whose npz already exists.")
    args = parser.parse_args()

    daily_dir = Path(args.daily_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    days = [args.day] if args.day else sorted([p.name for p in daily_dir.iterdir() if p.is_dir()])
    if args.start_day:
        days = [day for day in days if day >= args.start_day]

    ds_era5, t2m, lats, lons, era5_transform, date_to_idx = load_era5_monthly(Path(args.era5).resolve())

    dem_arr, dem_prof = read_raster(Path(args.dem).resolve())
    slope_arr, slope_prof = read_raster(Path(args.slope).resolve())
    aspect_arr, aspect_prof = read_raster(Path(args.aspect).resolve())
    imp_arr, imp_prof = read_raster(Path(args.imp).resolve())
    lc_arr, lc_prof = read_raster(Path(args.lc).resolve())

    built = 0
    for day in days:
        day_date = parse_modis_day(day).date()
        if day_date not in date_to_idx:
            print(f"SKIP {day}: no ERA5 match in monthly file")
            continue

        day_dir = daily_dir / day
        lst_day_path = next(day_dir.glob("*_lst_day_c.tif"))
        lst_night_path = next(day_dir.glob("*_lst_night_c.tif"))
        qc_day_path = next(day_dir.glob("*_qc_day.tif"))
        qc_night_path = next(day_dir.glob("*_qc_night.tif"))

        lst_day, target_prof = read_raster(lst_day_path)
        lst_night, _ = read_raster(lst_night_path)
        qc_day, _ = read_raster(qc_day_path)
        qc_night, _ = read_raster(qc_night_path)

        target_shape = (target_prof["height"], target_prof["width"])
        target_transform = target_prof["transform"]
        target_crs = target_prof["crs"]
        nodata = target_prof["nodata"]

        era5_day = t2m[date_to_idx[day_date], :, :].astype(np.float32) - 273.15
        era5_resampled = reproject_to_target(
            era5_day,
            WGS84,
            era5_transform,
            target_shape,
            target_crs,
            target_transform,
            src_nodata=None,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )

        dem_resampled = reproject_to_target(
            dem_arr.astype(np.float32),
            dem_prof["crs"],
            dem_prof["transform"],
            target_shape,
            target_crs,
            target_transform,
            src_nodata=dem_prof["nodata"],
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
        slope_resampled = reproject_to_target(
            slope_arr.astype(np.float32),
            slope_prof["crs"],
            slope_prof["transform"],
            target_shape,
            target_crs,
            target_transform,
            src_nodata=slope_prof["nodata"],
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
        aspect_resampled = reproject_to_target(
            aspect_arr.astype(np.float32),
            aspect_prof["crs"],
            aspect_prof["transform"],
            target_shape,
            target_crs,
            target_transform,
            src_nodata=aspect_prof["nodata"],
            dst_nodata=np.nan,
            resampling=Resampling.nearest,
        )
        imp_resampled = reproject_to_target(
            imp_arr.astype(np.float32),
            imp_prof["crs"],
            imp_prof["transform"],
            target_shape,
            target_crs,
            target_transform,
            src_nodata=imp_prof["nodata"],
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
        lc_resampled = reproject_to_target(
            lc_arr.astype(np.float32),
            lc_prof["crs"],
            lc_prof["transform"],
            target_shape,
            target_crs,
            target_transform,
            src_nodata=lc_prof["nodata"],
            dst_nodata=-9999,
            resampling=Resampling.nearest,
        ).astype(np.int16)

        lst_day = np.where(lst_day == nodata, np.nan, lst_day.astype(np.float32))
        lst_night = np.where(lst_night == nodata, np.nan, lst_night.astype(np.float32))
        lst_mean = nanmean_two(lst_day, lst_night).astype(np.float32)

        valid_day = np.isfinite(lst_day).astype(np.uint8)
        valid_night = np.isfinite(lst_night).astype(np.uint8)
        valid_mean = np.isfinite(lst_mean).astype(np.uint8)

        npz_path = output_dir / f"{day}.npz"
        if args.skip_existing and npz_path.exists():
            print(f"SKIP {day}: existing npz")
            continue
        save_npz(
            npz_path,
            era5_t2m_c=era5_resampled.astype(np.float32),
            dem_m=dem_resampled.astype(np.float32),
            slope_deg=slope_resampled.astype(np.float32),
            aspect_deg=aspect_resampled.astype(np.float32),
            imp_proxy=imp_resampled.astype(np.float32),
            lc_type1_majority=lc_resampled,
            lst_day_c=lst_day.astype(np.float32),
            lst_night_c=lst_night.astype(np.float32),
            lst_mean_c=lst_mean.astype(np.float32),
            qc_day=qc_day.astype(np.uint8),
            qc_night=qc_night.astype(np.uint8),
            valid_day=valid_day,
            valid_night=valid_night,
            valid_mean=valid_mean,
        )

        built += 1
        print(f"BUILT {day}: valid_mean={int(valid_mean.sum())} era5_mean={float(np.nanmean(era5_resampled)):.2f}C lst_mean={float(np.nanmean(lst_mean)):.2f}C")

    manifest_path = output_dir / "manifest.json"
    manifest = rebuild_manifest(output_dir)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    ds_era5.close()
    print(f"Done. built={built} manifest={manifest_path}")


if __name__ == "__main__":
    main()
