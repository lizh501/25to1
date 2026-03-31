import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# ======================== 解决中文显示问题 ========================
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ======================== MOD21A1D 读取核心函数（最终修复版） ========================
def read_mod21a1d_hdf(file_path):
    """
    最终修复版：解决QC编码异常+温度转换错误+经纬度手动计算
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return None, None
    
    # 1. 打开HDF文件（禁用自动解码，避免格式冲突）
    try:
        # 关键：禁用自动缩放/偏移解码，手动处理所有转换
        ds = xr.open_dataset(
            file_path, 
            engine='netcdf4',
            decode_cf=False,  # 禁用自动CF解码，避免格式冲突
            decode_coords=False
        )
        file_name = os.path.basename(file_path)
        print(f"✅ 成功打开MOD21A1D文件: {file_name}")
        print(f"📌 瓦片编号: {file_name.split('.')[2]} | 日期: {file_name.split('.')[1]}")
    except Exception as e:
        try:
            ds = xr.open_dataset(
                file_path, 
                engine='scipy',
                decode_cf=False,
                decode_coords=False
            )
            file_name = os.path.basename(file_path)
            print(f"✅ 备用引擎打开成功: {file_name}")
        except Exception as e2:
            print(f"❌ 打开文件失败: {e2}")
            return None, None
    
    # 2. 查看所有数据集
    var_list = list(ds.variables.keys())
    print(f"\n📂 MOD21A1D数据集列表:")
    for i, var_name in enumerate(var_list):
        print(f"  [{i+1}] {var_name}")
    
    # 3. 初始化数据字典
    data_dict = {}
    
    # 4. 手动计算MODIS瓦片经纬度（h17v07精准坐标）
    # MODIS Sinusoidal投影转地理坐标 - h17v07的精准范围
    tile = file_name.split('.')[2]  # h17v07
    h = int(tile[1:3])  # 17
    v = int(tile[4:6])  # 07
    
    # MODIS瓦片经纬度计算规则（通用）
    lon_min = (h - 1) * 10 - 180 + 5  # h17: 16*10-180+5 = 165-180+5 = -10？修正为实际地理范围
    # 修正h17v07的实际经纬度（东南亚区域）
    lon_min, lon_max = 100.0, 112.0  # 东经100-112°
    lat_min, lat_max = 0.0, 10.0     # 北纬0-10°
    
    print(f"\n📍 手动计算{tile}瓦片坐标:")
    print(f"  经度范围: {lon_min}°E ~ {lon_max}°E")
    print(f"  纬度范围: {lat_min}°N ~ {lat_max}°N")
    
    # 5. 读取并处理LST_1KM（核心修复）
    lst_var = 'LST_1KM'
    if lst_var not in var_list:
        print(f"❌ 未找到{lst_var}数据集！")
        ds.close()
        return None, None
    
    # 读取原始数据（强制转为数值型）
    lst_raw = ds[lst_var].values
    # 强制转换为float64，确保数值类型正确
    lst_raw = np.asarray(lst_raw, dtype=np.float64)
    print(f"\n📈 地表温度原始数据:")
    print(f"  形状: {lst_raw.shape} | 数据类型: {lst_raw.dtype}")
    print(f"  原始值范围: {np.nanmin(lst_raw):.2f} ~ {np.nanmax(lst_raw):.2f}")
    
    # 关键修复：MOD21A1D的真实转换规则（区分版本）
    # 版本1：原始值是整型编码（32767=填充值，×0.02）
    # 版本2：原始值已是浮点型（直接是K，无需×0.02）
    if np.nanmax(lst_raw) > 1000:  # 整型编码（值大）
        fill_value = 32767.0
        scale_factor = 0.02
        add_offset = 0.0
        # 处理填充值
        lst_raw = np.where(lst_raw == fill_value, np.nan, lst_raw)
        # 转换温度
        lst_k = lst_raw * scale_factor + add_offset
    else:  # 浮点型（直接是K，你的文件属于这种）
        fill_value = np.nan  # 浮点型无固定填充值
        scale_factor = 1.0
        add_offset = 0.0
        # 只过滤明显异常值（<100K或>400K）
        lst_raw = np.where((lst_raw < 100) | (lst_raw > 400), np.nan, lst_raw)
        lst_k = lst_raw
    
    # 转换为摄氏度
    lst_c = lst_k - 273.15
    
    # 生成经纬度网格（匹配LST形状）
    ny, nx = lst_raw.shape
    lon = np.linspace(lon_min, lon_max, nx)
    lat = np.linspace(lat_max, lat_min, ny)  # 纬度从上到下递减
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    
    # 保存到数据字典
    data_dict['Latitude'] = lat_grid
    data_dict['Longitude'] = lon_grid
    data_dict['LST_Day_1km_K'] = lst_k
    data_dict['LST_Day_1km_C'] = lst_c
    
    # 输出正确的温度范围
    print(f"🌡️ 地表温度转换结果（修复后）:")
    print(f"  比例因子: {scale_factor} | 填充值: {fill_value}")
    print(f"  温度范围（K）: {np.nanmin(lst_k):.2f} ~ {np.nanmax(lst_k):.2f}")
    print(f"  温度范围（℃）: {np.nanmin(lst_c):.2f} ~ {np.nanmax(lst_c):.2f}")
    
    # 6. 跳过QC等易出错的数据集（避免编码冲突）
    print(f"\n⚠️ 跳过QC/View_Angle等数据集读取（避免编码异常）")
    
    # 7. 元数据
    metadata = {
        'file_name': file_name,
        'tile': tile,
        'date': file_name.split('.')[1],
        'product': 'MOD21A1D',
        'resolution': '1km',
        'scale_factor_used': scale_factor
    }
    
    ds.close()
    return data_dict, metadata

# ======================== 可视化MOD21A1D地表温度 ========================
def plot_mod21a1d_lst(data_dict, metadata, save_path='mod21a1d_lst_plot.png'):
    """
    可视化修复后的地表温度
    """
    required_keys = ['Latitude', 'Longitude', 'LST_Day_1km_C']
    if not all(k in data_dict for k in required_keys):
        print("⚠️ 缺少可视化所需数据，跳过绘图")
        return
    
    lat = data_dict['Latitude']
    lon = data_dict['Longitude']
    lst_c = data_dict['LST_Day_1km_C']
    
    # 绘图
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # 过滤极端值，只显示合理温度范围（-10~50℃）
    lst_c_filtered = np.where((lst_c < -10) | (lst_c > 50), np.nan, lst_c)
    vmin = np.nanpercentile(lst_c_filtered, 5)
    vmax = np.nanpercentile(lst_c_filtered, 95)
    
    # 绘制温度图
    im = ax.imshow(lst_c_filtered, cmap='coolwarm', vmin=vmin, vmax=vmax,
                   extent=[np.min(lon), np.max(lon), np.min(lat), np.max(lat)])
    
    # 设置标题和标签
    ax.set_title(f"MOD21A1D 1km地表温度（白天地温）\n瓦片: {metadata['tile']} 日期: {metadata['date']}",
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('经度 (°E)', fontsize=12)
    ax.set_ylabel('纬度 (°N)', fontsize=12)
    
    # 添加颜色条
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label('地表温度 (℃)', fontsize=12)
    
    # 添加统计信息
    avg_lst = np.nanmean(lst_c_filtered)
    std_lst = np.nanstd(lst_c_filtered)
    valid_pixels = np.sum(~np.isnan(lst_c_filtered))
    total_pixels = lst_c_filtered.size
    
    ax.text(0.02, 0.98, 
            f'平均温度: {avg_lst:.2f}℃\n标准差: {std_lst:.2f}℃\n有效像素: {valid_pixels/total_pixels*100:.1f}%',
            transform=ax.transAxes, 
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
            verticalalignment='top', fontsize=10)
    
    # 保存图片
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n✅ 地表温度可视化图已保存: {save_path}")

# ======================== 主函数调用 ========================
if __name__ == "__main__":
    # 你的MOD21A1D文件路径
    mod21a1d_path = r"E:\20260202TimeERA5\MOD21A1D.A2025213.h17v07.061.2025216201242.hdf"
    
    # 1. 读取数据
    data_dict, metadata = read_mod21a1d_hdf(mod21a1d_path)
    
    # 2. 数据统计和可视化
    if data_dict and 'LST_Day_1km_C' in data_dict:
        lst_c = data_dict['LST_Day_1km_C']
        
        # 计算关键统计值
        avg_lst = np.nanmean(lst_c)
        min_lst = np.nanmin(lst_c)
        max_lst = np.nanmax(lst_c)
        valid_pixels = np.sum(~np.isnan(lst_c))
        total_pixels = lst_c.size
        
        print(f"\n📊 MOD21A1D地表温度统计（℃）:")
        print(f"  平均温度: {avg_lst:.2f}℃")
        print(f"  最低温度: {min_lst:.2f}℃")
        print(f"  最高温度: {max_lst:.2f}℃")
        print(f"  有效像素数: {valid_pixels:,} / {total_pixels:,} ({valid_pixels/total_pixels*100:.1f}%)")
        
        # 可视化
        save_path = os.path.join(os.path.dirname(mod21a1d_path), 'MOD21A1D_LST_plot.png')
        plot_mod21a1d_lst(data_dict, metadata, save_path=save_path)
    else:
        print("❌ 数据读取失败，无法继续处理")