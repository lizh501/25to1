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

## Update 2026-04-01: multi-station January ASOS downloads working

Validated station-query-based KMA download flow for daily ASOS filesets:

- `25to1/scripts/download_kma_station_fileset.py`
  - now supports real-time query lookup by `--station-id`
  - validated with `--lookup-mode search`

Newly downloaded ASOS daily 2018 files:

- station `105`
- station `108`
- station `143`
- station `159`
- station `184`

Extracted raw CSV directory:

- `25to1/data/stage1/raw/stations/asos_day_2018`

Normalized new UTF-8 station tables:

- `25to1/data/stage1/processed/stations/SURFACE_ASOS_105_DAY_2018_2018_2019_normalized.csv`
- `25to1/data/stage1/processed/stations/SURFACE_ASOS_108_DAY_2018_2018_2019_normalized.csv`
- `25to1/data/stage1/processed/stations/SURFACE_ASOS_143_DAY_2018_2018_2019_normalized.csv`
- `25to1/data/stage1/processed/stations/SURFACE_ASOS_159_DAY_2018_2018_2019_normalized.csv`
- `25to1/data/stage1/processed/stations/SURFACE_ASOS_184_DAY_2018_2018_2019_normalized.csv`

Added helper script:

- `25to1/scripts/build_station_metadata_subset.py`

Built January 7-station metadata subset:

- `25to1/data/stage1/processed/stations/station_metadata_stage1_jan7.csv`

Built January 7-station collocations:

- `25to1/data/stage1/processed/station_collocations_jan7/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations_jan7/stage1_station_collocations_2018_01_summary.json`

7-station collocation summary:

- rows: `217`
- sources: `asos`, `aws`
- station ids: `100`, `105`, `108`, `116`, `143`, `159`, `184`

Built January 7-station baseline outputs:

- `25to1/data/stage1/models/station_baseline_jan7/time_split`
- `25to1/data/stage1/models/station_baseline_jan7/holdout_station_108`
- `25to1/data/stage1/models/station_baseline_jan7/holdout_station_159`

7-station time-split headline result:

- `era5_only`: `MAE 2.058`, `RMSE 2.753`, `R2 0.846`
- `linear_regression_grid_only`: `MAE 1.465`, `RMSE 1.765`, `R2 0.937`
- `random_forest_grid_only`: `MAE 1.920`, `RMSE 2.526`, `R2 0.870`

## Update 2026-04-01: full-65 January station set built

Added batch ASOS download script:

- `25to1/scripts/download_kma_station_batch.py`

Optimized collocation script:

- `25to1/scripts/build_stage1_station_collocations.py`
  - now caches station pixel locations
  - now samples Stage-1 `npz` stacks by day instead of reopening per record
  - now supports `--station-csv-dir` plus glob patterns

Full January station coverage now available:

- ASOS normalized 2018 station tables: `64`
- AWS normalized 2018 station tables: `1`
- total station count used for the current full set: `65`

Built full January metadata subset:

- `25to1/data/stage1/processed/stations/station_metadata_stage1_full65.csv`

Built full January collocations:

- `25to1/data/stage1/processed/station_collocations_full65/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations_full65/stage1_station_collocations_2018_01_summary.json`

Full collocation summary:

- rows: `2015`
- date range: `2018-01-01` to `2018-01-31`
- station count: `65`

Built full January baseline outputs:

- `25to1/data/stage1/models/station_baseline_full65/time_split`
- `25to1/data/stage1/models/station_baseline_full65/holdout_station_108`

Full-65 time-split headline result:

- `era5_only`: `MAE 1.638`, `RMSE 2.050`, `R2 0.870`
- `linear_regression`: `MAE 1.545`, `RMSE 1.897`, `R2 0.889`
- `linear_regression_grid_only`: `MAE 1.559`, `RMSE 1.921`, `R2 0.886`

Full-65 holdout station `108` headline result:

- `era5_only`: `MAE 1.136`, `RMSE 1.422`, `R2 0.935`
- `random_forest_grid_only`: `MAE 1.064`, `RMSE 1.293`, `R2 0.946`

Current interpretation:

- We now have a much more realistic January Stage-1 engineering dataset than the earlier `2`-station and `7`-station bootstrap versions.
- The next high-value step is no longer more January station expansion, but extending this full station set from one month toward longer time coverage.
  - `ndvi`
  - `solar_incoming_j_m2_day`
  - `solar_incoming_w_m2`
  - validity / QC fields

