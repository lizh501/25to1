# Stage 1 Paper-like Label: AWS Batch120 Expansion

更新时间: `2026-04-08`

## 1. 这轮完成了什么

在上一轮 `AWS 15` 小规模验证基础上，这次把 AWS 扩站继续推进到前 `120` 个候选站，并完成了:

1. 批量下载探测
2. 日尺度 CSV 解压与规范化
3. 新增 `AWS 73` 站的增量 collocation
4. 与既有 `ASOS 64 + AWS 15` 主表合并
5. 重跑 paper-like `AWS train / ASOS validate`

---

## 2. 新增产物

下载日志:

- [aws576_batch120_download.log](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stations/aws576_batch120_download.log)

规范化后的 AWS 站表目录:

- [aws576_batch120_normalized](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stations/aws576_batch120_normalized)

新增 `AWS 73` 元数据:

- [station_metadata_aws73_batch120_increment.csv](/E:/18664-C5F119/华为家庭存储\CUBD\Research\HXGG2025-6-2\hxgg2025-6-2\25to1\data\stage1\processed\stations\station_metadata_aws73_batch120_increment.csv)
- [station_metadata_aws73_batch120_increment_summary.json](/E:/18664-C5F119/华为家庭存储\CUBD\Research\HXGG2025-6-2\hxgg2025-6-2\25to1\data\stage1\processed\stations\station_metadata_aws73_batch120_increment_summary.json)

新增 `AWS 73` collocation:

- [stage1_station_collocations_2018_01.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_aws73_batch120_increment_jansep/stage1_station_collocations_2018_01.csv)
- [stage1_station_collocations_2018_01_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_aws73_batch120_increment_jansep/stage1_station_collocations_2018_01_summary.json)

合并后的主表:

- [stage1_station_collocations_2018_01.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws88_batch120_jansep/stage1_station_collocations_2018_01.csv)
- [stage1_station_collocations_2018_01_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws88_batch120_jansep/stage1_station_collocations_2018_01_summary.json)

新的 paper-like 数据集与训练结果:

- [stage1_modis_at_paperlike_dataset.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws88_batch120_jansep/stage1_modis_at_paperlike_dataset.csv)
- [stage1_modis_at_paperlike_dataset_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws88_batch120_jansep/stage1_modis_at_paperlike_dataset_summary.json)
- [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/modis_at_paperlike_asos64_aws88_batch120_jansep/training_summary.json)

---

## 3. 规模变化

`batch120` 下载探测结果:

- 总候选: `120`
- 新增成功下载: `73`
- 已存在跳过: `15`
- 搜不到 2018 day fileset: `32`

现在本地已拿到的 AWS 2018 日表规模:

- `88` 个 AWS zip
- 其中有 `87` 个成功进入 `Jan-Sep` collocation

合并后的 `Jan-Sep` collocation 规模:

- `总行数 = 41037`
- `ASOS = 17408`
- `AWS = 23629`
- `ASOS 站数 = 64`
- `AWS 站数 = 87`

新的 paper-like 数据集规模:

- `train rows = 23297`
- `validate rows = 17391`
- `train stations = 87 AWS`
- `validate stations = 64 ASOS`

---

## 4. 指标对比

### 4.1 AWS train -> ASOS validate

`1 AWS`:

- `linear_regression RMSE = 12.419`
- `random_forest RMSE = 15.234`

`15 AWS`:

- `linear_regression RMSE = 7.584`
- `random_forest RMSE = 6.347`

`87 AWS`:

- `linear_regression RMSE = 5.952`
- `random_forest RMSE = 4.755`

### 4.2 和简单 LST baseline 的关系

验证集上的简单 baseline 仍然是:

- `same_day_lst_mean RMSE = 5.212`
- `four_obs_lst_mean RMSE = 4.754`

这意味着当前最好结果 `random_forest RMSE = 4.755` 已经几乎追平 `four-obs LST mean`，并明显优于之前的 `AWS 1` 和 `AWS 15` 版本。

### 4.3 pooled time split

`2018-07-01` 分割下:

- `four_obs_lst_mean RMSE = 3.775`
- `linear_regression RMSE = 8.569`
- `random_forest RMSE = 6.133`

这部分依然偏弱，说明当前问题仍然主要是:

- `AWS -> ASOS` 跨网络拟合比之前好了很多
- 但季节外推和长时间泛化依旧没有解决

---

## 5. 最重要的判断

这轮最值得记住的结论有 3 个。

1. `AWS` 扩站继续有效，而且效果是连续提升的，不是偶然波动。
2. 当 `AWS` 从 `1 -> 15 -> 87` 增长时，paper-like 标签链的 `AWS -> ASOS` 误差稳定下降:
   - `12.419 -> 7.584 -> 5.952`
3. 当前瓶颈已经从“几乎没有 AWS 训练样本”变成了“虽然 AWS 数量明显增加，但时间跨度和标签体系仍远弱于论文”。

所以现在可以更有把握地说:

`AWS 覆盖不足` 是论文式 Stage 1 标签链的关键瓶颈之一，而且已经被实证削弱了很多；但要追到论文量级，后面还需要继续扩站和扩时间。
