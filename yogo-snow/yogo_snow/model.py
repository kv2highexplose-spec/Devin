"""降雪量モデル。

ハードル型:
  P(降雪あり)    … HistGradientBoostingClassifier
  E[量|降雪あり] … HistGradientBoostingRegressor (poisson損失)
  予測 = 確率 × 条件付き期待量
に加えて、スキー場標高(540–740m)への地形性補正を掛ける。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)

from . import config
from .features import FEATURE_COLUMNS, build_features


@dataclass
class YogoSnowModel:
    clf: HistGradientBoostingClassifier = field(
        default_factory=lambda: HistGradientBoostingClassifier(
            max_depth=6, learning_rate=0.06, max_iter=400, random_state=0
        )
    )
    reg: HistGradientBoostingRegressor = field(
        default_factory=lambda: HistGradientBoostingRegressor(
            loss="poisson",
            max_depth=6,
            learning_rate=0.06,
            max_iter=400,
            random_state=0,
        )
    )
    feature_names: list[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))
    grid_elev_m: float = 553.0  # 学習した ERA5 格子の標高

    # ---------- 学習 ----------
    def fit(self, raw: pd.DataFrame) -> YogoSnowModel:
        X = build_features(raw)
        y_cm = pd.to_numeric(raw["snowfall"], errors="coerce").clip(lower=0.0)
        y_evt = (y_cm >= config.SNOW_EPS_CM).astype(int)

        ok = X.notna().all(axis=1) & y_cm.notna()
        X, y_cm, y_evt = X[ok], y_cm[ok], y_evt[ok]

        self.clf.fit(X, y_evt)
        snow = y_evt == 1
        self.reg.fit(X[snow], y_cm[snow])
        return self

    # ---------- 予測 ----------
    def predict(self, raw: pd.DataFrame, elev_m: float = config.MID_ELEV_M) -> pd.DataFrame:
        """各時刻の P(雪) と降雪量(cm/h)を返す。"""
        X = build_features(raw).ffill().bfill()
        p = self.clf.predict_proba(X)[:, 1]
        cm_cond = np.clip(self.reg.predict(X), 0.0, None)

        # 標高補正: 格子高度との差で地形性増減 + 湿球温度が高いほど減衰
        dz_100 = (elev_m - self.grid_elev_m) / 100.0
        oro = 1.0 + config.ORO_GAIN_PER_100M * dz_100
        twb = X["twb_2m"] + config.LAPSE_RATE_K_PER_M * (self.grid_elev_m - elev_m)
        melt = np.clip(1.0 - np.clip(twb, 0, None) / 2.0, 0.0, 1.0)

        out = pd.DataFrame(
            {
                "p_snow": p,
                "snow_cm_h": np.clip(p * cm_cond * oro * melt, 0.0, None),
                "twb_2m": twb,
            },
            index=raw.index,
        )
        return out

    # ---------- 保存/読込 ----------
    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "clf": self.clf,
                "reg": self.reg,
                "feature_names": self.feature_names,
                "grid_elev_m": self.grid_elev_m,
            },
            path,
        )
        meta = {"grid_elev_m": self.grid_elev_m, "features": self.feature_names}
        path.with_suffix(".meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)
        )

    @classmethod
    def load(cls, path: str | Path) -> YogoSnowModel:
        d = joblib.load(path)
        m = cls(clf=d["clf"], reg=d["reg"])
        m.feature_names = d["feature_names"]
        m.grid_elev_m = d["grid_elev_m"]
        return m


def daily_summary(pred: pd.DataFrame) -> pd.DataFrame:
    """時別予測 → JST日別集計(cm, 確率最大値, 降雪時間)。"""
    g = pred.groupby(pred.index.date)
    return pd.DataFrame(
        {
            "snow_cm": g["snow_cm_h"].sum(),
            "p_snow_max": g["p_snow"].max(),
            "snow_hours": g["snow_cm_h"].apply(lambda s: int((s >= config.SNOW_EPS_CM).sum())),
        }
    )


def evaluate(pred: pd.DataFrame, actual_cm: pd.Series) -> dict:
    """検証用指標。pred=predict結果, actual_cm=実績snowfall(cm/h)。"""
    y = actual_cm.clip(lower=0).reindex(pred.index).fillna(0.0)
    ph = pred["snow_cm_h"]
    ev_y = y >= config.SNOW_EPS_CM
    ev_p = ph >= config.SNOW_EPS_CM
    tp = int((ev_y & ev_p).sum())
    fp = int((~ev_y & ev_p).sum())
    fn = int((ev_y & ~ev_p).sum())

    daily = daily_summary(pred)
    y_daily = y.groupby(y.index.date).sum()

    return {
        "hours": len(pred),
        "hourly_mae_cm": float((ph - y).abs().mean()),
        "season_total_pred_cm": float(ph.sum()),
        "season_total_actual_cm": float(y.sum()),
        "daily_mae_cm": float((daily["snow_cm"] - y_daily).abs().mean()),
        "hit_rate_pod": tp / (tp + fn) if tp + fn else float("nan"),
        "false_alarm_far": fp / (tp + fp) if tp + fp else float("nan"),
        "csi": tp / (tp + fp + fn) if tp + fp + fn else float("nan"),
    }