Added scripts:

- `25to1/scripts/build_kma_station_metadata.py`
- `25to1/scripts/build_stage1_station_collocations.py`

## Update 2026-04-01: February 2018 extension completed

Extended Stage-1 gridded inputs from January into February 2018:

- downloaded `MOD11A1` for `A2018032` to `A2018059`
- downloaded `ERA5 daily T2M` for `2018-02`
- downloaded `ERA5 daily SSRD` for `2018-02`
- downloaded `MOD13A2` composites needed for February / early March carry-over

New or updated artifacts:

- `25to1/data/stage1/raw/era5_daily/era5_daily_t2m_2018_02.nc`
- `25to1/data/stage1/raw/solar_radiation/era5_daily_ssrd_2018_02.nc`
- `25to1/data/stage1/interim/mod11a1_2018_02_manifest.json`
- `25to1/data/stage1/interim/mod13a2_2018_02_03_manifest.json`
- `25to1/data/stage1/processed/ndvi_composites/manifest.json`

Completed February daily MOD11A1 mosaics:

- `25to1/data/stage1/interim/mod11a1_daily/A2018032`
- ...
- `25to1/data/stage1/interim/mod11a1_daily/A2018059`

Completed January+February simplified feature stacks:

- standard day-count: `59`
- coverage: `2018-01-01` to `2018-02-28`
- directory: `25to1/data/stage1/processed/stage1_simplified_features`

Feature-stack script improvements:

- `25to1/scripts/build_mod11a1_daily_mosaics.py`
  - added `--start-day`
  - added `--skip-existing`
- `25to1/scripts/build_stage1_simplified_feature_stacks.py`
  - added multi-file `ERA5` loading with `--era5-dir` and `--era5-glob`
  - switched static raster reprojection to stream from raster files instead of loading full-country arrays into memory
- `25to1/scripts/augment_stage1_features_with_solar_radiation.py`
  - added multi-file solar loading with `--solar-dir` and `--solar-glob`

Rebuilt feature augmentations across the full January+February set:

- `ndvi` now available for all `59` standard daily `npz`
- `solar_incoming_j_m2_day` now available for all `59` standard daily `npz`
- `solar_incoming_w_m2` now available for all `59` standard daily `npz`

Built January+February full-65 collocations:

- `25to1/data/stage1/processed/station_collocations_full65_janfeb/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations_full65_janfeb/stage1_station_collocations_2018_01_summary.json`

Important note:

- the above collocation file name still carries the historical `2018_01` suffix, but the actual content spans `2018-01-01` to `2018-02-28`

January+February collocation summary:

- rows: `3835`
- date range: `2018-01-01` to `2018-02-28`
- station count: `65`

Built January-train / February-test baseline outputs:

- `25to1/data/stage1/models/station_baseline_full65_janfeb/time_split_jan_train_feb_test`
- `25to1/data/stage1/models/station_baseline_full65_janfeb/holdout_station_108`

January-train / February-test headline result:

- `era5_only`: `MAE 1.295`, `RMSE 1.686`, `R2 0.885`
- `linear_regression`: `MAE 1.122`, `RMSE 1.435`, `R2 0.917`
- `linear_regression_grid_only`: `MAE 1.135`, `RMSE 1.452`, `R2 0.915`

January+February holdout station `108` headline result:

- `era5_only`: `MAE 0.944`, `RMSE 1.213`, `R2 0.945`
- `linear_regression`: `MAE 0.932`, `RMSE 1.194`, `R2 0.947`
- `linear_regression_grid_only`: `MAE 0.993`, `RMSE 1.236`, `R2 0.943`

Current interpretation:

- The Stage-1 bootstrap dataset is no longer January-only; it now supports a basic cross-month test.
- Extending from January to February improves confidence that the current feature stack generalizes beyond a single-month engineering sandbox.
- The next meaningful gain is to continue extending time coverage toward `2018 Q1` or full-year `2018`, then move from the station bootstrap target toward the paper's actual `MODIS-derived air temperature` label construction.

## Update 2026-04-01: March 2018 extension completed

Extended Stage-1 gridded inputs from January-February into full `2018 Q1`:

- downloaded `MOD11A1` for `A2018060` to `A2018090`
- downloaded `ERA5 daily T2M` for `2018-03`
- downloaded `ERA5 daily SSRD` for `2018-03`
- downloaded `MOD13A2` composites needed for March carry-over

