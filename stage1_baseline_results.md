# Stage 1 Bootstrap Baseline Results

Updated: 2026-03-31

## Scope

This is a bootstrap Stage 1 baseline built from the January 2018 collocation table:

- Dataset: `25to1/data/stage1/processed/station_collocations/stage1_station_collocations_2018_01.csv`
- Target: `station_avg_temp_c`
- Station count: `2`
- Sample count: `62`

The current goal is not to reproduce the paper's final Stage 1 label model yet. Instead, this baseline verifies that the data chain is runnable end to end:

- `MOD11A1`
- `ERA5 daily T2M`
- `DEM / slope / aspect`
- `MCD12Q1 land cover / imp proxy`
- `NDVI`
- `incoming solar radiation`
- `KMA ASOS / AWS station observations`

## Feature Set

Grid-side continuous features:

- `era5_t2m_c`
- `dem_m`
- `slope_deg`
- `aspect_deg`
- `imp_proxy`
- `lc_type1_majority`
- `lst_day_c`
- `lst_night_c`
- `lst_mean_c`
- `ndvi`
- `solar_incoming_w_m2`
- `valid_day`
- `valid_night`
- `valid_mean`

Optional categorical feature:

- `source`

## Time Split Result

Experiment:

- Train dates: `2018-01-01` to `2018-01-20`
- Test dates: `2018-01-21` to `2018-01-31`
- Train rows: `40`
- Test rows: `22`
- Output dir: `25to1/data/stage1/models/station_baseline_jan2018/time_split`

Metrics:

- `era5_only`: `MAE 4.124`, `RMSE 4.539`, `R2 0.337`
- `linear_regression`: `MAE 1.775`, `RMSE 2.056`, `R2 0.864`
- `random_forest`: `MAE 2.510`, `RMSE 3.166`, `R2 0.677`
- `linear_regression_grid_only`: `MAE 1.775`, `RMSE 2.056`, `R2 0.864`
- `random_forest_grid_only`: `MAE 2.461`, `RMSE 3.102`, `R2 0.690`

Observation:

- Even this small bootstrap feature stack improves clearly over raw `ERA5`.
- `source` did not change the linear regression result in this January bootstrap run.

## Leave-One-Station-Out Results

### Hold Out Station 100

Experiment:

- Train station: `116`
- Test station: `100`
- Train rows: `31`
- Test rows: `31`
- Output dir: `25to1/data/stage1/models/station_baseline_jan2018/holdout_station_100`

Metrics:

- `era5_only`: `MAE 3.374`, `RMSE 3.762`, `R2 0.554`
- `linear_regression`: `MAE 1.657`, `RMSE 2.174`, `R2 0.851`
- `random_forest`: `MAE 1.658`, `RMSE 2.162`, `R2 0.853`
- `linear_regression_grid_only`: `MAE 1.657`, `RMSE 2.174`, `R2 0.851`
- `random_forest_grid_only`: `MAE 1.696`, `RMSE 2.207`, `R2 0.847`

### Hold Out Station 116

Experiment:

- Train station: `100`
- Test station: `116`
- Train rows: `31`
- Test rows: `31`
- Output dir: `25to1/data/stage1/models/station_baseline_jan2018/holdout_station_116`

Metrics:

- `era5_only`: `MAE 3.611`, `RMSE 3.996`, `R2 0.579`
- `linear_regression`: `MAE 1.434`, `RMSE 1.781`, `R2 0.916`
- `random_forest`: `MAE 1.671`, `RMSE 2.000`, `R2 0.895`
- `linear_regression_grid_only`: `MAE 1.434`, `RMSE 1.781`, `R2 0.916`
- `random_forest_grid_only`: `MAE 1.664`, `RMSE 1.994`, `R2 0.895`

Observation:

- Under this bootstrap setup, cross-station generalization is still noticeably better than `ERA5` alone.
- Because there are only `2` stations, these results are encouraging but still too optimistic to treat as a paper-level reproduction result.

## Current Limitation

- This baseline predicts station daily mean temperature, not the paper's full `MODIS-derived air temperature` target.
- Only `2` stations are included so far.
- Only `2018-01` is included so far.
- The current `imp_proxy` is a reasonable proxy, not the paper author's explicitly released `Imp` formulation.
- The current `NDVI` choice is a practical approximation using `MOD13A2 v061`.

## Next Best Step

The next most useful Stage 1 step is:

1. Expand station coverage beyond the current `2` bootstrap stations.
2. Scale the collocations from `2018-01` toward a longer temporal span.
3. Replace the bootstrap station target with a closer approximation to the paper's `MODIS-derived air temperature` label construction.

## Update 2026-04-01: January 7-station expansion

We expanded the January 2018 bootstrap set from `2` stations to `7` stations:

- ASOS: `100`, `105`, `108`, `143`, `159`, `184`
- AWS: `116`

Expanded metadata and collocation artifacts:

- `25to1/data/stage1/processed/stations/station_metadata_stage1_jan7.csv`
- `25to1/data/stage1/processed/station_collocations_jan7/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations_jan7/stage1_station_collocations_2018_01_summary.json`

Expanded collocation summary:

- rows: `217`
- date range: `2018-01-01` to `2018-01-31`
- station count: `7`

### 7-station time split

Experiment:

- train dates: `2018-01-01` to `2018-01-20`
- test dates: `2018-01-21` to `2018-01-31`
- train rows: `140`
- test rows: `77`
- output dir: `25to1/data/stage1/models/station_baseline_jan7/time_split`

Metrics:

- `era5_only`: `MAE 2.058`, `RMSE 2.753`, `R2 0.846`
- `linear_regression`: `MAE 1.468`, `RMSE 1.764`, `R2 0.937`
- `random_forest`: `MAE 1.903`, `RMSE 2.498`, `R2 0.873`
- `linear_regression_grid_only`: `MAE 1.465`, `RMSE 1.765`, `R2 0.937`
- `random_forest_grid_only`: `MAE 1.920`, `RMSE 2.526`, `R2 0.870`

Interpretation:

- After expanding to `7` stations, the January time-split baseline is materially more credible than the original `2`-station bootstrap.
- The current Stage-1 feature stack still improves over raw `ERA5`.

### 7-station holdout checks

Hold out station `108`:

- `era5_only`: `MAE 1.136`, `RMSE 1.422`, `R2 0.935`
- `random_forest_grid_only`: `MAE 1.777`, `RMSE 2.056`, `R2 0.864`
- `random_forest`: `MAE 1.672`, `RMSE 1.959`, `R2 0.876`
- `linear_regression_grid_only`: `MAE 2.837`, `RMSE 3.092`, `R2 0.692`
- `linear_regression`: unstable in this holdout setting and should not be trusted as the preferred cross-station estimate

Hold out station `159`:

- `era5_only`: `MAE 1.237`, `RMSE 1.560`, `R2 0.872`
- `linear_regression_grid_only`: `MAE 0.961`, `RMSE 1.190`, `R2 0.926`
- `random_forest_grid_only`: `MAE 1.588`, `RMSE 2.014`, `R2 0.787`
- `random_forest`: `MAE 1.594`, `RMSE 2.018`, `R2 0.786`
- `linear_regression`: `MAE 1.859`, `RMSE 2.151`, `R2 0.757`

Current interpretation:

- The January `7`-station set is already useful for debugging Stage-1 inputs and model behavior.
- Cross-station generalization is still station-dependent and should be treated as a diagnostic result, not a final paper-level reproduction metric.
- The next major gain will come from extending both station count and time span, rather than tuning the current January-only baseline too aggressively.

## Update 2026-04-01: January full-65-station expansion

We then expanded the January 2018 collocation set to the full currently available station pool:

- `64` ASOS stations
- `1` AWS station
- total stations: `65`

Expanded artifacts:

- `25to1/data/stage1/processed/stations/station_metadata_stage1_full65.csv`
- `25to1/data/stage1/processed/station_collocations_full65/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations_full65/stage1_station_collocations_2018_01_summary.json`

Expanded collocation summary:

- rows: `2015`
- date range: `2018-01-01` to `2018-01-31`
- station count: `65`

### Full-65 time split

Experiment:

- train dates: `2018-01-01` to `2018-01-20`
- test dates: `2018-01-21` to `2018-01-31`
- train rows: `1295`
- test rows: `715`
- output dir: `25to1/data/stage1/models/station_baseline_full65/time_split`

Metrics:

- `era5_only`: `MAE 1.638`, `RMSE 2.050`, `R2 0.870`
- `linear_regression`: `MAE 1.545`, `RMSE 1.897`, `R2 0.889`
- `random_forest`: `MAE 1.645`, `RMSE 2.070`, `R2 0.867`
- `linear_regression_grid_only`: `MAE 1.559`, `RMSE 1.921`, `R2 0.886`
- `random_forest_grid_only`: `MAE 1.644`, `RMSE 2.069`, `R2 0.868`

