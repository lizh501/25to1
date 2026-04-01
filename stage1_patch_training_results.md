# Stage-1 Patch CNN Results

## 1. What was trained

This is the first end-to-end Stage-1 patch-training sanity check built on top of the current bootstrap data pipeline:

- patch index:
  - `25to1/data/stage1/processed/stage1_patch_index_q1_ps64_s64_v50/stage1_patch_index.csv`
- model script:
  - `25to1/scripts/train_stage1_patch_cnn.py`
- model type:
  - small `SRCNN`-like fully convolutional network
- input channels:
  - `era5_t2m_c`
  - `dem_m`
  - `slope_deg`
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
  - `aspect_sin`
  - `aspect_cos`
- target:
  - bootstrap `MODIS-derived AT` surrogate raster

## 2. Training configuration

- device: `cuda`
- epochs: `2`
- batch size: `16`
- learning rate: `1e-3`
- train patches: `1325`
- test patches: `807`

Output directory:

- `25to1/data/stage1/models/stage1_patch_cnn_q1_ps64_s64_v50`

Files:

- `25to1/data/stage1/models/stage1_patch_cnn_q1_ps64_s64_v50/best_model.pt`
- `25to1/data/stage1/models/stage1_patch_cnn_q1_ps64_s64_v50/training_summary.json`

## 3. Headline results

Epoch 1:

- train `MAE 0.374`
- train `RMSE 0.545`
- test `MAE 0.241`
- test `RMSE 0.325`

Epoch 2:

- train `MAE 0.221`
- train `RMSE 0.297`
- test `MAE 0.173`
- test `RMSE 0.245`

## 4. Interpretation

- The Stage-1 patch dataloader, mask-aware loss, model forward pass, and checkpoint path are all working.
- This is a strong engineering milestone because we now have a fully runnable Stage-1 training loop.

## 5. Important caveat

These patch-level metrics are **not** strict paper-level reproduction metrics yet.

Why:

- the current patch labels come from a bootstrap surrogate built using the full `Q1` station collocation set
- therefore the March pseudo-label field is not a strict unseen-label target in the same sense as the earlier station holdout experiments
- the CNN is learning to approximate a pseudo-label product that is itself derived from the same Stage-1 feature stack

So the current result should be interpreted as:

- `pipeline validation`: yes
- `full Stage-1 dataloader/training sanity check`: yes
- `strict leakage-free paper comparison`: not yet

## 6. Best next step

The clean next upgrade is to make the bootstrap MODIS-AT surrogate split-aware:

1. train the surrogate only on `train` dates
2. generate pseudo-label rasters separately for `train` and `test`
3. rebuild the patch index
4. retrain the CNN on the leakage-reduced target set

That will give a much more honest Stage-1 baseline before moving on to a closer SR-Weather implementation.
