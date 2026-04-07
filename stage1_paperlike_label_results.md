# Stage 1 论文式标签构造首轮结果

更新时间: `2026-04-07`

这一步的目标不是直接提升当前 patch 指标，而是验证:

**如果按论文描述，把 Stage 1 的标签构造往 `MODIS AT` 方向拉近，当前手里的数据到底够不够支撑。**

---

## 1. 这轮做了什么

我新增了两条脚本:

- [build_stage1_modis_at_paperlike_dataset.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/build_stage1_modis_at_paperlike_dataset.py)
- [train_stage1_modis_at_paperlike.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/train_stage1_modis_at_paperlike.py)

它们做的是:

1. 从现有 `Jan-Sep` collocation 表里构造一个更接近论文的标签建模表。
2. 特征改为更贴近论文的组合:
   - `previous-day daytime LST`
   - `previous-day nighttime LST`
   - `same-day daytime LST`
   - `same-day nighttime LST`
   - `solar`
   - `NDVI`
   - `lat`
   - `lon`
   - `DEM`
   - `aspect`
   - `imp_proxy`
3. 按论文思路尝试 `AWS train / ASOS validate`
4. 再额外做一个 pooled `time split` 诊断，判断问题到底出在“特征”还是“站点覆盖”

---

## 2. 生成的数据集

输出数据集:

- [stage1_modis_at_paperlike_dataset.csv](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_jansep/stage1_modis_at_paperlike_dataset.csv)
- [stage1_modis_at_paperlike_dataset_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/processed/modis_at_paperlike_dataset_jansep/stage1_modis_at_paperlike_dataset_summary.json)

数据概况:

- 时间范围: `2018-01-01 ~ 2018-09-30`
- 总行数: `17662`
- `ASOS validate`: `17391`
- `AWS train`: `271`
- `ASOS` 站点数: `64`
- `AWS` 站点数: `1`
- 四次 LST 观测都有效的样本: `1747`
- 至少有一次 LST 有效的样本: `12965`

最重要的现实约束是:

**我们当前只有 `1` 个 AWS 站点。**

这和论文里用大量 `AWS` 训练标签模型不是一个量级。

---

## 3. 论文式 `AWS -> ASOS` 结果

结果文件:

- [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/modis_at_paperlike_jansep/training_summary.json)

### 简单基线

`same-day day/night LST mean`:

- `MAE 4.158`
- `RMSE 5.212`
- `R² 0.789`

`previous-day + same-day four-obs LST mean`:

- `MAE 3.594`
- `RMSE 4.754`
- `R² 0.818`

### 模型结果

`linear_regression`:

- `MAE 10.809`
- `RMSE 12.419`
- `R² -0.288`

`random_forest`:

- `MAE 12.689`
- `RMSE 15.234`
- `R² -0.937`

这说明:

**在“仅 1 个 AWS 站训练、64 个 ASOS 站验证”的条件下，模型已经彻底失真，反而不如简单 LST 均值。**

---

## 4. pooled time-split 诊断结果

为了区分“是特征本身不行”还是“AWS 训练站太少”，我又做了一个全站 pooled 的时间切分:

- `train`: `2018-01-01 ~ 2018-06-30`
- `test`: `2018-07-01 ~ 2018-09-30`

结果同样在:

- [training_summary.json](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/data/stage1/models/modis_at_paperlike_jansep/training_summary.json)

### 简单基线

`same-day LST mean`:

- `RMSE 4.397`

`four-obs LST mean`:

- `RMSE 3.946`

### 模型

`linear_regression`:

- `RMSE 8.121`

`random_forest`:

- `RMSE 5.776`

这说明两件事:

1. 只按论文里那组标签特征做，在我们当前 `2018 Jan-Sep` 的有限数据上还远远不够。
2. 当前最强的标签链并不是“更像论文的这套 station label 模型”，而仍然是我们之前那个依赖更多格点信息的 bootstrap 方案。

---

## 5. 这轮最重要的判断

这次实验把一个关键事实说清楚了:

### 5.1 目前最大的瓶颈确实是 `AWS` 覆盖不足

论文能得到:

- `AWS train`
- `ASOS validate`
- `RMSE = 1.22 K`

但我们当前只有:

- `1` 个 AWS 站

这意味着:

- 论文式标签模型现在在统计意义上根本不成立

### 5.2 但不只是 AWS 数量问题

即便做 pooled time split，这套更像论文的标签特征仍然偏弱。

这说明我们当前和论文还有额外差距，例如:

- 缺少多年时段
- 缺少真正的 `2000-2020` 标签构造背景
- 还没有完全复刻论文里 `MODIS AT` 标签模型本身的建模细节

### 5.3 这也解释了为什么当前 bootstrap 流程“看起来更好”

因为我们现有 bootstrap 流程本质上是:

- 更强的工程化输入
- 更宽松的标签近似
- 更适合先把 Stage 1 数据链跑通

所以它更像:

- `工程 sanity check`

而不是:

- `严格论文标签复现`

---

## 6. 下一步最合理的顺序

基于这轮结果，最合理的后续优先级是:

1. 先扩 `AWS` 站点覆盖，而不是继续在 `1 个 AWS` 上调模型。
2. 在标签层把 `previous-day + same-day` 四次 LST 组合保留下来。
3. 等 `AWS` 站覆盖起来后，再重跑真正的 `AWS train / ASOS validate`。
4. 在此之前，不要急着用这一版 paperlike label 去替换当前 bootstrap 主线。

一句话总结就是:

**这轮实验不是失败，而是把“论文式标签复现的首要瓶颈是 AWS 数据量”这件事定量确认了。**

