# Stage 1 Expansion Roadmap

更新日期: `2026-04-08`

## Current State

当前已经稳定跑通的核心链路是:

- `2018-01-01 ~ 2018-09-30` 的 `stage1_simplified_features`
- `2018-01-01 ~ 2018-09-30` 的 paper-like daily label grids
- 基于上述 daily grids 的第一版 paper-like `SCM climatology`

当前最重要的现实约束是:

- `MOD11A1` 本地原始数据目前只到 `A2018273`
- `stage1_simplified_features` 目前也只到 `A2018273`
- `MOD13A2 NDVI` 原始数据目前也只到 `A2018273`
- `ERA5 t2m` 和 `SSRD` 原始文件目前也只覆盖到 `2018-09`
- 所以继续往前扩，真正慢的主要是“原始数据下载 + 月度整合”，不是后面的标签栅格或 `SCM` 脚本

## Measured Throughput

以下都是这台机器上的实测量级:

| 环节 | 当前实测速度 | 备注 |
|---|---:|---|
| `AWS` 增量扩站 | `100` 站约 `9 min` | 已有增量工作流 |
| paper-like daily label grids | `272` 天约 `10.3 min` | 约 `2.3 sec/day` |
| paper-like `SCM` | `272` 天约 `23.2 min` | 约 `5.1 sec/source day` |

这意味着:

- 如果原始特征已经齐了，后处理其实很快
- 如果原始特征没齐，时间主要花在 `MODIS / ERA5 / KMA` 下载与对齐上

## Best Strategy

最省时间、同时又最能缩小论文 gap 的顺序不是直接冲 `2000-2020`，而是:

1. 先补齐 `2018 Q4`
2. 再补 `2019` 全年
3. 再看是否继续到 `2020`

原因很简单:

- `2018` 全年可以让单年 climatology 更完整
- `2018 + 2019` 开始让 calendar-day std 真正可定义
- 到 `2020` 时，paper-like anomaly `SCM` 才会更稳

## Three Budget Plans

### Plan A: Half-day

目标:

- 把 `2018` 从 `Jan-Sep` 补到全年
- 重建 `2018` 全年 daily paper-like grids
- 重建 `2018` 全年 paper-like `SCM climatology`

预估时间:

- 如果原始 `Q4` 数据下载顺利: `3 ~ 6 小时`
- 如果下载慢或有重试: `6 ~ 8 小时`

主要工作:

- 下载 `2018 Q4` 的 `MOD11A1`
- 下载 `2018 Q4` 的 `ERA5 t2m` 和 `ssrd`
- 补齐 `2018 Q4` 的 `NDVI` composite 映射
- 生成 `Q4` 的 `stage1_simplified_features`
- 生成 `2018` 全年 paper-like daily label grids
- 重建 `2018` 全年 `SCM climatology`

交付物:

- `2018` 全年 label grid 库
- `2018` 全年 `SCM climatology`

局限:

- `anomaly-standardized SCM` 依然不科学，因为仍然只有单年

### Plan B: One-day

目标:

- 完成 `2018` 全年
- 再补 `2019` 全年
- 建立第一版“真正可算 std”的 multi-year paper-like `SCM`

预估时间:

- `8 ~ 14 小时`

主要工作:

- 完成 Plan A
- 下载并整合 `2019` 全年 `MOD11A1 / ERA5 / solar / NDVI`
- 生成 `2019` 的 `stage1_simplified_features`
- 生成 `2018-2019` 的 daily paper-like grids
- 重建 `2018-2019` 的 paper-like `SCM`

交付物:

- `2018-2019` daily label grid 库
- 第一版有统计意义的 paper-like `anomaly SCM`

价值:

- 这是从“单年验证”跨到“可开始逼近论文定义”的关键节点

### Plan C: Three-day

目标:

- 把多年份链路扩到 `2018-2020`
- 获得更稳的 paper-like `SCM` 和更长的标签历史

预估时间:

- `1 ~ 3 天`

主要工作:

- 完成 `2018-2019`
- 下载并整合 `2020` 全年
- 生成 `2018-2020` daily paper-like grids
- 重建 `2018-2020` paper-like `SCM`
- 基于新的 `SCM` 重新回灌 Stage 1 patch pipeline

交付物:

- `2018-2020` multi-year label 库
- 更稳定的 paper-like climatology/anomaly `SCM`
- 更接近论文设置的 Stage 1 输入先验

价值:

- 这是最像论文实验前置条件的一版

## Recommended Path

如果目标是“用尽量少的时间，把论文版 `SCM` 真正立起来”，我建议:

`先走 Plan A，再直接进入 Plan B`

也就是:

1. 今天先补完 `2018 Q4`
2. 确认全年 `2018` label grids 和 climatology 正常
3. 接着补 `2019`
4. 再第一次认真看 anomaly `SCM`

这是当前时间收益比最高的路线。

## Why Not Jump Straight to 2000-2020

直接冲论文全时段当然最完整，但对当前工程阶段不划算:

- 原始数据下载量太大
- 一旦某个环节格式或对齐策略要改，返工成本很高
- 现在我们更需要先确认“multi-year anomaly SCM”这条链在 `2年` 规模上是活的

换句话说:

`先做 2 年，把链跑活；再做 3 年以上，把统计做稳。`

## Decision Rule

可以用这个简单规则选路线:

- 如果你希望今天就能看到新结果: 走 `Plan A`
- 如果你希望下一版结果真正有论文意义: 走 `Plan B`
- 如果你希望开始为正式复现做底座: 走 `Plan C`
