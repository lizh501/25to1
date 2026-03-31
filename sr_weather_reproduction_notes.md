# SR-Weather 论文复现与速读笔记

论文: *A super-resolution framework for downscaling machine learning weather prediction toward 1-km air temperature*  
作者: Hyebin Park, Seonyoung Park, Daehyun Kang, Jeong-Hwan Kim  
期刊: *npj Climate and Atmospheric Science* 9, 56 (2026)  
DOI: https://doi.org/10.1038/s41612-026-01328-5

## 1. 一句话讲明白这篇论文

这篇论文做的事情可以概括成一句话:

把 **FuXi 的 0.25° 中期天气预报** 和 **1 km 静态/气候态地表信息** 结合起来，训练一个超分辨率模型 `SR-Weather`，把粗分辨率的 2 m 气温场下采样到 **1 km 日平均气温**。

它不是直接端到端拿 FuXi 训练，而是分成两个阶段:

1. 先用 `ERA5 0.25° T2M -> 1 km MODIS-derived air temperature` 训练一个超分模型。
2. 再把训练好的模型应用到 `FuXi 2020` 预报场上，得到 1 km 的中期气温预报。

## 2. 论文最核心的 4 个点

### 2.1 这是一个“两阶段”框架

- Stage 1: 用 ERA5 日平均 2 m 气温作为低分辨率输入，用 1 km MODIS 推导的 air temperature 作为高分辨率目标，训练超分模型。
- Stage 2: 把训练好的模型直接迁移到 FuXi 的 0.25° 预报上，输出 1 km 预报。

这一步的关键思想是:

**先学“从粗分辨率温度到 1 km 空间纹理”的映射，再把这个映射应用到更强的天气预报模型 FuXi 上。**

### 2.2 目标变量不是 MODIS LST，而是 MODIS-derived air temperature

论文不是直接把 MODIS LST 当标签，而是先把 `MOD11A1 v061` 的 1 km LST 转成 `daily mean air temperature (MODIS AT)`。

这一步非常重要，因为论文真正预测的是 **air temperature**，不是地表温度。

### 2.3 SR-Weather 的提升主要来自 3 个高分辨率辅助因子

- `DEM`: 地形高度
- `Imp`: 不透水面比例
- `SCM`: seasonal climatology map，季节气候态空间温度异常图

这 3 个量分别对应:

- 地形控制
- 城市热岛控制
- 季节性空间温度分布先验

### 2.4 SR-Weather 的真正创新点不是“换了个大模型”，而是“改了注意力”

SR-Weather 是在 `SE-SRCNN` 上改出来的，不是一个完全全新的 backbone。

它的关键改动是:

- 保留 `GAP` 全局平均池化分支
- 新增 `G.Max.P` 全局最大池化分支
- 新增 `G.Min.P` 全局最小池化分支
- 其中 max/min 分支只看 `DEM + SCM`

作者的动机是:

`GAP` 会把局部极值信息平均掉，不利于恢复山脊、谷地、城市热点这类尖锐局地结构。  
新增 `max/min pooling` 后，模型对局部极值和强梯度更敏感。

## 3. 论文方法流程图

## 3.1 Stage 1: 训练超分模型

输入:

- 低分辨率: `ERA5 0.25° daily mean T2M`
- 高分辨率辅助因子: `DEM`, `Imp`, `SCM`

输出:

- 目标: `1 km MODIS AT`

训练后得到:

- 一个从 `0.25° -> 1 km` 的超分模型 `SR-Weather`

## 3.2 Stage 2: 把模型应用到 FuXi

输入:

- `FuXi 0.25°` 预报气温
- 同样的 `DEM`, `Imp`, `SCM`

输出:

- `1 km` 日平均气温预报

## 4. 数据与时间划分

### 4.1 研究区域

- 韩国

作者选择韩国，是因为:

- 地形复杂
- 城市与农村差异显著
- 有较密集站点可以验证

### 4.2 主要数据源

