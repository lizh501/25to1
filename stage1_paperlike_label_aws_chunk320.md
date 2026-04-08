# Stage 1 Paper-like Label: AWS Chunk320

更新时间: `2026-04-08`

## 1. 这轮做了什么

继续沿用增量工作流，运行了一块新的 AWS 候选:

- `offset = 220`
- `limit = 100`

运行摘要:

- [pipeline_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs/aws_y2018_day_offset220_limit100/pipeline_summary.json)
- [download_result.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs/aws_y2018_day_offset220_limit100/download_result.json)

---

## 2. 这块扩站结果

下载结果:

- 成功: `94`
- 失败: `6`
- 跳过: `0`

失败站号主要是:

- `677`
- `678`
- `679`
- `683`
- `686`
- `687`

其余站点已经顺利接入。

---

## 3. 合并后的主表规模

新的主 collocation:

- [stage1_station_collocations_2018_01_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws_chunk320_jansep/stage1_station_collocations_2018_01_summary.json)

当前规模:

- `总行数 = 92664`
- `train side AWS + validate side ASOS 总站数 = 343`
- `时间范围 = 2018-01-01 ~ 2018-09-30`

---

## 4. 新的 paper-like 标签结果

数据集摘要:

- [stage1_modis_at_paperlike_dataset_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws_chunk320_jansep/stage1_modis_at_paperlike_dataset_summary.json)

训练结果:

- [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/modis_at_paperlike_asos64_aws_chunk320_jansep/training_summary.json)

当前 `AWS train -> ASOS validate`:

- `train rows = 74632`
- `train stations = 279`
- `linear_regression RMSE = 5.925`
- `random_forest RMSE = 4.521`

---

## 5. 与前几轮对比

- `1 AWS`: `linear 12.419`, `rf 15.234`
- `15 AWS`: `linear 7.584`, `rf 6.347`
- `87 AWS`: `linear 5.952`, `rf 4.755`
- `187 AWS`: `linear 5.944`, `rf 4.544`
- `279 AWS`: `linear 5.925`, `rf 4.521`

结论很直接:

1. 继续扩 AWS 仍然有收益。
2. `random_forest` 还在持续改善。
3. `linear_regression` 已经非常接近平台期。
4. 边际收益开始变慢，但还没有完全停止。
