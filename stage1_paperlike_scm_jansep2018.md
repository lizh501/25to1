# Stage 1 Long-Timeseries Paper-like SCM Progress

## What Was Built

This round moved the focus back to the long-timeseries label system and the paper-like `SCM` pipeline.

Two key scripts are now in place:

- `25to1/scripts/build_stage1_modis_at_paperlike_grids.py`
- `25to1/scripts/build_stage1_scm_paperlike.py`

The daily paper-like label grids were generated for `2018-01-01` to `2018-09-30` using the current `linear_regression` paper-like label model and then clipped to a physically safer range:

- `clip_min = -25 C`
- `clip_max = 40 C`

Outputs:

- Daily paper-like grids:
  `25to1/data/stage1/processed/modis_at_paperlike_grids_linear_clip_jansep2018`
- Paper-like SCM:
  `25to1/data/stage1/processed/scm_paperlike_linear_clip_jansep2018`

## Daily Label Grid Results

Manifest:

- `25to1/data/stage1/processed/modis_at_paperlike_grids_linear_clip_jansep2018/manifest.json`

Key facts:

- Built days: `272`
- Coverage: `A2018001` to `A2018273`
- Missing day-of-year: `257`
- Valid pixels per day: `402421`
- Global predicted range after clipping: `[-25.0, 40.0] C`
- Mean clipped pixels per day: about `1799`
- Clip count range: `1685` to `3500`

Interpretation:

- The earlier unclipped linear daily grids occasionally reached unrealistic values above `100 C`.
- The clipping step is therefore important before building long-timeseries climatology products.
- The missing `DOY 257` comes from an upstream missing daily feature file rather than from the SCM code.

Approximate runtime on the current machine:

- Daily grid generation for `Jan-Sep 2018`: about `10.3 min`

## Paper-like SCM Results

Manifest:

- `25to1/data/stage1/processed/scm_paperlike_linear_clip_jansep2018/manifest.json`

Current SCM settings:

- day-of-year climatology: `365`
- smoothing window: `11`
- fill iterations: `10`
- source daily labels: `272` days

Key results:

- Raw-observation DOY count: `272`
- Climatology valid DOY count after smoothing/fill: `365`
- Climatology mean range: about `[8.28, 21.25] C`
- Example output directory:
  `25to1/data/stage1/processed/scm_paperlike_linear_clip_jansep2018/climatology_365`

Interpretation:

- This is the first paper-structured `SCM` run that actually uses a longer daily label library rather than monthly or short rolling proxies.
- The `365` climatology maps are now available and can already be used as a more paper-like SCM prior than the older bootstrap proxies.

Approximate runtime on the current machine:

- SCM build for `Jan-Sep 2018`: about `23.2 min`

## Important Limitation

`anomaly_standardized_365` is not yet usable in a scientifically honest way with only `2018 Jan-Sep`.

Why:

- The paper standardizes using calendar-day ERA5 mean and standard deviation over a long period.
- With only one year per day-of-year, the calendar-day ERA5 standard deviation is undefined.
- That is why the anomaly-standardized output is effectively empty in the current run.

This is not a code failure in the main climatology branch. It is a data-span limitation.

## Practical Conclusion

The project now has:

1. A workable paper-like daily label-grid generator.
2. A first long-timeseries paper-like `SCM` climatology product.
3. Clear evidence that multi-year expansion is now the critical next step for anomaly-standardized SCM.

## Best Next Step

The highest-value next move is:

`expand paper-like daily label grids from 2018-only to multi-year coverage`

That unlocks two things at once:

- more paper-faithful `MODIS-derived AT` label history
- valid ERA5 calendar-day standardization for the paper-style `SCM`