- `ERA5 T2M 0.25°`
- `FuXi forecast 0.25°`，来自 WeatherBench2
- `MOD11A1 v061` 1 km LST
- `SRTM DEM`，重采样到 1 km
- `MCD12Q1 v061` 土地覆盖，用于构建 `Imp`
- `AWS` / `ASOS` 站点数据，用于 MODIS LST 到 air temperature 的建模和验证

### 4.3 时间划分

Stage 1 使用 ERA5 训练超分模型时:

- 训练集: `2001-2015`
- 验证集: `2016-2017`
- 测试集: `2018-2020`

Stage 2 使用 FuXi 推理时:

- 使用 `2020` 年 FuXi 预报
- 评估 lead time: `1-7 天`

## 5. 目标变量是怎么做出来的

### 5.1 MODIS LST -> MODIS AT

论文说明:

- 使用 `MOD11A1 v061`
- 只使用 `Terra`
- 组合前一天和当天的昼夜 LST
- 用辅助因子:
  - incoming solar radiation
  - NDVI
  - latitude
  - longitude
  - DEM
  - terrain aspect
  - impervious surface fraction
- `AWS` 作为训练目标
- `ASOS` 作为独立验证

论文报告这一步的效果:

- MODIS AT 模型: `RMSE = 1.22 K`, `R² = 0.95`
- 直接用 MODIS LST 均值: `RMSE = 4.13 K`, `R² = 0.47`

### 5.2 这意味着什么

你复现时真正的第一个难点不是 SR 模型，而是:

**先把可靠的 1 km 日平均 air temperature 标签做出来。**

如果这一步做偏了，后面所有 SR 指标都会偏。

## 6. SCM 是这篇论文最容易被忽略、但最关键的模块

### 6.1 SCM 的定义

`SCM` 是从 `2000-2020` 的 MODIS AT 构造出来的 `365` 张日序气候态空间图。

做法:

- 对每个 day-of-year 计算多年平均
- 用 `11-day moving average` 平滑
- 反复插值/平滑 `10` 次，填补云导致的缺测
- 再按每个 calendar day 的 ERA5 均值和标准差做标准化

最终得到:

- `365` 张 daily spatial anomaly maps

它表达的是:

**一年中某一天，韩国哪些地方通常偏暖、哪些地方通常偏冷。**

### 6.2 SCM 为什么有效

SCM 给模型提供了一个“季节稳定的空间温度先验”:

- 山区长期偏冷
- 城市区长期偏暖
- 沿海和内陆的季节对比不同

这能帮助模型在 MODIS 标签缺测时仍保持空间结构稳定。

## 7. 模型结构怎么理解

### 7.1 基座: SE-SRCNN

原始 `SE-SRCNN` 的逻辑是:

1. 先把低分辨率温度场 bicubic 到高分辨率网格
2. 低分辨率温度和高分辨率辅助数据分别提特征
3. 拼接特征
4. 用 `SE block` 做 channel attention
5. 卷积重建
6. 和 bicubic 输入做 skip connection

### 7.2 SR-Weather 的变化

SR-Weather 在 attention 这一步改成三路:

- average pooling branch: 看 `LR + DEM + Imp + SCM`
- max pooling branch: 只看 `DEM + SCM`
- min pooling branch: 只看 `DEM + SCM`

然后:

- 每条分支各自过一个轻量两层 gating 网络
- 融合 attention map
- 再进行卷积重建

### 7.3 直觉理解

- `DEM` 决定山顶/山谷的冷暖梯度
- `Imp` 决定城市热岛
- `SCM` 决定季节性的常年空间格局
- `FuXi/ERA5 T2M` 决定当天到底偏暖还是偏冷，以及异常的强弱

所以 SR-Weather 不是简单地把静态地图“贴”到 FuXi 上，而是:

**用静态/气候态信息约束空间纹理，用低分辨率天气场控制当天的温度异常幅度。**

## 8. 训练与推理设置

### 8.1 归一化

- 所有变量都缩放到 `[0, 1]`
- 对低分辨率和高分辨率温度，先做 standard normalization
- 标准化方式与 SCM 一致

