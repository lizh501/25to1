# Stage 1 Paper-like Label: AWS Chunk220

更新时间: `2026-04-08`

## 1. 这轮做了什么

这次没有再手工串下载、规范化、增量 collocation 和主表合并，而是直接用:

- [run_stage1_aws_incremental_pipeline.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/run_stage1_aws_incremental_pipeline.py)

实际跑了一块新的 `AWS`:

- `offset = 120`
- `limit = 100`
- 时间范围仍是 `2018-01-01 ~ 2018-09-30`

---

## 2. 这块扩站结果

运行总结:

- [pipeline_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs/aws_y2018_day_offset120_limit100/pipeline_summary.json)
- [download_result.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs/aws_y2018_day_offset120_limit100/download_result.json)

这块的下载结果非常干净:

- `100 / 100` 成功
- `0` 跳过
- `0` 失败

也就是说，从 `AWS 525` 到 `AWS 627` 这一整块，当前 KMA 链路已经能稳定拿到 `2018 day` 文件。

---

## 3. 合并后的主表规模

新的主 collocation:

- [stage1_station_collocations_2018_01.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws_chunk220_jansep/stage1_station_collocations_2018_01.csv)
- [stage1_station_collocations_2018_01_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/station_collocations_asos64_aws_chunk220_jansep/stage1_station_collocations_2018_01_summary.json)

合并后规模变成:

- `总行数 = 67956`
- `ASOS = 17408`
- `AWS = 50548`
- `AWS + ASOS 总站数 = 251`

这意味着训练侧 `AWS` 已经不再是“小样本补丁”，而是真正开始形成一个比较像样的站点网络。

---

## 4. 新的 paper-like 标签结果

新数据集:

- [stage1_modis_at_paperlike_dataset_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_asos64_aws_chunk220_jansep/stage1_modis_at_paperlike_dataset_summary.json)

新训练结果:

- [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/modis_at_paperlike_asos64_aws_chunk220_jansep/training_summary.json)

当前规模:

- `train rows = 50096`
- `validate rows = 17391`
- `train stations = 187 AWS`
- `validate stations = 64 ASOS`

`AWS train -> ASOS validate` 指标:

- `linear_regression RMSE = 5.944`
- `random_forest RMSE = 4.544`

对比之前:

- `1 AWS`: `linear 12.419`, `rf 15.234`
- `15 AWS`: `linear 7.584`, `rf 6.347`
- `87 AWS`: `linear 5.952`, `rf 4.755`
- `187 AWS`: `linear 5.944`, `rf 4.544`

所以这轮的关键信号是:

- `linear_regression` 已经基本进入平台期
- `random_forest` 还在继续变好

---

## 5. 这轮最有价值的地方

最重要的不只是误差继续下降，而是:

1. 新的增量工作流已经被真实大块任务验证过了。
2. `100` 个 AWS 站的一整块现在可以稳定跑通。
3. `AWS` 再扩之后，paper-like 标签链还在继续改善。

这说明后面继续扩 `AWS` 是值得的，而且工程上已经比前几轮轻得多。
