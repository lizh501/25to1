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

## 10. Update: first SCM bootstrap experiments

That SCM step has now been explored in two bootstrap forms.

Added scripts:

- `25to1/scripts/build_stage1_scm_bootstrap.py`
- `25to1/scripts/augment_stage1_features_with_scm.py`

### 10.1 Monthly SCM bootstrap

First attempt:

- source pseudo-labels:
  - `25to1/data/stage1/processed/modis_at_bootstrap_q1_janfebtrain`
- monthly SCM outputs:
  - `25to1/data/stage1/processed/scm_bootstrap_q1_janfebtrain/manifest.json`

Monthly means:

- `2018-01`: `-4.92 C`
- `2018-02`: `-2.90 C`
- `2018-03`: `6.64 C`

This version was too coarse: it effectively gave the network only three month-level constant climatology fields.

Split-aware epoch-2 test RMSE with monthly SCM:

- `srcnn_like`: `0.342`
- `se_srcnn`: `0.335`
- `sr_weather_like`: `0.400`

Interpretation:

- monthly SCM did not help
- it made every model worse than the no-SCM split-aware baseline

### 10.2 Rolling-15-day SCM bootstrap

We then replaced the month-constant SCM with a rolling daily SCM approximation:

- rolling SCM outputs:
  - `25to1/data/stage1/processed/scm_bootstrap_q1_janfebtrain_rolling15/manifest.json`
- window:
  - `15` days centered on each day when available

This gives a much more continuous seasonal field across `Q1`.

Examples:

- `A2018001`: mean `-3.11 C`
- `A2018032`: mean `-7.36 C`
- `A2018065`: mean `4.10 C`
- `A2018090`: mean `10.10 C`

Split-aware epoch-2 test RMSE with rolling-15-day SCM:

- `srcnn_like`: `0.321`
- `se_srcnn`: `0.322`
- `sr_weather_like`: `0.335`

### 10.3 Comparison across SCM variants

No SCM, split-aware:

- `srcnn_like`: `0.294`
- `se_srcnn`: `0.339`
- `sr_weather_like`: `0.317`

Monthly SCM:

- `srcnn_like`: `0.342`
- `se_srcnn`: `0.335`
- `sr_weather_like`: `0.400`

Rolling-15-day SCM:

- `srcnn_like`: `0.321`
- `se_srcnn`: `0.322`
- `sr_weather_like`: `0.335`

### 10.4 Interpretation

- The monthly SCM approximation was too crude and clearly harmful.
- The rolling-15-day SCM is materially better than monthly SCM and improves the SCM experiments noticeably.
- However, even the rolling SCM still does not beat the best no-SCM `srcnn_like` baseline.
- The `se_srcnn` model benefits more from rolling SCM than it did from no SCM, but the `sr_weather_like` model still does not unlock the paper-style gain.

### 10.5 What this likely means

The result is informative rather than discouraging:

- the paper's `SCM` probably carries richer seasonal-spatial structure than our current bootstrap proxy
- our current bootstrap SCM is still closer to a smoothed pseudo-label climatology than to the paper's intended seasonal climatology map
- architectural changes alone are not enough; the quality of `SCM` matters a lot

## 11. Updated next step

The next high-value move is now clearer:

1. build a better SCM approximation than the current rolling pseudo-label mean
2. preferably derive it from a longer temporal baseline than `Q1` alone
3. then rerun the same three-model comparison

That is now more valuable than adding still more CNN complexity.

## 12. Update: SCM anomaly experiment

We also tested a more paper-inspired SCM proxy: instead of averaging the pseudo-label temperature field itself, we first removed the coarse `ERA5` background and then built a rolling climatology of the remaining anomaly.

Added script:

- `25to1/scripts/build_stage1_scm_anomaly_bootstrap.py`

Artifacts:

- anomaly SCM manifest:
  - `25to1/data/stage1/processed/scm_bootstrap_anom_q1_janfebtrain_rolling15/manifest.json`

Design:

- source field:
  - `bootstrap_MODIS_AT - ERA5_T2M`
- smoothing:
  - rolling `15`-day window

### 12.1 Result of the anomaly SCM itself

