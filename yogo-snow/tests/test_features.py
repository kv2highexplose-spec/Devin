import numpy as np
import pandas as pd
import pytest

from yogo_snow import config
from yogo_snow.features import (
    FEATURE_COLUMNS,
    build_features,
    fetch_index,
    snowfall_physics_baseline,
    wet_bulb_stull,
)


def test_wet_bulb_colder_than_dry_bulb():
    tw = wet_bulb_stull(np.array([10.0, 0.0, -5.0]), np.array([50.0, 90.0, 100.0]))
    assert tw[0] < 10.0
    assert -1.0 < tw[1] < 0.5
    # 飽和時は湿球≈乾球
    assert abs(tw[2] - (-5.0)) < 0.3


def test_fetch_index_direction():
    # 北北西風(FETCH_DIRECTION近傍)で最大、南風で0
    spd = pd.Series([10.0, 10.0, 10.0])
    dirs = pd.Series([config.FETCH_DIRECTION_DEG, 180.0, 270.0])
    fi = fetch_index(spd, dirs)
    assert fi.iloc[0] == pytest.approx(10.0)
    assert fi.iloc[1] == pytest.approx(0.0)
    # 西風(270°)はfetch方位から65°ずれ → 0 < 値 < 最大
    assert 0.0 < fi.iloc[2] < 10.0


def _sample_frame(n=48):
    idx = pd.date_range("2025-01-05", periods=n, freq="h")
    d = {
        "temperature_2m": -2.0,
        "relative_humidity_2m": 90.0,
        "dew_point_2m": -3.5,
        "precipitation": 0.5,
        "snowfall": 0.4,
        "pressure_msl": 1015.0,
        "temperature_925hPa": -6.0,
        "temperature_850hPa": -9.0,
        "temperature_700hPa": -15.0,
        "temperature_500hPa": -33.0,
        "relative_humidity_925hPa": 95.0,
        "relative_humidity_850hPa": 90.0,
        "relative_humidity_700hPa": 80.0,
        "wind_speed_925hPa": 14.0,
        "wind_direction_925hPa": 330.0,
        "wind_speed_850hPa": 16.0,
        "wind_direction_850hPa": 335.0,
        "geopotential_height_500hPa": 5300.0,
        "pressure_msl_up": 1022.0,
        "temperature_850hPa_up": -7.0,
        "relative_humidity_850hPa_up": 88.0,
        "wind_speed_850hPa_up": 15.0,
        "wind_direction_850hPa_up": 330.0,
        "pressure_msl_east": 1010.0,
    }
    return pd.DataFrame(d, index=idx)


def test_build_features_columns_and_no_na():
    f = build_features(_sample_frame())
    assert list(f.columns) == FEATURE_COLUMNS
    assert f.notna().all().all()
    # 条件が強いほど fetch_index が大きいこと
    assert f["fetch_index"].iloc[0] > 10.0
    assert f["slp_grad_we"].iloc[0] == pytest.approx(12.0)
    assert f["cold_pool"].iloc[0] == 1.0


def test_physics_baseline_nonnegative_and_scales():
    df = _sample_frame()
    base = snowfall_physics_baseline(df)
    assert (base >= 0).all()

    # 暖かく南風なら指数がほぼ0
    warm = df.copy()
    warm["temperature_2m"] = 8.0
    warm["relative_humidity_2m"] = 70.0
    warm["wind_direction_850hPa"] = 180.0
    warm["temperature_850hPa"] = 2.0
    warm["pressure_msl_up"] = 1008.0
    warm["pressure_msl_east"] = 1012.0
    weak = snowfall_physics_baseline(warm)
    assert weak.mean() < base.mean()
