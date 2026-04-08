# Stage 1 Paper-like Label: AWS Chunk420

更新时间: `2026-04-08`

## 1. 这轮做了什么

继续沿用增量工作流，运行了一块新的 AWS 候选:

- `offset = 320`
- `limit = 100`

运行摘要:

- [pipeline_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs/aws_y2018_day_offset320_limit100/pipeline_summary.json)
- [download_result.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs/aws_y2018_day_offset320_limit100/download_result.json)

---

## 2. 这块扩站结果

下载结果非常干净:

- 成功: `100`
- 失败: `0`
- 跳过: `0`

也就是说，这一整块新 AWS 候选都顺利接入了 `2018 day` 数据链。

---

## 3. 合并后的主表规模

新的主 collocation:

- [stage1_station_collocations_2018_01_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws_chunk420_jansep/stage1_station_collocations_2018_01_summary.json)

当前规模:

- `总行数 = 119836`
- `AWS + ASOS 总站数 = 443`
- `时间范围 = 2018-01-01 ~ 2018-09-30`

---

## 4. 新的 paper-like 标签结果

数据集摘要:

- [stage1_modis_at_paperlike_dataset_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws_chunk420_jansep/stage1_modis_at_paperlike_dataset_summary.json)

纠正后的训练结果:

- [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/modis_at_paperlike_asos64_aws_chunk420_jansep_rerun/training_summary.json)

当前 `AWS train -> ASOS validate`:

- `train rows = 101653`
- `train stations = 379`
- `linear_regression RMSE = 5.918`
- `random_forest RMSE = 4.359`

说明:

- 初次运行时把“建数据集”和“训练”并行执行了
- 训练脚本读到了尚未完全写完的 CSV
- 上面这组数字已经用串行重跑纠正过

---

## 5. 与前几轮对比

- `1 AWS`: `linear 12.419`, `rf 15.234`
- `15 AWS`: `linear 7.584`, `rf 6.347`
- `87 AWS`: `linear 5.952`, `rf 4.755`
- `187 AWS`: `linear 5.944`, `rf 4.544`
- `279 AWS`: `linear 5.925`, `rf 4.521`
- `379 AWS`: `linear 5.918`, `rf 4.359`

结论:

1. 扩 AWS 仍然有收益。
2. `random_forest` 这条线到现在还在持续改善。
3. `linear_regression` 已经非常接近平台期。
4. 这说明单纯扩 AWS 还有价值，但真正更大的突破点，后面还是会回到长时序标签体系和更论文一致的 `SCM`。