This anomaly field turned out to be much flatter than expected.

Examples:

- `A2018001`: mean anomaly `-1.44 C`
- `A2018032`: mean anomaly `-1.45 C`
- `A2018090`: mean anomaly `-1.82 C`

That means the current anomaly SCM is close to a weak, nearly constant bias field rather than a rich spatial seasonal prior.

### 12.2 Patch-model results with anomaly SCM

Epoch-2 split-aware test RMSE:

- `srcnn_like`: `0.369`
- `sr_weather_like`: `0.335`

Relevant training summaries:

- `25to1/data/stage1/models/stage1_patch_cnn_scmanomroll15_q1_janfebtrain_ps64_s64_v50/training_summary.json`
- `25to1/data/stage1/models/stage1_patch_sr_weather_like_scmanomroll15_q1_janfebtrain_ps64_s64_v50/training_summary.json`

### 12.3 Interpretation

- The anomaly SCM did not help.
- It was worse than the rolling temperature-field SCM and also worse than the no-SCM baseline.
- This suggests that with only the current `Q1` bootstrap pseudo-labels, subtracting `ERA5` removes too much of the useful structure and leaves a prior that is too weak.

## 13. Practical conclusion

At this point, the experimental picture is pretty consistent:

- no SCM is currently best
- rolling temperature-field SCM is the least bad SCM proxy so far
- monthly SCM is too coarse
- anomaly SCM is too weak

So the bottleneck is no longer ambiguous:

- we need a **better temporal basis for SCM construction**
- most likely that means **more months of data**, not another quick SCM formula tweak

## 14. Update: January-April extension changed the SCM picture

We then extended the split-aware pseudo-label and SCM pipeline from `Q1` into full `Jan-Apr`.

New artifacts:

- split-aware pseudo-label model:
  - `25to1/data/stage1/models/modis_at_bootstrap_q1apr_janmartrain/training_summary.json`
- Jan-Apr pseudo-label rasters:
  - `25to1/data/stage1/processed/modis_at_bootstrap_q1apr_janmartrain/manifest.json`
- longer-baseline rolling SCM:
  - `25to1/data/stage1/processed/scm_bootstrap_q1apr_janmartrain_rolling15/manifest.json`
- Jan-Mar-train / Apr-test patch index:
  - `25to1/data/stage1/processed/stage1_patch_index_q1apr_janmartrain_ps64_s64_v50/stage1_patch_index.csv`
  - `25to1/data/stage1/processed/stage1_patch_index_q1apr_janmartrain_ps64_s64_v50/stage1_patch_index_summary.json`

Patch-index summary:

- date range: `2018-01-01` to `2018-04-30`
- split date: `2018-04-01`
- train period: `Jan-Mar`
- test period: `Apr`

### 14.1 Quick patch runs with longer-baseline rolling SCM

We reran the most informative pair of models:

- `srcnn_like`
- `sr_weather_like`

Outputs:

- `25to1/data/stage1/models/stage1_patch_cnn_scmroll15_q1apr_janmartrain_ps64_s64_v50/training_summary.json`
- `25to1/data/stage1/models/stage1_patch_sr_weather_like_scmroll15_q1apr_janmartrain_ps64_s64_v50/training_summary.json`

Epoch-2 April-holdout test metrics:

- `srcnn_like`: `MAE 0.138`, `RMSE 0.190`
- `sr_weather_like`: `MAE 0.157`, `RMSE 0.203`

### 14.2 Comparison with the earlier Q1-only SCM results

Earlier rolling-15-day SCM on the shorter `Q1` setup:

- `srcnn_like`: `RMSE 0.321`
- `sr_weather_like`: `RMSE 0.335`

Now, with the Jan-Apr split-aware pseudo-label chain and longer-baseline rolling SCM:

- `srcnn_like`: `RMSE 0.190`
- `sr_weather_like`: `RMSE 0.203`

### 14.3 Interpretation

- This is the first strong sign that extending the time span was the right move.
- The rolling SCM prior becomes much more usable once it is built from a longer temporal basis than `Q1` alone.
- `srcnn_like` is still slightly better than `sr_weather_like`, so we do **not** yet have a paper-style architectural win.
- But the gap is now much smaller, and the whole SCM-enabled setup is materially healthier than the earlier `Q1` experiments.