New or updated artifacts:

- `25to1/data/stage1/raw/era5_daily/era5_daily_t2m_2018_03.nc`
- `25to1/data/stage1/raw/solar_radiation/era5_daily_ssrd_2018_03.nc`
- `25to1/data/stage1/interim/mod11a1_2018_03_manifest.json`
- `25to1/data/stage1/interim/mod13a2_2018_03_04_manifest.json`
- `25to1/data/stage1/processed/ndvi_composites/manifest.json`

Completed March daily MOD11A1 mosaics:

- `25to1/data/stage1/interim/mod11a1_daily/A2018060`
- ...
- `25to1/data/stage1/interim/mod11a1_daily/A2018090`

Completed Q1 simplified feature stacks:

- standard day-count: `90`
- coverage: `2018-01-01` to `2018-03-31`
- directory: `25to1/data/stage1/processed/stage1_simplified_features`

March NDVI composite coverage added:

- `A2018065`
- `A2018081`

Feature-pipeline script improvements:

- `25to1/scripts/augment_stage1_features_with_solar_radiation.py`
  - now copies loaded arrays before overwrite on Windows
  - now writes through a temporary `.npz` and atomically replaces the target file
  - this fixes intermittent `PermissionError` failures during in-place `npz` updates

Rebuilt feature augmentations across the full Q1 set:

- `ndvi` now available for all `90` standard daily `npz`
- `solar_incoming_j_m2_day` now available for all `90` standard daily `npz`
- `solar_incoming_w_m2` now available for all `90` standard daily `npz`

Built Q1 full-65 collocations:

- `25to1/data/stage1/processed/station_collocations_full65_q1/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations_full65_q1/stage1_station_collocations_2018_01_summary.json`

Important note:

- the above collocation file name still carries the historical `2018_01` suffix, but the actual content spans `2018-01-01` to `2018-03-31`

Q1 collocation summary:

- rows: `5850`
- date range: `2018-01-01` to `2018-03-31`
- station count: `65`

Built Jan-Feb-train / March-test baseline outputs:

- `25to1/data/stage1/models/station_baseline_full65_q1/time_split_janfeb_train_mar_test`
- `25to1/data/stage1/models/station_baseline_full65_q1/holdout_station_108`

Jan-Feb-train / March-test headline result:

- `era5_only`: `MAE 1.409`, `RMSE 1.816`, `R2 0.853`
- `linear_regression`: `MAE 1.456`, `RMSE 1.913`, `R2 0.837`
- `linear_regression_grid_only`: `MAE 1.461`, `RMSE 1.921`, `R2 0.835`

Q1 holdout station `108` headline result:

- `era5_only`: `MAE 0.999`, `RMSE 1.280`, `R2 0.968`
- `linear_regression`: `MAE 0.874`, `RMSE 1.136`, `R2 0.975`
- `linear_regression_grid_only`: `MAE 0.951`, `RMSE 1.192`, `R2 0.972`

Current interpretation:

- We now have a complete Q1 engineering dataset for the Stage-1 bootstrap target.
- The cross-month result is harder in March than in February, and the simple linear baseline no longer beats raw `ERA5` on the March holdout month.
- That behavior is useful: it suggests Q1 is already exposing seasonal shift, which is exactly the kind of signal we want before moving on to the paper's true label-construction stage.

## Update 2026-04-01: bootstrap MODIS-derived AT surrogate built

We then moved one step closer to the paper's Stage-1 label-construction workflow by training a simple station-to-grid surrogate and applying it to the full Q1 1-km feature stacks.

Added script:

- `25to1/scripts/build_stage1_modis_at_bootstrap.py`

What this script does:

- trains a grid-only regression model on the full `Q1` station collocation set
- uses the existing Stage-1 feature stack (`ERA5`, `DEM`, `slope`, `aspect`, `imp`, `land cover`, `LST`, `NDVI`, `solar`) to predict daily 1-km air temperature
- writes a daily GeoTIFF label raster plus a valid-mask raster

Important scope note:

- this is still a bootstrap surrogate for `MODIS-derived air temperature`, not the paper's final official label-construction recipe
- it is useful as a working engineering label product for Stage-1 dataset assembly and model debugging

Model and output artifacts:

- `25to1/data/stage1/models/modis_at_bootstrap_q1/linear_regression_grid_only.joblib`
- `25to1/data/stage1/models/modis_at_bootstrap_q1/training_summary.json`
- `25to1/data/stage1/processed/modis_at_bootstrap_q1/manifest.json`

Per-day output layout:

- `25to1/data/stage1/processed/modis_at_bootstrap_q1/A2018001/A2018001_modis_at_bootstrap_c.tif`
- `25to1/data/stage1/processed/modis_at_bootstrap_q1/A2018001/A2018001_modis_at_bootstrap_valid.tif`
- ...
- `25to1/data/stage1/processed/modis_at_bootstrap_q1/A2018090/A2018090_modis_at_bootstrap_c.tif`

Bootstrap MODIS-AT surrogate summary:

- days built: `90`
- coverage: `2018-01-01` to `2018-03-31`
- training rows: `5845`
- training fit (`linear_regression`, grid-only):
  - `MAE 1.262`
  - `RMSE 1.629`
  - `R2 0.943`

Inference-side safeguards added:

- prediction now requires both `valid_mean == 1` and valid static land inputs
- invalid `DEM` sentinel values (for example `<= -10000`) are excluded from prediction
- negative `land-cover` sentinel values are excluded from prediction

This fix was necessary because an earlier first pass produced unrealistic extremes by letting nodata-coded static values leak into model inference.

Post-fix raster sanity check:

- across the Q1 manifest, daily prediction minima and maxima now fall roughly within `-29.54°C` to `19.39°C`
- example `A2018090` raster mean: `12.74°C`
- example `A2018090` raster range: `4.46°C` to `18.11°C`

Current interpretation:

- We now have a concrete daily 1-km pseudo-label raster product rather than only point collocations.
- That means the next step can finally move from "station baseline engineering" toward "full Stage-1 patch dataset assembly" using a spatial label field.

## Update 2026-04-01: Q1 Stage-1 patch index built

We then converted the Q1 feature stacks plus bootstrap MODIS-AT surrogate rasters into a training-ready patch index.

Added script:

- `25to1/scripts/build_stage1_patch_index.py`

Bootstrap patch-index configuration used for the first pass:

- patch size: `64`
- stride: `64`
- minimum valid-label fraction: `0.50`
- split date: `2018-03-01`
  - `train`: `2018-01-01` to `2018-02-28`
  - `test`: `2018-03-01` to `2018-03-31`

Artifacts:

- `25to1/data/stage1/processed/stage1_patch_index_q1_ps64_s64_v50/stage1_patch_index.csv`
- `25to1/data/stage1/processed/stage1_patch_index_q1_ps64_s64_v50/stage1_patch_index_summary.json`

Patch-index summary:

- indexed days with at least one valid patch: `85`
- total patches: `2132`
- training patches: `1325`
- test patches: `807`

Interpretation:

- We now have a concrete, date-split Stage-1 patch manifest rather than only daily rasters.
- This is enough to move on to a first real Stage-1 super-resolution training dataloader without redoing data preparation.
- Some cloud-heavy days naturally contribute zero patches under the current `50%` valid-label threshold, which is expected and consistent with the paper's missing-label challenge.

## Update 2026-04-01: first Stage-1 patch CNN sanity training completed

We then trained the first end-to-end Stage-1 patch-level CNN sanity baseline on the bootstrap patch dataset.

Added script:

- `25to1/scripts/train_stage1_patch_cnn.py`

Training artifacts:

- `25to1/data/stage1/models/stage1_patch_cnn_q1_ps64_s64_v50/best_model.pt`
- `25to1/data/stage1/models/stage1_patch_cnn_q1_ps64_s64_v50/training_summary.json`
- `25to1/stage1_patch_training_results.md`

Run configuration:

- device: `cuda`
- epochs: `2`
- batch size: `16`
- train patches: `1325`
- test patches: `807`

Headline sanity-check result:

- epoch 1 test: `MAE 0.241`, `RMSE 0.325`
- epoch 2 test: `MAE 0.173`, `RMSE 0.245`

Current interpretation:

- The Stage-1 patch dataloader, mask-aware loss, patch sampling, and checkpoint pipeline are now fully runnable.
- This is an engineering milestone, not yet a strict paper-level reproduction result.
- The current patch labels are generated from a bootstrap surrogate trained on the full `Q1` collocation set, so these patch metrics should be treated as pipeline-validation metrics rather than leakage-free benchmark numbers.
