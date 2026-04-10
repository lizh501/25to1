# Stage-1 Model Expansion Research

更新时间: `2026-04-10`

## 1. 先给结论

如果目标是“在当前代码和数据形态上，尽快把模型族扩得更有代表性”，我建议优先新增这 4 个：

1. `resunet_like`
2. `edsr_like`
3. `rcan_like`
4. `swinir_light`

如果目标是“更贴近论文 benchmark 和图像超分文献脉络”，再加这 2 个：

5. `hat_tiny`
6. `deepsd_cascade`

不建议当前优先投入的有：

- `srgan/esrgan`
- diffusion 类超分模型
- `espcn/fsrcnn` 这类显式上采样结构

原因不是这些模型不强，而是**它们和当前 Stage-1 的问题设定不完全匹配**，或者会把精力耗在和主瓶颈不一致的方向上。

---

## 2. 先看“问题本身”，再决定该加什么模型

### 2.1 当前 Stage-1 不是标准的自然图像超分

对照当前实现 [train_stage1_patch_cnn.py](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/scripts/train_stage1_patch_cnn.py)，现在的 patch 模型输入不是单张低分辨率图像，而是已经对齐到 `1 km` 网格的多通道场：

- `era5_t2m_c`
- `dem_m`
- `slope_deg`
- `imp_proxy`
- `lc_type1_majority`
- `lst_day_c`
- `lst_night_c`
- `lst_mean_c`
- `ndvi`
- `solar_incoming_w_m2`
- `valid_*`
- `SCM`
- `aspect_sin/cos`

也就是说，当前问题更像：

**多源栅格条件回归 / image-to-image restoration**

而不是严格意义上的：

**单输入 LR -> HR super-resolution**

这件事非常关键，因为它直接决定哪些模型“加了就能用”，哪些模型“要先重构数据几何才有意义”。

### 2.2 当前任务的统计性质

结合 [stage1_2018_2020_longtimeseries_results.md](/E:/18664-C5F119/华为家庭存储/CUBD/Research/HXGG2025-6-2/hxgg2025-6-2/25to1/stage1_2018_2020_longtimeseries_results.md) 和论文对问题的定义，我认为这个任务有 5 个核心特征：

1. 目标是连续温度场，不是纹理图像。
2. 评价核心是 `RMSE/MAE/R2/偏差`，不是感知质量。
3. 目标场比较平滑，但局地极值、地形梯度、城市热岛很重要。
4. `DEM/Imp/SCM` 这类静态或准静态高分辨率先验很强。
5. 上游 `paper-like MODIS-AT` 标签仍有明显噪声。

这 5 点一起意味着：

- 要优先选**稳定、确定性、回归导向**的模型。
- 要优先选**大感受野、多尺度上下文**模型。
- 要优先选**能自然融合静态辅助场**的模型。
- 不要过早押注“感知型”或“纹理生成型”模型。

---

## 3. 论文和文献对我们最有用的信号

### 3.1 论文本身已经给了一个 benchmark 方向

论文明确把 `HAT`、`SRGAN`、`SE-SRCNN` 作为对比方法，并指出 `SR-Weather` 优势来自于把 `DEM/Imp/SCM` 这类空间上下文真正接进网络，而且在极值恢复上优于更平滑的基线。

来源:

- [SR-Weather paper, Nature](https://www.nature.com/articles/s41612-026-01328-5)

这说明：

- 加 `HAT` 有论文对齐价值。
- `SRGAN` 有 benchmark 对齐价值，但未必有工程优先级。
- “上下文融合能力”比单纯堆深度更重要。

### 3.2 气候/天气下采样里，U-Net 和 DeepSD 两条线都很典型

`DeepSD` 把气候统计下采样写成 stacked SRCNN，这条线和我们的问题最接近，因为它本质上也是“把低分辨率气候变量映射到更高分辨率”。  
来源:

- [DeepSD](https://arxiv.org/abs/1703.03126)

另一方面，近年的天气/气候下采样工作里，`U-Net` 或其 3D 变体很常见。`3D U-Net` 在 2026 的天气后处理工作里对温度预报表现稳定优于 NWP，并强调了多尺度上下文和时序维度编码的重要性。  
来源:

- [3D U-Net for sub-seasonal forecasting (GMD 2026)](https://gmd.copernicus.org/articles/19/27/2026/gmd-19-27-2026.html)
- [U-Net original paper](https://arxiv.org/abs/1505.04597)

这说明：

- `U-Net` 不是“偏分割任务”的外来模型，它在气象下采样里是合理且强势的。
- `DeepSD` 更适合作为“气候/天气 downscaling 传统深度学习基线”。

### 3.3 图像超分主线里，最有代表性的 4 条骨干脉络

1. `SRCNN` 系
2. 残差 CNN 系，比如 `EDSR`
3. 注意力 CNN 系，比如 `RCAN`
4. Transformer 恢复系，比如 `SwinIR / HAT`

代表来源:

- [EDSR](https://arxiv.org/abs/1707.02921)
- [RCAN](https://openaccess.thecvf.com/content_ECCV_2018/html/Yulun_Zhang_Image_Super-Resolution_Using_ECCV_2018_paper.html)
- [SwinIR](https://arxiv.org/abs/2108.10257)
- [HAT](https://arxiv.org/abs/2309.05239)

所以如果我们要让模型组更“像一篇完整论文”，至少应该覆盖：

- 经典浅层 CNN
- 深残差 CNN
- 注意力 CNN
- 多尺度 encoder-decoder
- Transformer
- 气候下采样专用结构

---

## 4. 该加哪些模型

## 4.1 第一优先级: `resunet_like`

### 为什么该加

这是我认为**当前任务最该先加**的模型。

原因：

1. 这个问题非常依赖多尺度上下文。
2. 山地、海岸线、城市热岛都不是纯局部 3x3 卷积能吃干净的。
3. `U-Net`/`ResUNet` 天然适合融合 `DEM/SCM/Imp` 这类静态场。
4. 它和当前“所有输入都已在 HR 网格对齐”的代码形态高度兼容。

### 为什么比直接上 Transformer 更该先做

当前上游标签噪声还比较重，先用一个稳定、强上下文、训练友好的模型，性价比更高。`ResUNet` 往往能更快告诉我们：

- “多尺度上下文”到底值不值钱
- 当前瓶颈是不是确实已从 backbone 转移到标签

### 结论

- `必须加`
- `实现优先级 = 最高`
- `和当前框架适配度 = 非常高`

---

## 4.2 第二优先级: `edsr_like`

### 为什么该加

`EDSR` 是非常标准的强 residual CNN 超分基线。它的意义不是“最像气象模型”，而是：

- 它代表“去掉花哨模块后，深残差 CNN 本身能做到什么程度”
- 可以把当前 `srcnn_like` 和更深的 residual CNN 拉开一档

### 对当前问题的价值

如果 `edsr_like` 明显优于 `srcnn_like`，说明“更深的局部残差建模”本身就有收益。  
如果 `edsr_like` 仍然不行，而 `resunet_like` 更好，说明问题更缺的是多尺度上下文而不是单纯更深的卷积堆叠。

### 结论

- `必须加`
- `实现优先级 = 高`
- `它是最干净的“深残差 CNN”对照组`

---

## 4.3 第三优先级: `rcan_like`

### 为什么该加

`RCAN` 代表“强 CNN + channel attention”路线。论文现在的 `sr_weather_like` 也带 attention，但它是论文定制模块，解释空间比较窄。  
加 `RCAN-like` 的价值在于：

- 用一个社区公认的强 attention CNN 做对照
- 判断当前任务是否真的能从 channel attention 中获得稳定收益

### 和 `sr_weather_like` 的区别

- `sr_weather_like` 是问题定制 attention
- `rcan_like` 是通用强 attention CNN

如果 `rcan_like` 追不上甚至打不过 `sr_weather_like`，说明论文的 attention 设计确实有问题适配价值。  
如果 `rcan_like` 更强，说明我们当前的定制注意力可能还不够成熟。

### 结论

- `必须加`
- `实现优先级 = 高`

---

## 4.4 第四优先级: `swinir_light`

### 为什么该加

如果要补一个 Transformer，我更建议**先上轻量版 `SwinIR`，再决定要不要上 `HAT`**。

原因：

1. `SwinIR` 是恢复任务里非常成熟的 Transformer baseline。
2. 它比 `HAT` 更适合作为“第一批可训练 Transformer 对照组”。
3. 当前标签噪声不低，过重的 Transformer 不一定能带来真实收益。

### 为什么不是先上 `HAT`

`HAT` 的论文对齐意义更强，但实现和训练代价更高。  
如果现在连 `SwinIR-light` 都不能稳定优于 `ResUNet/RCAN`，那更重的 `HAT` 大概率也不会立刻改写结论。

### 结论

- `建议加`
- `实现优先级 = 中高`
- `先做 light 版最合理`

---

## 4.5 第五优先级: `hat_tiny`

### 为什么还值得加

虽然我不建议把 `HAT` 放到第一批，但它仍然值得保留，因为：

1. 当前论文 benchmark 明确用了 `HAT`
2. 它代表更强的 hybrid attention transformer 路线
3. 如果后续要写“对照论文”的复现结论，`HAT` 的说服力会高于 `SwinIR`

### 适合什么时候加

- 在 `ResUNet / EDSR / RCAN / SwinIR-light` 已跑完之后
- 当我们想做“更贴近原论文对比表”的复现时

### 结论

- `建议加`
- `但不该排在第一批`

---

## 4.6 第六优先级: `deepsd_cascade`

### 为什么它很重要

`DeepSD` 是最典型的“气候 statistical downscaling = stacked SRCNN”路线。  
它对我们有两层价值：

1. 它是气候下采样领域的经典深度学习 baseline。
2. 它比纯图像超分模型更贴近“地学 downscaling”叙事。

### 但为什么不建议立刻做

因为 `DeepSD` 更适合**显式尺度级联**，例如 `25 km -> 5 km -> 1 km`。  
而当前 Stage-1 patch pipeline 是“所有输入先对齐到 1 km，再做同尺度回归”。这两者几何设定不一样。

所以：

- 如果不改数据管线，`DeepSD` 会被改得不像 `DeepSD`
- 如果想做对，应该等到我们把 patch 任务重构得更像论文的 `LR -> HR` 超分问题之后再上

### 结论

- `很值得加`
- `但属于第二阶段重构后的模型`

---

## 5. 为什么我不建议优先加 SRGAN / ESRGAN / diffusion

### 5.1 GAN 类

`SRGAN` 在论文里出现，是因为它是经典感知型超分 baseline。  
但对当前问题，我不建议优先投入，原因很直接：

1. 我们优化目标是温度场误差，不是视觉纹理。
2. GAN 很容易制造“看起来锐利但数值不对”的假结构。
3. 当前上游标签本身已经有噪声，GAN 只会让误差解释更困难。

所以：

- 如果你要“论文 benchmark 完整性”，可以后补一个 `srgan_like`
- 如果你要“当前研究效率”，它不是高优先级

### 5.2 diffusion 类

diffusion 超分更重、更慢、更依赖高质量监督，而且常常偏感知质量优化。  
在当前 `paper-like label` 仍有噪声、patch 规模也不是超大、指标以 `RMSE/MAE` 为主的情况下，我不认为 diffusion 是对的问题。

---

## 6. 结合当前代码，最合理的扩模顺序

## 6.1 一个关键实现边界

当前 Stage-1 patch pipeline 不是显式 `LR -> HR` 上采样，而是：

- 先把低分辨率温度和辅助变量都对齐到 `1 km`
- 再做同尺度多通道回归

所以模型实现时要分成两类：

### 可以直接在当前框架下实现

- `resunet_like`
- `edsr_like`
- `rcan_like`
- `swinir_light`
- `hat_tiny`

这些模型都可以把原论文里的“上采样尾部”去掉，改成：

- head: 多通道特征投影
- body: 残差块 / 注意力块 / transformer block
- tail: 同尺度 `1x1` 或 `3x3` 重建头

### 需要先改数据几何再更合理

- `deepsd_cascade`
- `espcn`
- `fsrcnn`

因为它们的原始设计高度依赖：

- 显式倍率
- 像素重排 / 反卷积 / 逐级上采样
- 真正的低分辨率输入张量

如果现在直接硬套到同尺度回归框架里，会失去它们最有代表性的部分。

### 第一批: 不改数据几何，直接扩

1. `resunet_like`
2. `edsr_like`
3. `rcan_like`
4. `swinir_light`

这一批的共同点：

- 输入输出都保持当前 `1 km aligned-grid`
- 不需要把问题重写成显式 LR->HR 上采样
- 能最快告诉我们“多尺度 / 深残差 / 注意力 / Transformer”哪条线最有效

### 第二批: 为论文对齐再扩

5. `hat_tiny`
6. `srgan_like`

这一批更偏“论文 benchmark 对齐”。

### 第三批: 等管线重构后再上

7. `deepsd_cascade`
8. `espcn/fsrcnn`

这一批需要更接近真正的 LR->HR 设定才更合理。

---

## 7. 我建议的最终模型池

如果你想要一个“够代表性、又不失控”的模型池，我建议最终保留：

- `srcnn_like`
- `se_srcnn`
- `sr_weather_like`
- `resunet_like`
- `edsr_like`
- `rcan_like`
- `swinir_light`
- `hat_tiny`

其中：

- `srcnn_like / se_srcnn / sr_weather_like` 负责论文主线
- `resunet_like` 负责气象 downscaling 强多尺度基线
- `edsr_like / rcan_like` 负责 CNN 主线
- `swinir_light / hat_tiny` 负责 Transformer 主线

这 8 个模型已经足够组成一篇像样的 ablation / benchmark 矩阵。

---

## 8. 一句话版本

如果只让我现在选“最该新增的 4 个”，我会选：

1. `resunet_like`
2. `edsr_like`
3. `rcan_like`
4. `swinir_light`

如果再往后补论文对齐版本，再补：

5. `hat_tiny`
6. `deepsd_cascade`

---

## 9. 参考来源

- SR-Weather 论文: [Nature](https://www.nature.com/articles/s41612-026-01328-5)
- DeepSD: [arXiv](https://arxiv.org/abs/1703.03126)
- EDSR: [arXiv](https://arxiv.org/abs/1707.02921)
- RCAN: [ECCV open access](https://openaccess.thecvf.com/content_ECCV_2018/html/Yulun_Zhang_Image_Super-Resolution_Using_ECCV_2018_paper.html)
- SwinIR: [arXiv](https://arxiv.org/abs/2108.10257)
- HAT: [arXiv](https://arxiv.org/abs/2309.05239)
- ESPCN: [CVPR open access](https://openaccess.thecvf.com/content_cvpr_2016/html/Shi_Real-Time_Single_Image_CVPR_2016_paper.html)
- 3D U-Net weather downscaling: [GMD 2026](https://gmd.copernicus.org/articles/19/27/2026/gmd-19-27-2026.html)
- U-Net 原始论文: [arXiv](https://arxiv.org/abs/1505.04597)
