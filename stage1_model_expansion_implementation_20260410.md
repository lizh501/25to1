# Stage-1 Model Expansion Implementation

更新时间: `2026-04-10`

## 本轮新增模型

我已经把这 4 个新架构接进现有训练脚本 [train_stage1_patch_cnn.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/train_stage1_patch_cnn.py)：

- `resunet_like`
- `edsr_like`
- `rcan_like`
- `swinir_light`

当前脚本支持的 `--architecture` 已经变成：

- `srcnn_like`
- `se_srcnn`
- `resunet_like`
- `edsr_like`
- `rcan_like`
- `swinir_light`
- `sr_weather_like`

## 实现说明

### `resunet_like`

- 2 次下采样 + bottleneck + 2 次上采样
- skip connection 直接拼接 encoder feature
- 适合测试“多尺度上下文”是否比浅层局部卷积更重要

### `edsr_like`

- 无 BN 残差块
- 深残差 CNN 路线
- 适合作为 `SRCNN -> deeper residual CNN` 的干净对照

### `rcan_like`

- residual group + channel attention
- 适合作为“通用 attention CNN”对照组

### `swinir_light`

- window attention
- 交替 shift window
- 轻量版 transformer restoration backbone

这里做的是**适配当前同尺度回归框架**的版本，不带显式上采样尾部。

## Smoke 自检

我用一个很小的 smoke subset 跑了 1 epoch，确保：

- 能正常前向
- 能反向传播
- 能写出 `best_model.pt` 和 `training_summary.json`

smoke patch 索引在：

- [stage1_patch_index_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stage1_patch_index_2018_2020full_daily5_smoke96/stage1_patch_index_summary.json)

规模是：

- 总 `96` patch
- `64` train
- `32` test

对应 smoke 结果：

- `resunet_like`: [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/smoke_models_20260410/resunet_like/training_summary.json)
- `edsr_like`: [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/smoke_models_20260410/edsr_like/training_summary.json)
- `rcan_like`: [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/smoke_models_20260410/rcan_like/training_summary.json)
- `swinir_light`: [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/smoke_models_20260410/swinir_light/training_summary.json)

## 调参信号

smoke 里最有价值的信号不是“谁最好”，而是“谁对学习率更敏感”：

- `resunet_like` 在 `lr=1e-3` 下明显不稳
- `swinir_light` 也偏敏感
- `edsr_like`、`rcan_like` 用 `1e-3` 能正常跑通

我又额外补了两组低学习率 smoke：

- `resunet_like lr=2e-4`: [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/smoke_models_20260410/resunet_like_lr2e4/training_summary.json)
- `swinir_light lr=2e-4`: [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/smoke_models_20260410/swinir_light_lr2e4/training_summary.json)

结果说明：

- `resunet_like` 用 `2e-4` 后稳定很多
- `swinir_light` 用 `2e-4` 也更合理

## 建议的全量复跑超参

如果下一步要在 `2018-2020 daily5` 或更大 patch 集上正式复跑，我建议从这里起步：

- `edsr_like`: `lr=5e-4` 或 `1e-3`
- `rcan_like`: `lr=5e-4`
- `resunet_like`: `lr=2e-4`
- `swinir_light`: `lr=2e-4`

并统一保留：

- `--no-train-shuffle`
- `--cache-size 2~4`

因为当前网络盘 / 大量逐日 `npz+tif` 读盘模式下，按天顺序读 patch 更适合这个项目。

## 下一步最合理的复跑顺序

1. `edsr_like`
2. `rcan_like`
3. `resunet_like`
4. `swinir_light`

理由是：

- 先跑两个更稳的 CNN
- 再跑多尺度 `ResUNet`
- 最后跑 transformer

这样最容易把“结构收益”和“调参收益”分开看清楚。
