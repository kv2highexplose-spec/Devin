import numpy as np
import pandas as pd

from yogo_snow import config
from yogo_snow.model import YogoSnowModel, daily_summary, evaluate


def _synthetic(n=24 * 30, seed=0):
    """季節風が強いほど雪が降る合成データ。"""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-12-01", periods=n, freq="h")
    fetch = rng.uniform(0, 18, n)
    t850 = rng.uniform(-14, 2, n)
    twb = t850 * 0.1 + rng.normal(-2, 1.5, n)
    rate = np.clip(0.25 * fetch + 0.2 * (-4 - t850) - 0.6, 0, 6)
    snow = np.where((twb < 0.5) & (rng.random(n) < rate / 6), rate * rng.uniform(0.5, 1.5, n), 0.0)

    d = {
        "temperature_2m": twb + 1.0,
        "relative_humidity_2m": np.clip(80 + (rate), 0, 100),
        "dew_point_2m": twb - 1,
        "precipitation": snow * 0.7 + 0.05,
        "snowfall": snow,
        "pressure_msl": 1015 + rng.normal(0, 2, n),
        "temperature_925hPa": t850 + 3,
        "temperature_850hPa": t850,
        "temperature_700hPa": t850 - 7,
        "temperature_500hPa": t850 - 25,
        "relative_humidity_925hPa": 90.0,
        "relative_humidity_850hPa": 88.0,
        "relative_humidity_700hPa": 75.0,
        "wind_speed_925hPa": fetch * 0.9,
        "wind_direction_925hPa": 335.0,
        "wind_speed_850hPa": fetch,
        "wind_direction_850hPa": 335.0,
        "geopotential_height_500hPa": 5400 - t850 * 10,
        "pressure_msl_up": 1020.0,
        "temperature_850hPa_up": t850 + 1,
        "relative_humidity_850hPa_up": 86.0,
        "wind_speed_850hPa_up": fetch,
        "wind_direction_850hPa_up": 335.0,
        "pressure_msl_east": 1012.0,
    }
    return pd.DataFrame(d, index=idx)


def test_fit_predict_learns_fetch_snow_relation():
    df = _synthetic()
    m = YogoSnowModel().fit(df)
    pred = m.predict(df)
    assert {"p_snow", "snow_cm_h", "twb_2m"} <= set(pred.columns)
    assert (pred["snow_cm_h"] >= 0).all()

    # fetch強い日は弱い日より予測降雪が多いはず
    strong = df["wind_speed_850hPa"] > 14
    weak = df["wind_speed_850hPa"] < 4
    assert pred.loc[strong, "snow_cm_h"].mean() > pred.loc[weak, "snow_cm_h"].mean()


def test_elevation_correction_scales_snow():
    df = _synthetic()
    m = YogoSnowModel().fit(df)
    p_top = m.predict(df, elev_m=config.TOP_ELEV_M)["snow_cm_h"]
    p_base = m.predict(df, elev_m=config.BASE_ELEV_M)["snow_cm_h"]
    assert p_top.mean() >= p_base.mean()


def test_daily_summary_and_evaluate():
    df = _synthetic()
    m = YogoSnowModel().fit(df)
    pred = m.predict(df)
    daily = daily_summary(pred)
    assert len(daily) == 30
    metrics = evaluate(pred, df["snowfall"])
    for k in ["hourly_mae_cm", "season_total_pred_cm", "csi"]:
        assert k in metrics
    assert metrics["hourly_mae_cm"] >= 0


def test_save_load_roundtrip(tmp_path):
    df = _synthetic(n=500)
    m = YogoSnowModel().fit(df)
    p = tmp_path / "m.joblib"
    m.save(p)
    m2 = YogoSnowModel.load(p)
    pd.testing.assert_frame_equal(m.predict(df), m2.predict(df))
