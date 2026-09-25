"""定数・地点設定。

余呉高原リゾート・ヤップ (滋賀県長浜市余呉町中河内 栃ノ木峠) の
地理条件をここに集約する。
"""

# --- スキー場 ---
RESORT_LAT = 35.6983
RESORT_LON = 136.1580
BASE_ELEV_M = 540   # 麓(センターハウス付近)
TOP_ELEV_M = 740    # 山頂
MID_ELEV_M = 640    # 予測の代表標高

# --- 補助観測点 ---
# 上流側: 若狭湾〜日本海上。冬季季節風が水分を吸収してくる(fetch)領域。
UPSTREAM_LAT = 36.20
UPSTREAM_LON = 135.70

# 東側: 伊勢湾方面。「西高東低」の気圧傾度を測るための太平洋側代表点。
EAST_LAT = 34.70
EAST_LON = 136.90

# 日本海(若狭湾)から余呉の山間へ雪雲が流入する卓越方位(度, 風が吹いてくる向き)
FETCH_DIRECTION_DEG = 335.0

TIMEZONE = "Asia/Tokyo"

# 1時間あたりこれ以上なら「降雪あり」とみなすしきい値(cm)
SNOW_EPS_CM = 0.05

# 標高差 → 気温の環境減率 (K/m)
LAPSE_RATE_K_PER_M = 0.0065

# 標高100mあたりの地形性降雪増加率(経験則)
ORO_GAIN_PER_100M = 0.12

# 学習に使う気象変数 (Open-Meteo hourly)
MAIN_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "snowfall",
    "pressure_msl",
    "temperature_925hPa",
    "temperature_850hPa",
    "temperature_700hPa",
    "temperature_500hPa",
    "relative_humidity_925hPa",
    "relative_humidity_850hPa",
    "relative_humidity_700hPa",
    "wind_speed_925hPa",
    "wind_direction_925hPa",
    "wind_speed_850hPa",
    "wind_direction_850hPa",
    "geopotential_height_500hPa",
]

UPSTREAM_VARS = [
    "pressure_msl",
    "temperature_850hPa",
    "relative_humidity_850hPa",
    "wind_speed_850hPa",
    "wind_direction_850hPa",
]

EAST_VARS = ["pressure_msl"]
