# Stage 1 Bootstrap 数据状态

更新时间: 2026-03-31

## 已确认的韩国 MODIS tiles

- `h27v05`
- `h28v05`
- `h29v05`

## 已经实际下载到本地的数据

### 1. MOD11A1

- 时间范围: `2018-01-01` 到 `2018-01-31`
- granule 数: `94`
- 本地目录: `25to1/data/stage1/raw/mod11a1`

说明:

- 包含 `2017-12-31` 的一个跨日 granule
- 其余是 `2018-01` 的日尺度 `3 tiles/day`
- 已生成 `31` 个完整日的拼接输出
- 日拼接输出目录: `25to1/data/stage1/interim/mod11a1_daily`
- 每天包含:
  - `*_lst_day_c.tif`
  - `*_lst_night_c.tif`
  - `*_qc_day.tif`
  - `*_qc_night.tif`

### 2. MCD12Q1

- 时间范围: `2018`
- granule 数: `3`
- 本地目录: `25to1/data/stage1/raw/mcd12q1`
- 已生成静态土地覆盖产物:
  - `25to1/data/stage1/processed/mcd12q1_lc_type1_korea_500m.tif`
  - `25to1/data/stage1/processed/mcd12q1_lc_type1_majority_korea_1km.tif`
  - `25to1/data/stage1/processed/mcd12q1_imp_proxy_korea_1km.tif`

说明:

- `imp_proxy` 是依据 `LC_Type1` 中 `Urban and Built-up Lands = 13` 聚合得到的 `1 km` 城市建成区比例代理
- 这一步是合理复现近似，但不是论文作者公开说明过的精确 `Imp` 构造公式

### 3. ERA5 daily mean T2M

- 时间范围: `2018-01`
- 文件数: `1`
- 文件: `25to1/data/stage1/raw/era5_daily/era5_daily_t2m_2018_01.nc`

ERA5 文件检查:

- 文件头是 `HDF5/NetCDF4`
- 变量包含:
  - `latitude`
  - `longitude`
  - `number`
  - `t2m`
  - `valid_time`

补充:

- 在 `python312` 环境里可通过 `netCDF4.Dataset` 正常读取
- `xarray + netCDF4` 在当前中文绝对路径下有兼容问题，后续建议优先用相对路径或直接用 `netCDF4`

### 4. SRTMGL1

- 韩国 bbox granule 数: `44`
- 已下载 zip: `44`
- 已解压 hgt: `44`
- 清单文件: `25to1/data/stage1/interim/srtm_korea_preview.json`
- 原始目录: `25to1/data/stage1/raw/srtm`
- 解压目录: `25to1/data/stage1/raw/srtm/unpacked`
- 韩国范围 DEM mosaic:
  - `25to1/data/stage1/processed/srtm_dem_korea_wgs84.tif`
  - CRS: `EPSG:4326`
  - 尺寸: `25200 x 23400`
  - 边界约: `124.50E-131.50E, 33.00N-39.50N`
- 已派生地形因子:
  - `25to1/data/stage1/processed/srtm_slope_korea_wgs84.tif`
  - `25to1/data/stage1/processed/srtm_aspect_korea_wgs84.tif`
  - slope 范围约: `0.0° ~ 89.9°`
  - aspect 范围约: `0.0° ~ 359.4°`

### 5. python312 环境

当前已确认可用:

- `numpy`
- `requests`
- `xarray`
- `netCDF4`
- `cdsapi`
- `rasterio`
- `pyhdf`

说明:

- `MOD11A1` 目前已可通过 `pyhdf` 读取
- `MOD11A1` 批量拼接脚本:
  - `25to1/scripts/build_mod11a1_daily_mosaics.py`
- `SRTM` 派生脚本:
  - `25to1/scripts/derive_srtm_slope_aspect.py`
- 样本文件 `MOD11A1.A2018001.h28v05...hdf` 检查结果:
  - `LST_Day_1km` 形状 `1200 x 1200`
  - 有效像元 `182,075`
  - 白天地表温度约 `-25.87°C ~ 15.15°C`

## 还没开始下载的数据

- `AWS / ASOS` 站点数据
- `NDVI`
- `incoming solar radiation`

## 当前最适合继续做的事情

1. 补 `NDVI`
2. 补 `incoming solar radiation`
3. 用 `MOD11A1 + ERA5 + DEM/aspect + imp_proxy` 先搭一个简化版标签生成流水线
4. 再扩展到 `2018` 全年甚至 `2000-2020`
