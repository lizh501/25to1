# Stage 1 数据获取清单

目标: 为 `ERA5 -> 1 km MODIS-derived air temperature` 训练阶段准备原始数据。

## 1. 一阶段必须具备的数据

| 数据 | 用途 | 时间范围 | 当前状态 | 官方入口 |
|---|---|---|---|---|
| `MOD11A1 v061` | 1 km LST，构造 MODIS AT 标签 | `2000-2020` | 待下载 | https://lpdaac.usgs.gov/products/mod11a1v061/ |
| `ERA5 daily T2M` | Stage 1 低分辨率输入 | `2001-2020` | 待下载 | https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics?tab=overview |
| `MCD12Q1 v061` | 构造 impervious surface / 土地覆盖辅助因子 | `2001-2020` | 待下载 | https://lpdaac.usgs.gov/products/mcd12q1v061/ |
| `DEM` | 构造地形高度和 terrain aspect | 静态 | 待下载 | https://lpdaac.usgs.gov/products/srtmgl1v003/ |
| `AWS / ASOS` 站点气温 | 训练与验证 MODIS AT 标签 | `2000-2020` | 待申请/下载 | https://data.kma.go.kr/ |
| `NDVI` | MODIS AT 辅助变量 | `2000-2020` | 产品待确认 | 论文提到 NDVI，但当前论文页面未明确具体 MODIS 产品号 |
| `incoming solar radiation` | MODIS AT 辅助变量 | `2000-2020` | 数据源待确认 | 论文提到该变量，但当前论文页面未明确具体数据产品 |

## 2. 目录约定

原始数据目录:

- `data/stage1/raw/mod11a1`
- `data/stage1/raw/era5_daily`
- `data/stage1/raw/mcd12q1`
- `data/stage1/raw/srtm`
- `data/stage1/raw/stations`
- `data/stage1/raw/ndvi`
- `data/stage1/raw/solar_radiation`

中间产物目录:

- `data/stage1/interim`

处理后数据目录:

- `data/stage1/processed`

## 3. 建议先获取的最小可运行子集

如果目标是尽快开工，而不是一次性拉全量 `2000-2020` 数据，建议先拿一个小样本窗口:

- 空间范围: 韩国
- 时间范围: `2018-01-01` 到 `2018-12-31`
- 必要数据: `MOD11A1`, `ERA5 daily T2M`, `DEM`, `MCD12Q1`

这样可以先验证:

1. 空间投影是否对齐
2. 0.25° 到 1 km 的重采样链路是否正确
3. MODIS 有效像元 mask 是否能正常工作

## 4. 凭据要求

### 4.1 NASA Earthdata

用于:

- `MOD11A1`
- `MCD12Q1`
- `SRTMGL1`

需要:

- `EARTHDATA_USERNAME`
- `EARTHDATA_PASSWORD`

### 4.2 Copernicus CDS

用于:

- `ERA5 daily statistics`

需要:

- `CDSAPI_URL`
- `CDSAPI_KEY`

### 4.3 KMA

用于:

- `AWS`
- `ASOS`

说明:

- 该部分通常需要在韩国气象资料开放平台手动申请或登录下载
- 当前工作区未检测到 KMA 相关凭据

## 5. 论文复现里最容易漏掉的点

- 标签不是直接用 LST，而是先生成 `MODIS AT`
- `SCM` 依赖多年 `MODIS AT`
- terrain aspect 可以从 `DEM` 派生，不需要额外下载
- `Imp` 在论文里来自土地覆盖派生，不是单独给出的现成产品

## 6. 当前已完成的准备

- 已创建一阶段目录骨架
- 已加入凭据模板
- 已加入数据检查脚本

运行检查:

```powershell
python 25to1/scripts/check_stage1_data.py --config 25to1/configs/stage1_data_config.example.json
```