Interpretation:

- The Stage-1 feature stack still improves over raw `ERA5`, but the gain is now more modest on the larger `65`-station set.
- This is actually a healthier sign than the tiny bootstrap results because the task is now much less toy-like.

### Full-65 holdout check for station 108

Experiment:

- holdout station: `108`
- train rows: `1979`
- test rows: `31`
- output dir: `25to1/data/stage1/models/station_baseline_full65/holdout_station_108`

Metrics:

- `era5_only`: `MAE 1.136`, `RMSE 1.422`, `R2 0.935`
- `linear_regression`: `MAE 1.115`, `RMSE 1.362`, `R2 0.940`
- `random_forest`: `MAE 1.074`, `RMSE 1.301`, `R2 0.945`
- `linear_regression_grid_only`: `MAE 1.153`, `RMSE 1.387`, `R2 0.938`
- `random_forest_grid_only`: `MAE 1.064`, `RMSE 1.293`, `R2 0.946`

Current interpretation:

- Once the station pool is widened enough, the previously unstable holdout behavior becomes much more reasonable.
- The current January full-65 setup is a solid Stage-1 engineering checkpoint, even though it is still not the paper's final `MODIS-derived air temperature` target construction.

## Update 2026-04-01: January+February full-65 extension

We then extended the full-65 station bootstrap from January 2018 into February 2018.

Extended artifacts:

- `25to1/data/stage1/processed/station_collocations_full65_janfeb/stage1_station_collocations_2018_01.csv`
- `25to1/data/stage1/processed/station_collocations_full65_janfeb/stage1_station_collocations_2018_01_summary.json`
- `25to1/data/stage1/models/station_baseline_full65_janfeb/time_split_jan_train_feb_test/metrics_summary.json`
- `25to1/data/stage1/models/station_baseline_full65_janfeb/holdout_station_108/metrics_summary.json`

Important note:

- the collocation file name still keeps the legacy `2018_01` suffix, but the actual content spans `2018-01-01` to `2018-02-28`

Expanded collocation summary:

- rows: `3835`
- date range: `2018-01-01` to `2018-02-28`
- station count: `65`

### January-train / February-test time split

Experiment:

- train dates: `2018-01-01` to `2018-01-31`
- test dates: `2018-02-01` to `2018-02-28`
- train rows: `2010`
- test rows: `1820`
- output dir: `25to1/data/stage1/models/station_baseline_full65_janfeb/time_split_jan_train_feb_test`

Metrics:

- `era5_only`: `MAE 1.295`, `RMSE 1.686`, `R2 0.885`
- `linear_regression`: `MAE 1.122`, `RMSE 1.435`, `R2 0.917`
- `random_forest`: `MAE 1.148`, `RMSE 1.467`, `R2 0.913`
- `linear_regression_grid_only`: `MAE 1.135`, `RMSE 1.452`, `R2 0.915`
- `random_forest_grid_only`: `MAE 1.150`, `RMSE 1.468`, `R2 0.913`

Interpretation:

- This is a more meaningful temporal-generalization check than the earlier within-January split.
- The current Stage-1 feature stack still improves materially over raw `ERA5` when trained on January and tested on a full unseen month.
- The gap between `grid_only` and `grid_plus_source` remains small, which is a good sign that the gridded predictors themselves are carrying most of the signal.

### January+February holdout check for station 108

Experiment:

- holdout station: `108`
- train rows: `3771`
- test rows: `59`
- output dir: `25to1/data/stage1/models/station_baseline_full65_janfeb/holdout_station_108`

Metrics:

- `era5_only`: `MAE 0.944`, `RMSE 1.213`, `R2 0.945`
- `linear_regression`: `MAE 0.932`, `RMSE 1.194`, `R2 0.947`
- `random_forest`: `MAE 1.194`, `RMSE 1.433`, `R2 0.923`
- `linear_regression_grid_only`: `MAE 0.993`, `RMSE 1.236`, `R2 0.943`
- `random_forest_grid_only`: `MAE 1.191`, `RMSE 1.426`, `R2 0.924`

Interpretation:

- On the larger two-month set, the `linear_regression` baseline is currently the cleanest and most stable simple baseline for this bootstrap target.
- The spatial holdout result remains strong enough to justify continuing time expansion before spending effort on heavier model tuning.
