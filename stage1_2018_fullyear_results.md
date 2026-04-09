# Stage 1 2018 Full-Year Results

## 1. Goal

This report consolidates the first complete `2018-01-01` to `2018-12-31` Stage-1 paper-like pipeline run:

- finish `2018 Q4` raw data and daily feature stacks
- build full-year station-grid collocations
- train paper-like `MODIS-derived AT` label models
- generate daily `1 km` pseudo-label grids
- build full-year paper-like `SCM climatology`
- summarize the main numerical findings and remaining gaps against the paper

## 2. Data Coverage

### 2.1 Raw / intermediate data completed

- `MOD11A1 v061`: full year daily mosaics now available through `A2018365`
- `MOD13A2 v061`: `1 km 16-day NDVI` composites extended through `2018 Q4`
- `ERA5 daily T2M`: full year `2018-01` to `2018-12`
- `ERA5 daily SSRD`: full year `2018-01` to `2018-12`
- `KMA stations`: combined `ASOS + AWS` normalized daily tables used for full-year collocation

### 2.2 Main outputs

- Full-year collocation summary:
  `25to1/data/stage1/processed/station_collocations_asos64_aws_chunk420_2018full/stage1_station_collocations_2018_01_summary.json`
- Paper-like dataset summary:
  `25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws_chunk420_2018full/stage1_modis_at_paperlike_dataset_summary.json`
- Trained label model summary:
  `25to1/data/stage1/models/modis_at_paperlike_asos64_aws_chunk420_2018full/training_summary.json`
- Daily paper-like label grids:
  `25to1/data/stage1/processed/modis_at_paperlike_grids_linear_clip_2018full/manifest.json`
- Full-year paper-like SCM:
  `25to1/data/stage1/processed/scm_paperlike_linear_clip_2018full/manifest.json`

## 3. Space / Time Scale

### 3.1 Spatial scale

- Target grid: about `1 km`
- Region: South Korea domain used in the current Stage-1 workflow
- Output form:
  - station-grid collocation table
  - daily `1 km` pseudo-label rasters
  - `365`-DOY SCM climatology rasters

### 3.2 Temporal scale

- Daily feature stacks: `2018-01-01` to `2018-12-31`
- Full-year collocations: `2018-01-01` to `2018-12-31`
- Daily label grids: near-complete 2018 daily sequence
- SCM climatology: `365` day-of-year maps, based on the available 2018 daily label grids

## 4. Collocation Summary

From `station_collocations_asos64_aws_chunk420_2018full`:

- total rows: `159,915`
- date range: `2018-01-01` to `2018-12-31`
- sources: `ASOS + AWS`
- total station IDs in collocation table: `443`

This is the first full-year Stage-1 station-grid table in the current reproduction workflow.

## 5. Paper-like Label Dataset

From `modis_at_paperlike_dataset_asos64_aws_chunk420_2018full`:

- dataset rows: `158,302`
- `AWS train` rows: `135,091`
- `ASOS validate` rows: `23,211`
- train stations: `379`
- validate stations: `64`

Current feature columns:

- `lst_prev_daytime_c`
- `lst_prev_nighttime_c`
- `lst_curr_daytime_c`
- `lst_curr_nighttime_c`
- `solar_incoming_w_m2`
- `ndvi`
- `lat`
- `lon`
- `dem_m`
- `aspect_deg`
- `imp_proxy`

Target:

- `target_station_avg_temp_c`

## 6. Model Results

### 6.1 Paper-style split: AWS train -> ASOS validate

From `training_summary.json`:

- `same_day_lst_mean`: `RMSE = 4.893`
- `four_obs_lst_mean`: `RMSE = 4.446`
- `linear_regression`: `RMSE = 5.781`
- `random_forest`: `RMSE = 4.106`

Main reading:

- The best current full-year Stage-1 label model is `random_forest`
- Adding more stations continues to help, but this is still far from the paper's reported label accuracy
- In the current pipeline, a nonlinear model is clearly more effective than the linear baseline

### 6.2 Pooled time split: train before 2018-10-01, test on 2018 Q4

- `same_day_lst_mean`: `RMSE = 4.033`
- `four_obs_lst_mean`: `RMSE = 3.511`
- `linear_regression`: `RMSE = 4.956`
- `random_forest`: `RMSE = 4.521`

Main reading:

- The `four_obs_lst_mean` baseline remains strong
- The current learned paper-like model still does not beat the stronger LST-only heuristic in this pooled time split
- This suggests the main Stage-1 gap is still label-system quality rather than model complexity

## 7. Daily Paper-like 1 km Grids

The full-year daily paper-like label grids were generated with the trained linear model and clipped to:

- minimum: `-25 C`
- maximum: `40 C`

This clipping was intentionally kept conservative to prevent obviously nonphysical temperature artifacts from propagating into climatology construction.

## 8. Full-Year Paper-like SCM

From `scm_paperlike_linear_clip_2018full/manifest.json`:

- daily items used: `363`
- raw-observation DOY count: `363 / 365`
- output climatology maps: full `365` DOY sequence after smoothing and filling
- smoothing window: `11`
- fill iterations: `10`

This means the current pipeline can now build a complete annual `SCM climatology` structure that is much closer to the paper's intended Stage-1 SCM than the earlier monthly or rolling proxy versions.

## 9. Most Important Limitation

The anomaly-standardized SCM was **not** produced for 2018-only data.

Reason recorded by the pipeline:

`With only one year per day-of-year, calendar-day ERA5 std is undefined; multi-year coverage is needed.`

This is scientifically expected and is the key reason the next priority must be extending the daily label system to multiple years, beginning with `2019`.

## 10. Comparison Against the Paper

What is now much closer to the paper:

- full-year daily Stage-1 feature coverage
- paper-like daily label-grid generation
- `365`-DOY SCM climatology construction
- explicit recognition that anomaly-SCM requires multi-year coverage

What still materially differs from the paper:

- current label target is still a practical paper-like approximation, not the paper's final label recipe
- time coverage is still too short for anomaly-standardized SCM
- the current accuracy is still much weaker than the paper's reported Stage-1 label performance

## 11. Decision

The correct next step is:

1. extend raw data and daily features to `2019`
2. rebuild `2018-2019` daily paper-like label grids
3. rebuild SCM using a multi-year day-of-year basis
4. rerun Stage-1 models and evaluate whether anomaly-standardized SCM begins to provide real gains

## 12. Bottom Line

The `2018` work is no longer a partial bootstrap. It is now a complete full-year Stage-1 engineering baseline with:

- full-year raw-data coverage
- full-year station-grid collocations
- full-year paper-like label modeling
- full-year daily `1 km` pseudo-label grids
- full-year `365`-DOY SCM climatology

The biggest remaining scientific gap is no longer Q4 coverage. It is the absence of multi-year daily label support, which is exactly why `2019` is the next priority.
