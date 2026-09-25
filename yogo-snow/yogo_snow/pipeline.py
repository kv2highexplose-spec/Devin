"""学習・検証・予報のパイプライン。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, sources
from .features import fetch_index
from .model import YogoSnowModel, daily_summary, evaluate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


def winter_ranges(n_winters: int, end_year: int) -> list[tuple[str, str, str]]:
    """[(label, start, end)] — 11/1〜3/31 を1冬とする。"""
    out = []
    for y in range(end_year - n_winters + 1, end_year + 1):
        out.append((f"{y}-{str(y + 1)[2:]}", f"{y}-11-01", f"{y + 1}-03-31"))
    return out


def fetch_dataset(n_winters: int, end_year: int) -> dict[str, pd.DataFrame]:
    data = {}
    for label, start, end in winter_ranges(n_winters, end_year):
        print(f"[fetch] {label} ({start} .. {end})")
        data[label] = sources.fetch_training_frame(start, end)
    return data


@dataclass
class TrainResult:
    model: YogoSnowModel
    metrics: dict
    valid_label: str


def train(n_winters: int = 9, end_year: int = 2025) -> TrainResult:
    """直近n_winters冬を取得し、最後の冬を検証に残して学習。"""
    data = fetch_dataset(n_winters, end_year)
    labels = sorted(data.keys())
    valid_label = labels[-1]
    train_df = pd.concat([data[l] for l in labels[:-1]]).sort_index()
    valid_df = data[valid_label]

    model = YogoSnowModel()
    model.fit(train_df)

    pred = model.predict(valid_df)
    metrics = evaluate(pred, valid_df["snowfall"])
    metrics["valid_winter"] = valid_label
    metrics["train_winters"] = labels[:-1]
    metrics["train_hours"] = len(train_df)
    return TrainResult(model, metrics, valid_label)


def save_model(r: TrainResult, name: str = "yogo_snow") -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / f"{name}.joblib"
    r.model.save(path)
    path.with_suffix(".metrics.json").write_text(
        json.dumps(r.metrics, ensure_ascii=False, indent=2)
    )
    return path


DIRS16 = [
    "北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
    "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西",
]


def _dir16(deg: float) -> str:
    return DIRS16[int((deg + 11.25) // 22.5) % 16]


def explain_conditions(raw: pd.DataFrame, when: pd.Timestamp | None = None) -> list[str]:
    """ある時刻(デフォルト=最も雪が強い時間)の状況を日本語で要約。"""
    df = raw.apply(pd.to_numeric, errors="coerce").dropna(subset=["temperature_850hPa"])
    if when is None:
        when = df["snowfall"].idxmax() if "snowfall" in df else df.index[len(df) // 2]
    row = df.loc[when]
    t850, t500 = row["temperature_850hPa"], row["temperature_500hPa"]
    wd, ws = row["wind_direction_850hPa"], row["wind_speed_850hPa"]
    fi = fetch_index(pd.Series([ws]), pd.Series([wd])).iloc[0]
    grad = row["pressure_msl_up"] - row["pressure_msl_east"]

    cold = "平地でも雪になる強い寒気" if t850 <= -6 else "山地なら雪になる寒気" if t850 <= -3 else "寒気は弱め"
    fetch = "日本海から雪雲が流入しやすい" if fi >= 8 else "流入は弱め" if fi < 3 else "ある程度流入"
    pattern = "典型的な西高東低" if grad >= 5 else "気圧傾度は緩い"

    return [
        f"{when:%m/%d %H時}: 850hPa {t850:.0f}°C, 500hPa {t500:.0f}°C — {cold}",
        f"850hPa風 {_dir16(wd)} {ws:.0f}m/s (fetch指数{fi:.1f}) — {fetch}",
        f"日本海-太平洋 気圧差 {grad:.1f}hPa — {pattern}",
    ]


def snow_level(cm: float) -> str:
    if cm >= 40:
        return "豪雪"
    if cm >= 25:
        return "大雪"
    if cm >= 10:
        return "中雪"
    if cm >= 3:
        return "小雪"
    return "ほぼなし"


def forecast(
    model_path: str | Path,
    wx_model: str = "jma_msm",
    out_csv: Path | None = None,
    out_png: Path | None = None,
) -> dict:
    """予報モデルデータに学習済みモデルを適用し、3標高の日別降雪を返す。"""
    model = YogoSnowModel.load(model_path)
    raw = sources.fetch_forecast_frame(model=wx_model)

    res = {}
    for name, elev in [("麓540m", config.BASE_ELEV_M), ("中腹640m", config.MID_ELEV_M), ("山頂740m", config.TOP_ELEV_M)]:
        pred = model.predict(raw, elev_m=elev)
        res[name] = daily_summary(pred)

    hourly_mid = model.predict(raw, elev_m=config.MID_ELEV_M)
    table = res["中腹640m"].join(
        res["麓540m"]["snow_cm"].rename("snow_base"),
        rsuffix="_mid",
    ).join(res["山頂740m"]["snow_cm"].rename("snow_top"))

    if out_csv is None:
        out_csv = DATA_DIR / "forecast.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    hourly_mid.assign(
        raw_snowfall=raw["snowfall"], t850=raw["temperature_850hPa"]
    ).to_csv(out_csv)

    if out_png is not None:
        _plot(table, out_png)

    return {
        "daily": table,
        "raw_model_daily_cm": raw["snowfall"].groupby(raw.index.date).sum(),
        "explain": explain_conditions(
            raw, hourly_mid["snow_cm_h"].idxmax() if hourly_mid["snow_cm_h"].sum() > 0 else None
        ),
        "hours": len(hourly_mid),
        "wx_model": wx_model,
    }


def hindcast(
    model_path: str | Path,
    start: str,
    end: str,
    elev_m: int = config.MID_ELEV_M,
    out_png: Path | None = None,
) -> dict:
    """過去の解析値(JMA seamless)にモデルを適用し、実績との比較を返す。"""
    model = YogoSnowModel.load(model_path)
    raw = sources.fetch_training_frame(start, end)
    pred = model.predict(raw, elev_m=elev_m)
    daily = daily_summary(pred)
    actual = raw["snowfall"].astype(float).groupby(raw.index.date).sum()
    table = daily.join(actual.rename("actual_cm"))
    metrics = evaluate(pred, raw["snowfall"].astype(float))
    if out_png is not None:
        _plot_hindcast(table, out_png)
    return {"daily": table, "metrics": metrics, "hours": len(pred)}


def _plot(daily: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(daily))
    ax.bar(x, daily["snow_top"], 0.6, label="Summit 740m", color="#2f6fb3")
    ax.bar(x, daily["snow_base"], 0.6, label="Base 540m", color="#9ec7e8")
    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in daily.index], rotation=45, ha="right")
    ax.set_ylabel("Snowfall (cm/day)")
    ax.set_title("Yogo Kogen Resort YAP - daily snowfall forecast")
    ax.legend()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_hindcast(daily: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(daily))
    w = 0.4
    ax.bar(x - w / 2, daily["actual_cm"], w, label="JMA analysis (actual)", color="#444444")
    ax.bar(x + w / 2, daily["snow_cm"], w, label="Model hindcast 640m", color="#2f6fb3")
    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in daily.index], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Snowfall (cm/day)")
    ax.set_title("Yogo Kogen Resort YAP - hindcast vs analysis")
    ax.legend()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