## 15. Current practical conclusion

The picture is more specific now:

- the previous weak point was not just "SCM formula quality" in the abstract
- it was also the fact that the SCM proxy was being estimated from too short a seasonal window
- once the dataset extends into `April`, the rolling SCM prior starts to support much stronger patch-level performance

So the next best move is no longer another quick bootstrap formula tweak. It is:

1. continue extending the time span beyond `Jan-Apr`
2. keep the split-aware pseudo-label generation strict
3. rerun the same `srcnn_like vs sr_weather_like` comparison as the SCM prior becomes more climatological and less short-window-smoothed

## 16. Update: H1 extension with Jan-Apr train / May-Jun test

We then extended the same split-aware pseudo-label and rolling-SCM pipeline into full `H1`.

New artifacts:

- H1 split-aware pseudo-label model:
  - `25to1/data/stage1/models/modis_at_bootstrap_h1_janaprtrain/training_summary.json`
- H1 pseudo-label rasters:
  - `25to1/data/stage1/processed/modis_at_bootstrap_h1_janaprtrain/manifest.json`
- H1 rolling SCM:
  - `25to1/data/stage1/processed/scm_bootstrap_h1_janaprtrain_rolling15/manifest.json`
- H1 patch index:
  - `25to1/data/stage1/processed/stage1_patch_index_h1_janaprtrain_ps64_s64_v50/stage1_patch_index.csv`
  - `25to1/data/stage1/processed/stage1_patch_index_h1_janaprtrain_ps64_s64_v50/stage1_patch_index_summary.json`

Patch-index summary:

- date range: `2018-01-01` to `2018-06-30`
- split date: `2018-05-01`
- train period: `Jan-Apr`
- test period: `May-Jun`
- total patches: `4097`
- train patches: `2881`
- test patches: `1216`

### 16.1 Quick patch runs with H1 rolling SCM

We reran the same two-model comparison:

- `srcnn_like`
- `sr_weather_like`

Outputs:

- `25to1/data/stage1/models/stage1_patch_cnn_scmroll15_h1_janaprtrain_ps64_s64_v50/training_summary.json`
- `25to1/data/stage1/models/stage1_patch_sr_weather_like_scmroll15_h1_janaprtrain_ps64_s64_v50/training_summary.json`

Best H1 test RMSE:

- `srcnn_like`: `0.208`
- `sr_weather_like`: `0.217`

Important note:

- for `sr_weather_like`, the best test score occurred at epoch `1`
- epoch `2` drifted slightly worse, so the current comparison should use the summary's `best_test_rmse`, not just the final epoch line

### 16.2 Comparison with the earlier Jan-Apr split

Earlier Jan-Apr setup with Apr holdout:

- `srcnn_like`: `RMSE 0.190`
- `sr_weather_like`: `RMSE 0.203`

Now, with the harder H1 setup and May-Jun holdout:

- `srcnn_like`: `RMSE 0.208`
- `sr_weather_like`: `RMSE 0.217`

### 16.3 Interpretation

- The H1 holdout is harder than the earlier single-month April holdout, so some degradation is expected.
- Even on this harder setup, the rolling-SCM patch pipeline remains much stronger than the old Q1-era SCM experiments.
- `srcnn_like` still performs best, but `sr_weather_like` is now very close in best-RMSE terms.
- That is a healthier signal than we had earlier: the paper-inspired gating structure is no longer clearly off the pace once the SCM prior has a longer temporal basis.

## 17. Current practical conclusion

The current Stage-1 picture is now much clearer:

- longer temporal coverage really does matter for SCM usefulness
- the H1 pipeline is substantially more informative than the earlier Q1 bootstrap
- the best simple image model is still `srcnn_like`
- but the gap to `sr_weather_like` is now small enough that further time extension may plausibly flip the ranking later

So the next high-value move is:

1. extend the same strict split-aware pipeline beyond `H1`
2. keep evaluating `srcnn_like` and `sr_weather_like` side by side
3. watch whether the SCM-enabled architecture overtakes the simpler baseline once the temporal basis becomes even more climatological
