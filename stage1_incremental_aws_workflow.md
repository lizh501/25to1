# Stage 1 Incremental AWS Workflow

更新时间: `2026-04-08`

## 1. 为什么要改成增量流程

现在扩 `AWS` 数据最耗时的，不是单独某一步，而是每次都要重复做:

1. 批量下载探测
2. 规范化 CSV
3. 站点元数据子集整理
4. 新增站点的 collocation
5. 与旧主表手工合并

为了避免每一轮都手工串这些步骤，新增了一键脚本:

- [run_stage1_aws_incremental_pipeline.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/run_stage1_aws_incremental_pipeline.py)

同时还增强了两个底层脚本:

- [download_kma_station_batch.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/download_kma_station_batch.py)
- [build_stage1_station_collocations.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_station_collocations.py)

---

## 2. 现在多了哪些能力

### 2.1 下载脚本

`download_kma_station_batch.py` 新增:

- `--offset`
- `--result-json`

这样可以把候选站分块跑，也可以把每一块的成功/失败记录下来，后面断点续跑更轻松。

### 2.2 collocation 脚本

`build_stage1_station_collocations.py` 现在支持:

- 参考栅格坐标一次性批量映射
- 同一天内批量像元采样
- `--merge-existing-csv`

最后这项最重要，意味着可以只对“新增站点”建增量表，然后自动和旧主表合并去重。

---

## 3. 推荐用法

### 3.1 跑一个新的 AWS 分块

```powershell
& 'D:\ApplicationData\Anaconda\envs\python312\python.exe' `
  '.\25to1\scripts\run_stage1_aws_incremental_pipeline.py' `
  --metadata-master '.\25to1\data\stage1\processed\stations\station_metadata_aws576.csv' `
  --stations-csv '.\25to1\data\stage1\processed\stations\station_metadata_aws576.csv' `
  --year 2018 `
  --frequency day `
  --offset 120 `
  --limit 100 `
  --merge-existing-csv '.\25to1\data\stage1\processed\station_collocations_asos64_aws88_batch120_jansep\stage1_station_collocations_2018_01.csv' `
  --collocation-output-dir '.\25to1\data\stage1\processed\station_collocations_asos64_aws_chunk220_jansep'
```

这个命令会自动做:

1. 下载这一块 `AWS`
2. 规范化这一块的 CSV
3. 生成这一块的元数据子集
4. 只为这一块生成 collocation
5. 自动和旧主表合并

### 3.2 只重跑后半段

如果下载已经完成，可以跳过前面步骤:

```powershell
& 'D:\ApplicationData\Anaconda\envs\python312\python.exe' `
  '.\25to1\scripts\run_stage1_aws_incremental_pipeline.py' `
  --year 2018 `
  --frequency day `
  --offset 120 `
  --limit 100 `
  --skip-download `
  --merge-existing-csv '.\old_main.csv' `
  --collocation-output-dir '.\new_main_dir'
```

---

## 4. 当前已经验证过什么

我已经用一个小块做了端到端自检:

- 运行目录: [aws_y2018_day_offset20_limit2](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs_test/aws_y2018_day_offset20_limit2)
- 输出总结: [pipeline_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/aws_incremental_runs_test/aws_y2018_day_offset20_limit2/pipeline_summary.json)

这次测试用的是 `AWS 314` 和 `AWS 315`，成功串通了:

- 已有下载结果复用
- 规范化
- 子集元数据构造
- collocation 输出

---

## 5. 现在这套流程到底能省什么

它主要省的是:

- 手工命令拼接
- 重复探测已知结果
- 重复重建整张主表
- 人工维护“这次新增了哪些站”的负担

它暂时还没有从根上解决的，是:

- `Jan-Sep` collocation 本身仍然计算重
- 单次新增站太多时，像元抽样仍然要花比较久

所以最推荐的实际策略是:

1. `AWS` 站点按块跑，例如每块 `50-100` 站
2. 每块写 `result-json`
3. 每块只做增量 collocation
4. 合并进一个主表

这样后面即使继续扩到更多 `AWS`，成本也会比现在这种“每轮都手工重拼”低很多。
