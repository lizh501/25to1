import json
import math
import os
from datetime import date, timedelta
from pathlib import Path


MODIS_SINUSOIDAL_RADIUS = 6371007.181
MODIS_TILE_SIZE_M = 1111950.5196666666
MODIS_XMIN = -20015109.354
MODIS_YMAX = 10007554.677


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def workspace_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parents[2]


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def modis_hv_from_latlon(lat: float, lon: float) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    x = MODIS_SINUSOIDAL_RADIUS * lon_rad * math.cos(lat_rad)
    y = MODIS_SINUSOIDAL_RADIUS * lat_rad
    h = int(math.floor((x - MODIS_XMIN) / MODIS_TILE_SIZE_M))
    v = int(math.floor((MODIS_YMAX - y) / MODIS_TILE_SIZE_M))
    return h, v


def modis_tiles_for_bbox(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    samples_per_axis: int = 32,
) -> list[str]:
    tiles = set()
    for i in range(samples_per_axis + 1):
        lat = min_lat + (max_lat - min_lat) * i / samples_per_axis
        for j in range(samples_per_axis + 1):
            lon = min_lon + (max_lon - min_lon) * j / samples_per_axis
            h, v = modis_hv_from_latlon(lat, lon)
            tiles.add(f"h{h:02d}v{v:02d}")
    return sorted(tiles)


def month_strings(start_year: int, end_year: int) -> list[str]:
    months = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            months.append(f"{year:04d}-{month:02d}")
    return months


def year_strings(start_year: int, end_year: int) -> list[str]:
    return [f"{year:04d}" for year in range(start_year, end_year + 1)]

