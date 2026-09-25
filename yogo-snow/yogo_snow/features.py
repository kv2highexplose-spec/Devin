"""特徴量エンジニアリング。

余呉(湖北)の降雪は典型的な日本海側パターン:
  1. シベリア高気圧→太平洋低気圧の「西高東低」で西北西〜北の季節風が吹く
  2. 風が暖かい日本海(若狭湾)上で水蒸気・下層熱を吸収
  3. 国境の山地(栃ノ木峠〜余呉湖西方の稜線)で強制上昇 → 地形性豪雪

よって特徴量は「寒気の強さ(T850/T500)」「季節風の向きと強さ(fetch index)」
「海上での加湿(RH850, 上流との差)」「気圧配置(西高東低勾配)」
「雨雪判別(湿球温度)」を軸に組む。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

FEATURE_COLUMNS = [
    # 気温・湿り
    "temperature_2m",
    "twb_2m",
    "dew_point_2m",
    "rh_2m",
    # 寒気
    "temperature_925hPa",
    "temperature_850hPa",
    "temperature_700hPa",
    "temperature_500hPa",
    "geopotential_height_500hPa",
    # 加湿
    "relative_humidity_925hPa",
    "relative_humidity_850hPa",
    "relative_humidity_700hPa",
    # 風
    "wind_speed_925hPa",
    "wind_speed_850hPa",
    "u850",
    "v850",
    "u925",
    "v925",
    # 日本海側パターン指標
    "fetch_index",
    "fetch_index_6h",
    "slp_grad_we",
    "upstream_rh850",
    "upstream_t850",
    "upstream_warming",
    "cold_pool",
    # 降水・時間
    "precipitation",
    "t850_6h",
    "doy_sin",
    "doy_cos",
]


def wet_bulb_stull(t_c: np.ndarray, rh_pct: np.ndarray) -> np.ndarray:
    """Stull(2011)の湿球温度近似式。気温°C・相対湿度% → 湿球温度°C。"""
    t = np.asarray(t_c, dtype=float)
    rh = np.clip(np.asarray(rh_pct, dtype=float), 1e-3, 100.0)
    return (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * rh**1.5 * np.arctan(0.023101 * rh)
        - 4.686035
    )


def _uv(speed: pd.Series, direction_deg: pd.Series) -> tuple[pd.Series, pd.Series]:
    """風速・風向(吹いてくる向き,度) → u,v成分(東向き+,北向き+)。"""
    rad = np.deg2rad(direction_deg)
    return -speed * np.sin(rad), -speed * np.cos(rad)


def fetch_index(speed: pd.Series, direction_deg: pd.Series) -> pd.Series:
    """日本海からのfetchスコア: 風が fetch方位側から吹く成分の風速。

    speed * max(0, cos(wd - FETCH_DIRECTION)) で、北北西風ほど大きく
    南風では0になる単調な指標。
    """
    align = np.cos(np.deg2rad(direction_deg - config.FETCH_DIRECTION_DEG))
    return speed * np.clip(align, 0.0, None)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """結合済みフレーム(主地点+_up+_east列)から特徴量フレームを作る。"""
    # Open-Meteoは欠損をnullで返し、列がobject dtypeになるため数値化する
    df = df.apply(pd.to_numeric, errors="coerce")
    f = pd.DataFrame(index=df.index)

    f["temperature_2m"] = df["temperature_2m"]
    f["rh_2m"] = df["relative_humidity_2m"]
    f["dew_point_2m"] = df["dew_point_2m"]
    f["twb_2m"] = wet_bulb_stull(df["temperature_2m"], df["relative_humidity_2m"])

    for c in [
        "temperature_925hPa", "temperature_850hPa", "temperature_700hPa",
        "temperature_500hPa", "geopotential_height_500hPa",
        "relative_humidity_925hPa", "relative_humidity_850hPa",
        "relative_humidity_700hPa", "wind_speed_925hPa", "wind_speed_850hPa",
    ]:
        f[c] = df[c]

    u850, v850 = _uv(df["wind_speed_850hPa"], df["wind_direction_850hPa"])
    u925, v925 = _uv(df["wind_speed_925hPa"], df["wind_direction_925hPa"])
    f["u850"], f["v850"] = u850, v850
    f["u925"], f["v925"] = u925, v925

    f["fetch_index"] = fetch_index(
        df["wind_speed_850hPa"], df["wind_direction_850hPa"]
    )
    f["fetch_index_6h"] = f["fetch_index"].rolling(6, min_periods=1).mean()

    # 西高東低: 日本海上の気圧 - 太平洋側の気圧 (正で季節風型)
    f["slp_grad_we"] = df["pressure_msl_up"] - df["pressure_msl_east"]

    # 上流(日本海上)の状態: 雪雲の「燃料」
    f["upstream_rh850"] = df["relative_humidity_850hPa_up"]
    f["upstream_t850"] = df["temperature_850hPa_up"]
    # 海上での下層加湿 = 沿岸より沖の方が湿っている度合い
    f["upstream_warming"] = (
        df["temperature_850hPa_up"] - df["temperature_850hPa"]
    )

    # JPCZレベルの寒気の目安: 500hPa -30°C
    f["cold_pool"] = (df["temperature_500hPa"] <= -30.0).astype(float)

    f["precipitation"] = df["precipitation"]
    f["t850_6h"] = df["temperature_850hPa"].rolling(6, min_periods=1).mean()

    doy = df.index.dayofyear
    f["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    f["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)

    return f[FEATURE_COLUMNS]


def snowfall_physics_baseline(df: pd.DataFrame) -> pd.Series:
    """説明用のルールベース降雪指数(cm/h)。

    MLモデルと併記する「定性的な裏付け」: 湿球温度で雨雪を切り、
    fetch・寒気・気圧勾配で強弱を付ける。絶対値は目安。
    """
    df = df.apply(pd.to_numeric, errors="coerce")
    twb = wet_bulb_stull(df["temperature_2m"], df["relative_humidity_2m"])
    phase = np.clip((0.8 - twb) / 1.5, 0.0, 1.0)          # 雪<雨
    fetch = fetch_index(df["wind_speed_850hPa"], df["wind_direction_850hPa"])
    cold = np.clip((-2.0 - df["temperature_850hPa"]) / 8.0, 0.0, 1.0)
    grad = np.clip((df["pressure_msl_up"] - df["pressure_msl_east"]) / 12.0, 0.0, 1.0)
    moist = df["relative_humidity_850hPa"] / 100.0
    return pd.Series(
        3.0 * phase * moist * (0.4 * np.clip(fetch / 12.0, 0, 1) + 0.4 * cold + 0.2 * grad),
        index=df.index,
    )
