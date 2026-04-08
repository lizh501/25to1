# Stage 1 Refocus: Long-timeseries Labels and Paper-like SCM

更新时间: `2026-04-08`

## 1. 为什么现在要转回这条主线

最近几轮把 `AWS` 从极小规模扩到了更大的训练网络后，结论已经比较稳定:

- `AWS` 扩站确实有效
- `AWS train -> ASOS validate` 的 paper-like 结果持续变好
- 但收益已经开始明显放缓

当前已验证的趋势大致是:

- `1 AWS`: `rf RMSE 15.234`
- `15 AWS`: `rf RMSE 6.347`
- `87 AWS`: `rf RMSE 4.755`
- `187 AWS`: `rf RMSE 4.544`
- `279 AWS`: `rf RMSE 4.521`
- `379 AWS`: `rf RMSE 4.359`

这说明:

`继续扩 AWS 仍有价值，但已经不再是最核心的 gap。`

现在真正更大的 gap 是两件事:

1. 长时序 `MODIS-derived AT` 标签体系
2. 论文定义的 `SCM`

---

## 2. 当前实现和论文差在哪里

### 2.1 标签体系

论文要的是:

- 基于 `2000-2020`
- 先构造多年 `MODIS-derived air temperature`
- 再用它训练 Stage 1

我们当前做到的是:

- `2018-01 ~ 2018-09`
- station-driven paper-like approximation

也就是说，我们现在已经验证了标签建模方向，但还没有真正进入论文级“多年标签库”的阶段。

### 2.2 SCM

论文要的是:

- `2000-2020 MODIS AT`
- `365` 张 day-of-year 图
- `11-day moving average`
- `10` 轮填补/平滑
- 再按 `ERA5` calendar-day mean/std 标准化

我们之前做的是:

- monthly proxy
- rolling `15-day` proxy
- anomaly proxy

这些都只能算“方向验证”，不能算论文版 `SCM`。

---

## 3. 现在应该优先做什么

### 第一优先级: 形成多年标签库

后面不应该再优先追 `2018` 内更多 AWS 站，而应该开始把标签时间轴拉长，目标是:

1. 按年或按季度补 `MOD11A1 / ERA5 / solar / NDVI`
2. 继续接入 `AWS / ASOS`
3. 形成跨年的 `MODIS-derived AT` 站点建模表
4. 逐年生成 daily `1 km MODIS AT` 栅格

一句话:

`先把多年 daily MODIS-AT 库建出来，SCM 才有真正的输入。`

### 第二优先级: 按论文定义重建 SCM

在有了多年 daily label 之后，再走:

1. 按 `day-of-year` 聚合
2. 形成 `365` 张 climatology
3. 做 `11-day` 环状平滑
4. 多轮缺测填补
5. 用 `ERA5` calendar-day mean/std 做标准化

---

## 4. 这轮新增的代码底座

我已经把论文版 `SCM` 的骨架脚本补上了:

- [build_stage1_scm_paperlike.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_scm_paperlike.py)

它当前支持的逻辑是:

1. 从 daily MODIS-AT 栅格目录读取多年样本
2. 折叠到 `365` 个 calendar day
3. 做 `11-day` 环状平滑
4. 做多轮时间邻域填补
5. 可选输出:
   - `climatology_365`
   - `anomaly_standardized_365`

其中 `anomaly_standardized_365` 会使用 `stage1_simplified_features` 里的 `era5_t2m_c` 做 calendar-day mean/std 标准化。

这不是论文最终版的全部细节，但已经把最关键的统计结构搭起来了。

---

## 5. 接下来最合理的执行顺序

如果我们从现在开始不再分散注意力，最合理的顺序是:

1. 先挑一个更长时间段作为第一阶段多年样本，例如 `2018-2020` 或先做 `2018-2019`
2. 生成这一段的 daily paper-like `MODIS AT` 栅格库
3. 用上面的新脚本生成第一版 `365` 张 paper-like SCM
4. 再把 Stage 1 patch 输入切回更接近论文的 `LR + DEM + Imp + SCM`

---

## 6. 当前最重要的一句话

从现在开始，Stage 1 的主战场不该再是“继续堆更多 2018 AWS 站点”，而应该是:

`把多年 MODIS-AT 标签库和论文版 SCM 真正立起来。`
