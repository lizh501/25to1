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

## 7. Update: split-aware bootstrap label training

That next step has now been completed once.

### 7.1 Split-aware label source

Instead of training the bootstrap MODIS-AT surrogate on the full `Q1` collocation set, we trained it only on the `Jan+Feb` collocations:

- surrogate model summary:
  - `25to1/data/stage1/models/modis_at_bootstrap_q1_janfebtrain/training_summary.json`
- surrogate raster outputs:
  - `25to1/data/stage1/processed/modis_at_bootstrap_q1_janfebtrain`
- split-aware patch index:
  - `25to1/data/stage1/processed/stage1_patch_index_q1_janfebtrain_ps64_s64_v50/stage1_patch_index.csv`

### 7.2 Split-aware CNN training run

Output directory:

- `25to1/data/stage1/models/stage1_patch_cnn_q1_janfebtrain_ps64_s64_v50`

Files:

- `25to1/data/stage1/models/stage1_patch_cnn_q1_janfebtrain_ps64_s64_v50/best_model.pt`
- `25to1/data/stage1/models/stage1_patch_cnn_q1_janfebtrain_ps64_s64_v50/training_summary.json`

Configuration:

- device: `cuda`
- epochs: `2`
- batch size: `16`
- train patches: `1325`
- test patches: `807`

Results:

Epoch 1:

- train `MAE 0.408`
- train `RMSE 0.578`
- test `MAE 0.266`
- test `RMSE 0.375`

Epoch 2:

- train `MAE 0.226`
- train `RMSE 0.307`
- test `MAE 0.211`
- test `RMSE 0.294`

### 7.3 Comparison to the earlier optimistic run

Earlier full-Q1 pseudo-label run, epoch 2:

- test `MAE 0.173`
- test `RMSE 0.245`

Current split-aware run, epoch 2:

- test `MAE 0.211`
- test `RMSE 0.294`

Interpretation:

- the split-aware result is worse than the earlier optimistic result, which is expected and healthy
- that drop confirms the earlier full-Q1 pseudo-label setup was indeed easier
- the new split-aware run should be treated as the more honest Stage-1 baseline checkpoint

## 8. Updated best next step

Now that we have a stricter patch-training baseline, the next most valuable move is no longer just another leakage fix.

The next major upgrade should be one of:

1. replace the current small CNN with a closer `SE-SRCNN` baseline
2. add the paper-inspired pooling/attention modification toward `SR-Weather`
3. improve the label-construction stage itself with a closer approximation to the paper's `MODIS-derived air temperature`

## 9. Update: architecture comparison on the split-aware setup

That next architecture step has now been started.

We upgraded the training script so it can train three architectures from the same patch pipeline:

- `srcnn_like`
- `se_srcnn`
- `sr_weather_like`

Script:

- `25to1/scripts/train_stage1_patch_cnn.py`

Important scope note:

- the current `sr_weather_like` is structurally inspired by the paper's three-branch pooling idea
- it is **not** a full faithful SR-Weather implementation yet because we still do not have the paper-style `SCM` input in the patch stack

### 9.1 Split-aware architecture results

Patch source:

- `25to1/data/stage1/processed/stage1_patch_index_q1_janfebtrain_ps64_s64_v50/stage1_patch_index.csv`

Models:

- `srcnn_like`:
  - `25to1/data/stage1/models/stage1_patch_cnn_q1_janfebtrain_ps64_s64_v50/training_summary.json`
- `se_srcnn`:
  - `25to1/data/stage1/models/stage1_patch_se_srcnn_q1_janfebtrain_ps64_s64_v50/training_summary.json`
- `sr_weather_like`:
  - `25to1/data/stage1/models/stage1_patch_sr_weather_like_q1_janfebtrain_ps64_s64_v50/training_summary.json`

Epoch-2 test results:

- `srcnn_like`: `MAE 0.211`, `RMSE 0.294`
- `se_srcnn`: `MAE 0.261`, `RMSE 0.339`
- `sr_weather_like`: `MAE 0.229`, `RMSE 0.317`

### 9.2 Interpretation

- In the current bootstrap setting, the simple `srcnn_like` baseline is still the strongest of the three.
- The `sr_weather_like` model does improve over `se_srcnn`, which is encouraging because it suggests the pooling-based gating idea is not useless even before `SCM` is available.
- However, without the paper's `SCM` and without more careful tuning, the current `sr_weather_like` does not yet beat the simpler baseline.

### 9.3 What this means

At this point we have learned something useful:

- the pipeline can support architecture comparison
- the paper-inspired pooling change is directionally promising
- the next real performance gain is more likely to come from better inputs and label construction than from blindly making the CNN fancier

So the most valuable next step is probably:

1. add a first `SCM` approximation
2. inject that `SCM` into the patch pipeline
3. rerun `se_srcnn` vs `sr_weather_like`

That would be a much fairer test of the actual paper idea.
