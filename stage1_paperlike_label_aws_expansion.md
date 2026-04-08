# Stage 1 Paper-like Label: AWS Expansion Probe

更新时间: `2026-04-07`

## 1. 这轮做了什么

目标是验证一个关键判断:

`论文式 Stage 1 标签链跑不起来，究竟是不是因为 AWS 训练站点太少。`

这轮沿着这个问题做了 5 件事:

1. 从 KMA `SFC02` 树里解析出 `576` 个 AWS 候选站号。
2. 批量抓取公开站点详情页，并成功解析出 `555` 个带坐标的 AWS 站点元数据。
3. 对其中前 `20` 个站号做 `2018` 年日尺度文件下载探测。
4. 成功下载并规范化了 `14` 个新的 AWS 日尺度 CSV。
5. 把这 `14` 个新 AWS 站与原有 `AWS 116` 合并，重建 `AWS train / ASOS validate` 的 paper-like 标签实验。

---

## 2. 新增数据资产

候选 AWS 站列表:

- [kma_aws_candidate_stations_576.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/interim/kma_aws_candidate_stations_576.csv)

AWS 元数据:

- [station_metadata_aws576.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stations/station_metadata_aws576.csv)
- [station_metadata_aws576_invalid.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stations/station_metadata_aws576_invalid.json)

探测成功的 AWS 规范化日表:

- [aws576_probe_normalized](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stations/aws576_probe_normalized)

用于重建 collocation 的元数据:

- [station_metadata_stage1_asos64_aws15_probe.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stations/station_metadata_stage1_asos64_aws15_probe.csv)
- [station_metadata_stage1_asos64_aws15_probe_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/stations/station_metadata_stage1_asos64_aws15_probe_summary.json)

增量 AWS collocation:

- [stage1_station_collocations_2018_01.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_aws14_probe_jansep/stage1_station_collocations_2018_01.csv)

合并后的 `ASOS 64 + AWS 15` collocation:

- [stage1_station_collocations_2018_01.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws15_probe_jansep/stage1_station_collocations_2018_01.csv)
- [stage1_station_collocations_2018_01_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws15_probe_jansep/stage1_station_collocations_2018_01_summary.json)

新的 paper-like 数据集与结果:

- [stage1_modis_at_paperlike_dataset.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws15_probe_jansep/stage1_modis_at_paperlike_dataset.csv)
- [stage1_modis_at_paperlike_dataset_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws15_probe_jansep/stage1_modis_at_paperlike_dataset_summary.json)
- [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/modis_at_paperlike_asos64_aws15_probe_jansep/training_summary.json)

---

## 3. 探测结果

### 3.1 AWS 候选与元数据

- 候选站数: `576`
- 成功解析坐标的站数: `555`
- 失效详情页: `21`
- 坐标范围大致覆盖韩国 AWS 网络:
  - 纬度: `33.12206 ~ 38.54251`
  - 经度: `124.63048 ~ 131.86983`

### 3.2 小批量下载探测

前 `20` 个 AWS 站号中:

- 已存在并跳过: `1`
- 成功下载: `14`
- 搜不到 `2018 day fileset`: `5`

成功下载的新增 AWS 站号:

- `160`
- `229`
- `300`
- `301`
- `302`
- `303`
- `304`
- `305`
- `306`
- `308`
- `310`
- `311`
- `312`
- `313`

这一步说明:

`AWS 扩站链已经真实可用，不再停留在单站 bootstrap。`

---

## 4. 对论文式标签链的直接影响

### 4.1 训练集规模变化

旧版 paper-like 数据集:

- `train rows = 271`
- `train stations = 1 AWS`
- `validate rows = 17391`
- `validate stations = 64 ASOS`

新版 `ASOS 64 + AWS 15 probe`:

- `train rows = 4021`
- `train stations = 15 AWS`
- `validate rows = 17391`
- `validate stations = 64 ASOS`

也就是说，`AWS` 训练样本量约扩大了 `14.8x`。

### 4.2 AWS -> ASOS 指标变化

旧版 `1 AWS`:

- `four_obs_lst_mean RMSE = 4.754`
- `linear_regression RMSE = 12.419`
- `random_forest RMSE = 15.234`

新版 `15 AWS`:

- `four_obs_lst_mean RMSE = 4.754`
- `linear_regression RMSE = 7.584`
- `random_forest RMSE = 6.347`

改善幅度:

- `linear_regression`: `12.419 -> 7.584`
- `random_forest`: `15.234 -> 6.347`

这说明:

`AWS 覆盖不足` 确实是之前 paper-like 标签链崩掉的主因之一，而且这个判断已经被定量验证。

---

## 5. 目前仍然和论文有多远

虽然结果明显变好了，但还不能说已经接近论文:

- 论文报告的 `AWS train / ASOS validate` 级别是 `RMSE = 1.22 K`
- 我们当前最好的 paper-like 结果仍是 `RMSE = 6.347`

所以当前状态更准确的判断是:

1. `AWS 扩站` 是必要条件，而且已经证明有效。
2. 但它还不是充分条件。
3. 剩余 gap 仍然包括:
   - `AWS` 站点覆盖仍偏少
   - 只用了 `2018-01 ~ 2018-09`
   - 还没有论文定义的 `2000-2020` 长时序标签体系
   - 还没有真正论文版 `SCM`

---

## 6. 这轮最重要的结论

这次最有价值的不是某个单独 RMSE 数字，而是把一句关键判断落成了证据:

`论文式 Stage 1 标签链并不是完全走不通，而是对 AWS 覆盖非常敏感。`

在 `1 AWS` 时，模型几乎失真。

扩到 `15 AWS` 之后，`AWS -> ASOS` 已经开始出现可解释的泛化能力，但离论文还有明显距离。

所以后续最合理的优先级仍然是:

1. 继续批量扩 AWS 站点下载
2. 把时间范围继续拉长
3. 再重新评估真正论文式 `MODIS-derived AT` 标签构造