### 8.2 patch 策略

论文明确写到:

- `SE-SRCNN / SRGAN / SR-Weather`: 低分辨率 patch 为 `3 x 3`
- overlap: `1/3`
- stride: `2`
- `HAT`: 低分辨率 patch 为 `5 x 5`

基于 `25x` 超分倍率，可以合理推断:

- `3 x 3` 低分辨率 patch 对应大约 `75 x 75` 高分辨率 patch
- `5 x 5` 低分辨率 patch 对应大约 `125 x 125` 高分辨率 patch

这里“高分辨率 patch 大小”是根据论文给出的 `25x spatial resolution enhancement` 推断出来的，正文抓取内容里没有把表格文本完整展开。

### 8.3 样本筛选

- 只有当高分辨率 patch 中 `valid MODIS AT pixels > 100` 时才作为训练样本
- HAT 样本数: `10,558`
- 其余模型样本数: `39,162`

### 8.4 loss 计算

- MODIS AT 的无效像元在 loss 中被 mask 掉

这一点非常重要，否则模型会学到“云缺测”而不是气温结构。

## 9. Stage 2 的 FuXi 推理设置

- 使用 `2020` 年 FuXi 预报
- 先把 `6-hourly` 预报平均成 `daily mean`
- 使用 `1-7 day lead time`
- `Imp` 使用 `2019` 年数据
- 除标准化外，不做额外 preprocessing
- 推理时仍使用和训练一致的 patch-based inference

## 10. 论文结果要记住哪些数字

### 10.1 Stage 1: ERA5 -> MODIS AT

和 bicubic 对比:

- Bicubic: `RMSE = 1.79 K`, `R² = 0.65`, `A-MBE = 1.35 K`
- HAT: `RMSE = 1.47 K`, `R² = 0.77`, `A-MBE = 0.32 K`
- SRGAN: `RMSE = 1.33 K`, `R² = 0.81`, `A-MBE = 0.38 K`
- SE-SRCNN: `RMSE = 1.24 K`, `R² = 0.83`, `A-MBE = 0.43 K`
- SR-Weather: `RMSE = 1.16 K`, `R² = 0.85`, `A-MBE = 0.34 K`

区域细分表现:

- 相对 bicubic，SR-Weather 在高海拔区域 `RMSE 降低 46.4%`
- 在低海拔区域 `RMSE 降低 30.6%`
- 在城市区域 `RMSE 降低 21.6%`

### 10.2 Stage 2: FuXi -> 1 km forecast

- SR-Weather 在 `1-7 天` 所有 lead time 上都最好
- `FuXi 7-day lead + SR-Weather` 的 RMSE，优于 `FuXi 1-day lead + bicubic`
- 相比 LDAPS:
  - `1-day lead` 时 RMSE 低 `0.12 K`
  - `2-day lead` 时 RMSE 低 `0.24 K`

### 10.3 计算代价

- SR-Weather 推理成本约 `8.0 x 10^4 FLOPs / grid cell`
- LDAPS 约 `1.0-1.3 x 10^7 FLOPs / grid cell`
- 约降低 `100-150x` 计算成本

## 11. 真正的复现难点在哪里

### 11.1 最大难点不是网络，而是数据链

你真正要复现的关键链路是:

1. `MOD11A1 -> MODIS AT`
2. `MODIS AT -> SCM`
3. `ERA5 daily T2M + DEM + Imp + SCM -> SR-Weather`
4. `FuXi daily forecast + DEM + Imp + SCM -> 1 km forecast`

前两步比后两步更容易出偏差。

### 11.2 论文没有公开完整代码

论文写得很明确:

- 代码需要向作者申请
- HAT / SRGAN / SE-SRCNN 只给了原始参考论文

这意味着你在复现时必然要自己补这些实现细节:

- 通道数
- 卷积层数
- 损失函数细节
- 优化器
- 学习率
- batch size
- epoch 数
- early stopping 细节

### 11.3 目标标签含缺测

