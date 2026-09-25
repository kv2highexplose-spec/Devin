"""Open-Meteo API からのデータ取得 (ERA5再解析アーカイブ / JMA予報)。"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

from . import config

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


def _get(url: str, params: dict, retries: int = 3) -> dict:
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            d = r.json()
            if d.get("error"):
                raise RuntimeError(d.get("reason", "Open-Meteo error"))
            return d
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2**i)
    raise RuntimeError(f"Open-Meteo fetch failed: {last_err}")


def _hourly_to_frame(payload: dict) -> pd.DataFrame:
    h = payload["hourly"]
    df = pd.DataFrame(h)
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time").sort_index()


UNIT_PARAMS = {"wind_speed_unit": "ms", "temperature_unit": "celsius"}


def fetch_point(
    lat: float,
    lon: float,
    variables: list[str],
    start: str,
    end: str,
    elevation: int | None = None,
    forecast: bool = False,
    model: str = "era5",
    cache_key: str | None = None,
) -> pd.DataFrame:
    """1地点のhourlyデータをDataFrameで返す。cache_key指定でparquetキャッシュ。"""
    if cache_key:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fp = CACHE_DIR / f"{cache_key}_{model}_{lat:.3f}_{lon:.3f}_{start}_{end}.parquet"
        if fp.exists():
            return pd.read_parquet(fp)

    if forecast:
        params: dict = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "timezone": config.TIMEZONE,
            "forecast_days": 16,
            "models": model,
            **UNIT_PARAMS,
        }
        url = FORECAST_URL
    else:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(variables),
            "start_date": start,
            "end_date": end,
            "timezone": config.TIMEZONE,
            "models": model,
            **UNIT_PARAMS,
        }
        url = ARCHIVE_URL
    if elevation is not None:
        params["elevation"] = elevation

    df = _hourly_to_frame(_get(url, params))
    if cache_key:
        df.to_parquet(fp)
    return df


def fetch_training_frame(
    start: str, end: str, model: str = "jma_seamless"
) -> pd.DataFrame:
    """主地点+上流点+東側点を結合した学習用フレーム。"""
    tag = f"train_{start}_{end}"
    main = fetch_point(
        config.RESORT_LAT, config.RESORT_LON, config.MAIN_VARS, start, end,
        cache_key=f"{tag}_main", model=model,
    )
    up = fetch_point(
        config.UPSTREAM_LAT, config.UPSTREAM_LON, config.UPSTREAM_VARS, start, end,
        cache_key=f"{tag}_up", model=model,
    ).add_suffix("_up")
    east = fetch_point(
        config.EAST_LAT, config.EAST_LON, config.EAST_VARS, start, end,
        cache_key=f"{tag}_east", model=model,
    ).add_suffix("_east")
    return main.join(up, how="left").join(east, how="left")


def fetch_forecast_frame(
    model: str = "jma_msm", elevation: int = config.MID_ELEV_M
) -> pd.DataFrame:
    """予報モデルのhourlyデータ (学習時と同じ結合構造)。"""
    main = fetch_point(
        config.RESORT_LAT, config.RESORT_LON, config.MAIN_VARS,
        "", "", elevation=elevation, forecast=True, model=model,
    )
    up = fetch_point(
        config.UPSTREAM_LAT, config.UPSTREAM_LON, config.UPSTREAM_VARS,
        "", "", forecast=True, model=model,
    ).add_suffix("_up")
    east = fetch_point(
        config.EAST_LAT, config.EAST_LON, config.EAST_VARS,
        "", "", forecast=True, model=model,
    ).add_suffix("_east")
    return main.join(up, how="left").join(east, how="left")
