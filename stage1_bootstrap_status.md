# Stage 1 Bootstrap 数据状态

更新时间: 2026-03-31

## 已确认的韩国 MODIS tiles

- `h27v05`
- `h28v05`
- `h29v05`

## 已经实际下载到本地的数据

### 1. MOD11A1

- 时间范围: `2018-01-01` 到 `2018-01-31`
- granule 数: `94`
- 本地目录: `25to1/data/stage1/raw/mod11a1`

说明:

- 包含 `2017-12-31` 的一个跨日 granule
- 其余是 `2018-01` 的日尺度 `3 tiles/day`
- 已生成 `31` 个完整日的拼接输出
- 日拼接输出目录: `25to1/data/stage1/interim/mod11a1_daily`

每天包含:

- `*_lst_day_c.tif`
- `*_lst_night_c.tif`
- `*_qc_day.tif`
- `*_qc_night.tif`

### 2. MCD12Q1

- 时间范围: `2018`
- granule 数: `3`
- 本地目录: `25to1/data/stage1/raw/mcd12q1`

已生成静态土地覆盖产物:

- `25to1/data/stage1/processed/mcd12q1_lc_type1_korea_500m.tif`
- `25to1/data/stage1/processed/mcd12q1_lc_type1_majority_korea_1km.tif`
- `25to1/data/stage1/processed/mcd12q1_imp_proxy_korea_1km.tif`

说明:

- `imp_proxy` 是依据 `LC_Type1` 中 `Urban and Built-up Lands = 13` 聚合得到的 `1 km` 城市建成区比例代理
- 这是合理复现近似，但不是论文作者公开说明过的精确 `Imp` 构造公式

### 3. ERA5 daily mean T2M

- 时间范围: `2018-01`
- 文件数: `1`
- 文件: `25to1/data/stage1/raw/era5_daily/era5_daily_t2m_2018_01.nc`

ERA5 文件检查:

- 文件头是 `HDF5/NetCDF4`
- 变量包含:
  - `latitude`
  - `longitude`
  - `number`
  - `t2m`
  - `valid_time`

补充:

- 在 `python312` 环境里可通过 `netCDF4.Dataset` 正常读取
- `xarray + netCDF4` 在当前中文绝对路径下有兼容问题，后续建议优先用相对路径或直接用 `netCDF4`
- 已与 `MOD11A1` 日栅格和静态因子对齐，生成简化版日特征栈

### 4. SRTMGL1

- 韩国 bbox granule 数: `44`
- 已下载 zip: `44`
- 已解压 hgt: `44`
- 清单文件: `25to1/data/stage1/interim/srtm_korea_preview.json`
- 原始目录: `25to1/data/stage1/raw/srtm`
- 解压目录: `25to1/data/stage1/raw/srtm/unpacked`

韩国范围 DEM 产物:

- `25to1/data/stage1/processed/srtm_dem_korea_wgs84.tif`
- `25to1/data/stage1/processed/srtm_slope_korea_wgs84.tif`
- `25to1/data/stage1/processed/srtm_aspect_korea_wgs84.tif`

说明:

- DEM CRS: `EPSG:4326`
- DEM 尺寸: `25200 x 23400`
- DEM 边界约: `124.50E-131.50E, 33.00N-39.50N`
- slope 范围约: `0.0° ~ 89.9°`
- aspect 范围约: `0.0° ~ 359.4°`

### 5. NDVI

- 采用产品: `MOD13A2 v061` 1 km 16-day NDVI
- 说明: 这是当前阶段为论文 NDVI 变量采用的合理近似方案，当前论文可见内容没有明确写出具体 MODIS NDVI 产品号
- 已下载时间片:
  - `A2018001`
  - `A2018017`
- 原始目录: `25to1/data/stage1/raw/ndvi`

已生成 NDVI composite:

- `25to1/data/stage1/processed/ndvi_composites/A2018001_ndvi.tif`
- `25to1/data/stage1/processed/ndvi_composites/A2018017_ndvi.tif`
- manifest: `25to1/data/stage1/processed/ndvi_composites/manifest.json`

补充:

- 已成功并入 `31` 天的简化版 `npz` 特征栈
- `npz` 新增字段: `ndvi`

### 6. python312 环境

当前已确认可用:

- `numpy`
- `requests`
- `xarray`
- `netCDF4`
- `cdsapi`
- `rasterio`
- `pyhdf`

已新增/可用脚本:

- `25to1/scripts/build_mod11a1_daily_mosaics.py`
- `25to1/scripts/derive_srtm_slope_aspect.py`
- `25to1/scripts/build_mcd12q1_static_features.py`
- `25to1/scripts/build_mod13a2_ndvi_composites.py`
- `25to1/scripts/augment_stage1_features_with_ndvi.py`
- `25to1/scripts/build_stage1_simplified_feature_stacks.py`

### 7. 简化版一阶段特征栈

- 目录: `25to1/data/stage1/processed/stage1_simplified_features`
- 已生成天数: `31`
- manifest: `25to1/data/stage1/processed/stage1_simplified_features/manifest.json`

每个 `npz` 目前包含:

- `era5_t2m_c`
- `dem_m`
- `slope_deg`
- `aspect_deg`
- `imp_proxy`
- `ndvi`
- `lc_type1_majority`
- `lst_day_c`
- `lst_night_c`
- `lst_mean_c`
- `qc_day`
- `qc_night`
- `valid_day`
- `valid_night`
- `valid_mean`

说明:

- 这是“简化版标签流水线”，目标是先把 Stage 1 训练样本组织起来
- 这里的 `lst_mean_c` 只是 `day/night` 的近似平均，不等于论文中的 `MODIS-derived air temperature`
- 它适合下一步快速验证数据管线和模型输入接口

## 还没开始下载或构造的数据

- `AWS / ASOS` 站点数据
- `incoming solar radiation`

## 当前最适合继续做的事情

1. 补 `incoming solar radiation`
2. 引入站点数据，拟合真正的 `MODIS-derived air temperature`
3. 再扩展到 `2018` 全年甚至 `2000-2020`
4. 开始搭一个简化版 Stage 1 baseline 模型验证数据接口

## Update 2026-03-31: incoming solar radiation added

- Source chosen for current approximation: ERA5 daily statistics `surface_solar_radiation_downwards` (`ssrd`)
- Raw NetCDF: `25to1/data/stage1/raw/solar_radiation/era5_daily_ssrd_2018_01.nc`
- Verified variables: `latitude`, `longitude`, `number`, `ssrd`, `valid_time`
- NetCDF `ssrd` metadata:
  - units: `J m**-2`
  - long_name: `Surface short-wave (solar) radiation downwards`
- Added script: `25to1/scripts/augment_stage1_features_with_solar_radiation.py`
- Updated script: `25to1/scripts/download_era5_daily.py`
- Updated `31` standard daily feature stacks with:
  - `solar_incoming_j_m2_day`
  - `solar_incoming_w_m2`
- Verification:
  - `A2018001.npz` solar mean: `10050044.0 J/m2/day`, `116.32 W/m2`
  - `A2018031.npz` solar mean: `9827590.0 J/m2/day`, `113.75 W/m2`

## Update 2026-03-31: KMA station data bootstrap added

- KMA login and day-fileset download flow confirmed working
- Confirmed usage purpose code for this project:
  - `F00408` = academic / research
- Returned file structure confirmed as:
  - outer application zip
  - inner data zip
  - final `cp949` CSV

Downloaded station files:

- ASOS day 2018:
  - outer zip: `25to1/data/stage1/raw/stations/SURFACE_ASOS_100_DAY_2018_2018_2019.zip`
  - extracted csv: `25to1/data/stage1/raw/stations/asos_2018/SURFACE_ASOS_100_DAY_2018_2018_2019.csv`
- AWS day 2018:
  - outer zip: `25to1/data/stage1/raw/stations/SURFACE_AWS_116_DAY_2018_2018_2019.zip`
  - extracted csv: `25to1/data/stage1/raw/stations/aws_2018/SURFACE_AWS_116_DAY_2018_2018_2019.csv`

Normalized UTF-8 station tables:

- `25to1/data/stage1/processed/stations/SURFACE_ASOS_100_DAY_2018_2018_2019_normalized.csv`
- `25to1/data/stage1/processed/stations/SURFACE_AWS_116_DAY_2018_2018_2019_normalized.csv`
- manifest: `25to1/data/stage1/processed/stations/manifest.json`

Row counts:

- ASOS 2018 normalized rows: `365`
- AWS 2018 normalized rows: `365`

Added scripts:

- `25to1/scripts/download_kma_station_fileset.py`
- `25to1/scripts/normalize_kma_daily_station_csv.py`

## Update 2026-03-31: station metadata + collocations added

Built station metadata from KMA detail pages:

- `25to1/data/stage1/processed/stations/station_metadata_bootstrap.csv`
- `25to1/data/stage1/processed/stations/station_metadata_bootstrap.json`

Bootstrap station metadata:

- ASOS `100`: lat `37.67713`, lon `128.71834`, elev `772.43 m`
- AWS `116`: lat `37.44526`, lon `126.96402`, elev `624.82 m`

Built January 2018 station-to-grid collocations:

- `25to1/data/stage1/processed/station_collocations/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations/stage1_station_collocations_2018_01_summary.json`

Collocation summary:

- rows: `62`
- sources: `asos`, `aws`
- station count: `2`
- date range: `2018-01-01` to `2018-01-31`

Each collocation row currently includes:

- station target fields such as `station_avg_temp_c`, `station_min_temp_c`, `station_max_temp_c`
- station-side daily variables such as precipitation, wind, humidity, pressure, solar where available
- colocated grid features from the Stage-1 simplified stacks such as:
  - `era5_t2m_c`
  - `dem_m`
  - `slope_deg`
  - `aspect_deg`
  - `imp_proxy`
  - `lc_type1_majority`
  - `lst_day_c`
  - `lst_night_c`
  - `lst_mean_c`

## Update 2026-03-31: bootstrap Stage 1 baseline trained

Added baseline training script:

- `25to1/scripts/train_stage1_station_baseline.py`

Generated baseline result folders:

- `25to1/data/stage1/models/station_baseline_jan2018/time_split`
- `25to1/data/stage1/models/station_baseline_jan2018/holdout_station_100`
- `25to1/data/stage1/models/station_baseline_jan2018/holdout_station_116`

Generated summary note:

- `25to1/stage1_baseline_results.md`

Time-split January 2018 result:

- train dates: `2018-01-01` to `2018-01-20`
- test dates: `2018-01-21` to `2018-01-31`
- `era5_only`: `MAE 4.124`, `RMSE 4.539`, `R2 0.337`
- `linear_regression`: `MAE 1.775`, `RMSE 2.056`, `R2 0.864`
- `random_forest`: `MAE 2.510`, `RMSE 3.166`, `R2 0.677`

Leave-one-station-out result:

- hold out station `100`:
  - `era5_only`: `MAE 3.374`, `RMSE 3.762`, `R2 0.554`
  - `linear_regression`: `MAE 1.657`, `RMSE 2.174`, `R2 0.851`
  - `random_forest`: `MAE 1.658`, `RMSE 2.162`, `R2 0.853`
- hold out station `116`:
  - `era5_only`: `MAE 3.611`, `RMSE 3.996`, `R2 0.579`
  - `linear_regression`: `MAE 1.434`, `RMSE 1.781`, `R2 0.916`
  - `random_forest`: `MAE 1.671`, `RMSE 2.000`, `R2 0.895`

Current interpretation:

- The bootstrap feature stack already beats raw `ERA5` clearly.
- The result is still only a bootstrap verification because it uses `2` stations and `2018-01` only.
- The current target is station daily mean temperature, not the full paper-level `MODIS-derived air temperature`.

## Update 2026-03-31: ASOS station expansion scaffold added

Added scripts for batch station expansion:

- `25to1/scripts/list_kma_station_filesets.py`
- `25to1/scripts/fetch_kma_station_detail_pages.py`
- `25to1/scripts/build_kma_station_metadata_table.py`

Updated scripts:

- `25to1/scripts/download_kma_station_fileset.py`
  - now supports `--station-id`
- `25to1/scripts/build_stage1_station_collocations.py`
  - now supports multiple normalized station CSV inputs via `--station-csvs`

Added official ASOS candidate list:

- `25to1/data/stage1/interim/kma_asos_candidate_stations_62.csv`

Batch-fetched public station detail pages:

- directory: `25to1/data/stage1/interim/kma_station_details_asos62`
- saved detail HTML count: `64`

Built batch ASOS station metadata:

- `25to1/data/stage1/processed/stations/station_metadata_asos62.csv`
- `25to1/data/stage1/processed/stations/station_metadata_asos62.json`
- `25to1/data/stage1/processed/stations/station_metadata_asos62_summary.json`

Current ASOS metadata summary:

- row count: `64`
- latitude range: `33.24616` to `38.25085`
- longitude range: `124.71237` to `130.89863`

Interpretation:

- We now have a much broader official station metadata base than the original `2`-station bootstrap.
- The remaining bottleneck is no longer station location metadata, but downloading and normalizing the matching daily ASOS filesets for these stations.
  - `ndvi`
  - `solar_incoming_j_m2_day`
  - `solar_incoming_w_m2`
  - validity / QC fields

Added scripts:

- `25to1/scripts/build_kma_station_metadata.py`
- `25to1/scripts/build_stage1_station_collocations.py`
