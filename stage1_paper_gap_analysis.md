# Stage 1 对照论文差距分析

更新时间: `2026-04-07`

对照对象:

- 论文 PDF: `25to1/A super-resolution framework for downscaling machine learning weather prediction toward 1-km air temperature.pdf`
- 当前实现主脚本:
  - `25to1/scripts/build_stage1_simplified_feature_stacks.py`
  - `25to1/scripts/build_stage1_modis_at_bootstrap.py`
  - `25to1/scripts/build_stage1_scm_bootstrap.py`
  - `25to1/scripts/build_stage1_patch_index.py`
  - `25to1/scripts/train_stage1_patch_cnn.py`

---

## 1. 结论先行

如果只回答“有没有重大出入”，答案是:

**有，而且不止一处。**

但需要区分两层意思:

1. **Stage 1 的“大框架方向”基本对了。**
2. **Stage 1 的“关键定义和训练几何”与论文仍有明显偏差。**

所以当前这套更准确的定位是:

**论文 Stage 1 的 bootstrap / engineering sanity-check 版本，而不是严格论文级复现。**

---

## 2. 哪些地方是“基本一致”的

这些部分说明我们没有跑偏主线:

### 2.1 两阶段思想是一致的

论文: 先用 `ERA5 -> 1 km MODIS-derived AT` 学空间超分，再迁移到 `FuXi`。  
当前: 也是先围绕 `ERA5 + 高分辨率辅助信息` 建 `Stage 1`，再为后续 `Stage 2` 做准备。

判断:

- `一致`

### 2.2 研究区域和主数据骨架是一致的

论文方法部分第 `7` 页明确写的是:

- 韩国区域
- `ERA5 0.25° T2M`
- `MODIS LST`
- `DEM`
- `Imp`
- `AWS/ASOS`

当前:

- 区域也是韩国
- 也用了 `ERA5 + MODIS + DEM + imp_proxy + AWS/ASOS`

判断:

- `一致`

### 2.3 我们已经意识到 `SCM` 是核心，而不是可有可无的附加图层

论文第 `7-8` 页把 `SCM` 放在非常核心的位置。  
当前我们也已经把 `SCM` 单独抽出来做 rolling / anomaly / longer-baseline 实验。

判断:

- `方向一致`

---

## 3. 重大出入

下面这些是我认为会直接影响“能不能叫论文级 Stage 1 复现”的关键差距。

## 3.1 目标标签定义已经发生了实质变化

### 论文怎么做

论文第 `7` 页明确写的是:

- 先把 `MOD11A1 v061` 的 `1 km Terra LST`
- 用“前一天 + 当天”的昼夜观测组合
- 加 `incoming solar radiation, NDVI, latitude, longitude, DEM, terrain aspect, impervious surface fraction`
- 用 `AWS` 训练
- 用 `ASOS` 独立验证
- 生成 `2000-2020` 的 gridded `MODIS AT`

也就是说，论文 Stage 1 的监督目标不是站点均温本身，而是:

**先构造一个完整定义的 `1 km MODIS-derived air temperature` 数据集，再用它训练超分模型。**

### 我们现在怎么做

当前 `build_stage1_modis_at_bootstrap.py` 里，目标直接就是 `station_avg_temp_c`，见:

- [build_stage1_modis_at_bootstrap.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_modis_at_bootstrap.py#L19)

当前用于拟合伪标签的特征包括:

- `era5_t2m_c`
- `dem_m`
- `slope_deg`
- `aspect_deg`
- `imp_proxy`
- `lc_type1_majority`
- `lst_day_c`
- `lst_night_c`
- `lst_mean_c`
- `ndvi`
- `solar_incoming_w_m2`
- `valid_day`
- `valid_night`
- `valid_mean`

见:

- [build_stage1_modis_at_bootstrap.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_modis_at_bootstrap.py#L24)

### 为什么这是重大出入

因为这里改掉了 4 个关键定义:

1. 论文是 `MODIS AT` 标签构造，我们现在是 `station_avg_temp_c -> pseudo-grid`。
2. 论文明确区分 `AWS 训练 / ASOS 验证`，我们当前 collocation 训练默认混合使用不同 source。
3. 论文标签模型包含 `latitude / longitude`，我们当前没有。
4. 论文标签模型使用“前一天 + 当天”的昼夜 LST 组合，我们当前只用当天日/夜和日夜平均。

结论:

- `重大出入`
- 这是当前最重要的 gap

---

## 3.2 我们的 `SCM` 不是论文里的 `SCM`

### 论文怎么做

论文第 `7` 页对 `SCM` 的定义非常具体:

- 数据基础: `2000-2020` 的 `MODIS AT`
- 先按 `day-of-year` 做多年平均，得到 `365` 张图
- 用 `11-day moving average`
- 对缺测做额外插值和平滑
- 上述迭代共 `10` 次
- 再按每个 calendar day 的 `ERA5` 均值和标准差做标准化
- 最终得到 `365` 张 `daily spatial anomaly maps`

### 我们现在怎么做

当前 `build_stage1_scm_bootstrap.py` 只有两种近似:

- `monthly`
- `rolling`

代码位置:

- [build_stage1_scm_bootstrap.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_scm_bootstrap.py#L78)

具体实现是:

- 对现有 bootstrap 伪标签直接做月平均，或
- 做一个短窗 `rolling` 平均

见:

- [build_stage1_scm_bootstrap.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_scm_bootstrap.py#L94)
- [build_stage1_scm_bootstrap.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_scm_bootstrap.py#L120)

### 为什么这是重大出入

因为论文里的 `SCM` 本质上是:

**长期多年气候态异常图**

而我们现在的是:

**短时间段伪标签均值图**

少掉了这些关键环节:

- `2000-2020` 长时段
- `365 day-of-year climatology`
- `11-day moving average`
- `10次` 迭代平滑/插值
- `ERA5` calendar-day anomaly standardization

这不是“公式稍微不同”，而是统计定义已经换了。

结论:

- `重大出入`

---

## 3.3 Stage 1 超分模型的输入几何已经和论文不是同一个问题

### 论文怎么做

论文第 `8-9` 页说得很明确:

- `SR-Weather / SE-SRCNN` 的核心输入是
  - bicubic 之后的低分辨率 `LR temperature`
  - 高分辨率辅助因子 `DEM, Imp, SCM`
- `SE-SRCNN` 和 `SR-Weather` 都是围绕
  - 低分辨率温度分支
  - 高分辨率辅助分支
  - attention / gating
  - skip connection
  来构建的

Table 1 还明确给出:

- `SR-Weather` 输入变量: `Bicubic LR, DEM, Imp, SCM`
- `SE-SRCNN` 输入变量: `Bicubic LR, DEM, Imp`

### 我们现在怎么做

当前 patch 输入通道是:

- `era5_t2m_c`
- `dem_m`
- `slope_deg`
- `imp_proxy`
- `lc_type1_majority`
- `lst_day_c`
- `lst_night_c`
- `lst_mean_c`
- `scm_bootstrap_c`
- `ndvi`
- `solar_incoming_w_m2`
- `valid_day`
- `valid_night`
- `valid_mean`
- `aspect_sin`
- `aspect_cos`

见:

- [train_stage1_patch_cnn.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/train_stage1_patch_cnn.py#L14)

而且这些输入在进入网络前已经全部是同一张 `1 km` 网格上的张量，而不是“真正的 LR patch + HR aux”双分支结构。

### 为什么这是重大出入

这会把任务本身改掉:

1. 论文想学的是 `0.25° temperature -> 1 km temperature texture`
2. 我们现在更像是在学 `多源1 km特征 -> 1 km伪标签`

尤其是我们把 `LST day/night/mean` 直接放进 patch 模型后，模型会看到非常接近目标热力纹理的强特征，这和论文中 Stage 1 的主输入定义已经不一样了。

结论:

- `重大出入`

---

## 3.4 patch 几何和样本筛选条件没有对齐论文

### 论文怎么做

论文第 `9` 页 Table 1 和正文写的是:

- `SR-Weather / SE-SRCNN / SRGAN`
  - LR patch = `3 x 3`
  - HR patch = `75 x 75`
  - overlap = `1/3`
  - stride = `2`
- 训练 patch 要求:
  - 对应 HR patch 中 `valid MODIS AT pixels > 100`

### 我们现在怎么做

当前 patch index 默认是:

- `patch_size = 64`
- `stride = 64`
- `min_valid_frac = 0.5`

见:

- [build_stage1_patch_index.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_patch_index.py#L101)

### 为什么这是重大出入

这里不是只差 `75` 和 `64` 这么简单，而是:

1. 论文 patch 是围绕 `25x` 超分倍率定义的 `LR->HR` 配对。
2. 我们 patch 是在已经投到 `1 km` 的全分辨率网格上直接裁块。
3. 论文用的是“有效像元数 > 100”，我们用的是“有效比例 > 0.5”。
4. 论文有显式 overlap / stride 设计，我们现在是无 overlap 的方块切片。

这会改变:

- 训练样本数量
- 感受野
- 边界效应
- 输出拼接方式

结论:

- `重大出入`

---

## 4. 中等出入

这些不会推翻整个方向，但会直接影响“论文数值能不能拿来对比”。

## 4.1 时间切分和样本时间范围还远不够

### 论文怎么做

论文第 `2` 页写得很明确:

- 训练: `2001-2015`
- 验证: `2016-2017`
- 测试: `2018-2020`

并且评估时使用的是:

- 去除长期气候态后的 `temperature anomalies`

### 我们现在怎么做

当前 Stage 1 主要还是:

- `2018-01 ~ 2018-09`
- 做 `Jan-Feb->Mar`、`Jan-Apr->May-Jun`、`Jan-Jun->Jul-Sep` 这类时间外推
- 评价指标多是原始温度 RMSE / MAE / R²

### 影响

- 当前结果可以用于工程诊断
- 但不能拿去和论文里的 Stage 1 数值做严格横向对比

结论:

- `中等出入`

---

## 4.2 归一化方式没有完全按论文执行

### 论文怎么做

论文第 `9` 页写的是:

- 所有变量缩放到 `[0, 1]`
- 温度变量先按与 `SCM` 相同的方法做 standard normalization
- 再做 `[0, 1]` 归一化

### 我们现在怎么做

当前 `train_stage1_patch_cnn.py` 里对不同变量主要是:

- clipping
- 手写比例缩放
- `nan_to_num`

见:

- [train_stage1_patch_cnn.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/train_stage1_patch_cnn.py#L46)

### 影响

- 会影响不同变量的数值权重
- 也会影响论文模型结构对 `SCM` 的利用效率

结论:

- `中等出入`

---

## 4.3 `SR-Weather-like` 还不是严格的 `SR-Weather`

### 论文怎么做

论文第 `8` 页定义的是:

- LR 分支与 HR 辅助分支分别提特征
- GAP 分支看所有输入
- max/min 分支只看 `DEM + SCM`
- attention 融合后重建
- skip connection 加回 bicubic LR

### 我们现在怎么做

当前 `sr_weather_like` 只是一个近似版:

- 全通道直接一起卷积
- 再对 `DEM + scm_bootstrap_c` 做 pooling gate

见:

- [train_stage1_patch_cnn.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/train_stage1_patch_cnn.py#L224)

### 影响

- 它可以验证 pooling/gating 思路是否有价值
- 但还不能算“结构级完全复现”

结论:

- `中等出入`

---

## 5. 轻微出入或可以接受的近似

## 5.1 `Imp` 的近似方式

论文:

- previous-year `MCD12Q1` urban fraction

当前:

- 基于 `LC_Type1=13` 聚合成 `imp_proxy`

这不是完全等价，但逻辑比较一致，且在没有作者原始代码时是合理近似。

结论:

- `轻微到中等`

## 5.2 DEM / terrain aspect 的使用

这部分基本合理，没有明显方向性偏差。

结论:

- `基本一致`

---

## 6. 论文自身也有一个需要注意的歧义

论文内部关于 LST 产品存在一个小矛盾:

- 方法部分第 `7` 页写的是 `MOD11A1 v061`
- 数据可用性部分第 `9` 页链接写成了 `MOD21A1D`

当前我们采用的是:

- `MOD11A1`

我认为这是合理选择，因为它和方法正文、参考文献 `MOD11A1` 更一致。

结论:

- 这不是我们当前实现的主要问题
- 但在正式论文级复现文档里，最好单独标注这个 paper-side ambiguity

---

## 7. 最终判断

### 如果按“论文骨架是否对齐”来问

答案是:

- `大体对齐`

### 如果按“Stage 1 是否已经论文级复现”来问

答案是:

- `还没有`

### 当前最关键的 4 个 major gap

1. `MODIS AT` 标签构造没有按论文定义完成。
2. `SCM` 仍是 bootstrap proxy，不是论文的 365-day climatological anomaly maps。
3. patch 输入问题已经从 `LR->HR super-resolution` 变成了 `multi-channel 1 km regression`。
4. patch 几何、样本筛选、归一化没有对齐论文。

---

## 8. 如果要把当前 Stage 1 拉回论文主线，优先级应该怎么排

最建议的顺序是:

1. **先修标签层**  
   把 `MODIS AT` 真正按论文方式重建出来，至少先补上:
   - `previous-day + same-day` LST 组合
   - `lat/lon`
   - `AWS train / ASOS validate`

2. **再修 SCM**  
   做成真正的 `365-day` climatological anomaly maps，而不是 rolling mean proxy。

3. **再修 patch geometry**  
   回到论文的 `3x3 LR -> 75x75 HR`，并按 `valid pixels > 100` 选样本。

4. **最后修网络结构**  
   这时再去做严格版 `SE-SRCNN / SR-Weather` 才有意义。

原因很简单:

**当前最大的偏差不在 backbone，而在标签定义和问题设定。**