MODIS AT 受云影响有缺测，所以:

- patch 选择策略
- valid-pixel mask
- SCM 填补策略

这三处如果不严谨，指标会差很多。

## 12. 你现在最合理的复现顺序

### 第一阶段: 先复现“标签”和“静态因子”

先不要急着搭深度网络，先把这些数据产物做出来:

1. `MODIS AT`
2. `DEM 1 km`
3. `Imp 1 km`
4. `SCM (365 maps)`
5. `ERA5 daily mean T2M`
6. `训练/验证/测试时间划分`

只要这一步不通，后面训练都是空转。

### 第二阶段: 复现 Stage 1

先只做:

- 输入: `ERA5 + DEM + Imp + SCM`
- 标签: `MODIS AT`
- 模型: 先复现 `SE-SRCNN`
- 再加 `SCM + max/min pooling` 变成 `SR-Weather`

原因:

- 这样最容易验证你的 SR-Weather 改动是否真的有效
- 先跑通 `SE-SRCNN -> SR-Weather`，比直接上 FuXi 更稳

### 第三阶段: 复现 Stage 2

把 Stage 1 训练好的模型直接切到 `FuXi 2020`:

- 先做 daily mean 聚合
- 再跑 `1-7 day lead`
- 再对比站点或 MODIS 有效像元区域

## 13. 你当前工作区的状态判断

### 13.1 当前 `data` 目录是空的

目前 `25to1/data` 下面没有实际数据文件，这意味着:

- 你还没进入可训练阶段
- 当前最优先任务是搭数据准备流水线

### 13.2 当前 `20260210_hdf.py` 和论文并不一致

你现在的脚本 `20260210_hdf.py` 存在几个和论文不一致的地方:

- 读的是 `MOD21A1D`，论文写的是 `MOD11A1 v061`
- 脚本里对 tile 经纬度有硬编码
- 目前逻辑更像是单文件读取和可视化，不是论文需要的批处理数据生产流水线

所以这个脚本可以作为你熟悉 HDF 结构的起点，但不能直接当论文复现主流程。

## 14. 我建议你把论文拆成这三个“复现目标”

### 目标 A: 理解论文

你现在最应该记住的是:

- 这不是单纯的图像超分任务
- 它本质上是“气象粗分辨率场 + 高分辨率地表先验 -> 1 km 气温重建”
- `SCM` 是关键
- `max/min pooling` 是结构创新点

### 目标 B: 先做可运行的简化复现

先不追求完全一模一样，优先追求:

- 能正确生成标签
- 能跑通 Stage 1
- 能看到 `SR-Weather > SE-SRCNN > bicubic` 的趋势

### 目标 C: 再逼近论文结果

后面再逐步补:

- 更严格的 SCM
- 更严格的站点验证
- 更严格的 FuXi 对齐
- 更完整的 baseline

## 15. 如果让我带你复现，最推荐的开工顺序

我建议你下一步按这个顺序推进:

1. 先把 `MOD11A1 / ERA5 / DEM / MCD12Q1 / station` 的目录结构搭好
2. 写 `MODIS AT` 生成脚本
3. 写 `SCM` 生成脚本
4. 写 `ERA5 -> patch dataset` 生成脚本
5. 先复现 `SE-SRCNN`
6. 再改成 `SR-Weather`
7. 最后接 `FuXi`

如果你愿意，我下一步可以直接继续帮你做两件事里的其中一件:

- 方案 1: 先给你把这篇论文的 **复现代码框架** 在当前目录里搭出来
- 方案 2: 先帮你把论文里的 **数据流水线和变量定义** 一步一步落实成脚本清单

## 16. 本笔记使用到的主要来源

- 论文 HTML 页面: https://www.nature.com/articles/s41612-026-01328-5
- 论文 PDF 页面: https://www.nature.com/articles/s41612-026-01328-5_reference.pdf
- 本地论文文件: `25to1/A super-resolution framework for downscaling machine learning weather prediction toward 1-km air temperature.pdf`

