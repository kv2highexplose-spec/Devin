"""CLI: train / forecast / evaluate。

  python3 run.py train                 # 直近9冬で学習+最新冬を検証
  python3 run.py forecast              # JMA MSM で今後の降雪予測
  python3 run.py forecast --wx jma_seamless --png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import pipeline

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _model_path(name: str) -> Path:
    return MODELS_DIR / f"{name}.joblib"


def cmd_train(args: argparse.Namespace) -> int:
    r = pipeline.train(n_winters=args.winters, end_year=args.end_year)
    path = pipeline.save_model(r, args.name)
    print(f"\n[model] {path}")
    print(f"[valid] {r.valid_label}冬")
    m = r.metrics
    print(json.dumps(m, ensure_ascii=False, indent=2))
    print(
        f"\n季節累積: 予測 {m['season_total_pred_cm']:.0f}cm / "
        f"実績(ERA5) {m['season_total_actual_cm']:.0f}cm — "
        f"降雪検出 POD {m['hit_rate_pod']:.2f}, CSI {m['csi']:.2f}"
    )
    return 0


def cmd_forecast(args: argparse.Namespace) -> int:
    model_path = _model_path(args.name)
    if not model_path.exists():
        print(f"モデルが無い: {model_path} — 先に `train` を実行してください")
        return 1

    png = DATA_DIR / "forecast.png" if args.png else None
    out = pipeline.forecast(
        model_path, wx_model=args.wx, out_png=png
    )
    print(f"[気象モデル] {out['wx_model']}  ({out['hours']}時間先まで)")
    print("\n=== 日別降雪予測 (cm) ===")
    daily = out["daily"]
    print(f"{'日付':<12}{'麓540m':>8}{'中腹640m':>8}{'山頂740m':>8}  目安")
    for d, row in daily.iterrows():
        print(
            f"{d!s:<12}{row['snow_base']:>8.1f}{row['snow_cm']:>8.1f}"
            f"{row['snow_top']:>8.1f}  {pipeline.snow_level(row['snow_cm'])}"
        )
    print("\n=== 気象モデル素の降雪量(cm/日, 比較用) ===")
    for d, v in out["raw_model_daily_cm"].items():
        print(f"{d!s:<12}{v:>6.1f}")

    print("\n=== ピーク時の大気状態 ===")
    for line in out["explain"]:
        print("・" + line)
    print(f"\n[出力] {DATA_DIR/'forecast.csv'}")
    if png:
        print(f"[出力] {png}")
    return 0


def cmd_hindcast(args: argparse.Namespace) -> int:
    model_path = _model_path(args.name)
    if not model_path.exists():
        print(f"モデルが無い: {model_path} — 先に `train` を実行してください")
        return 1
    png = DATA_DIR / "hindcast.png" if args.png else None
    out = pipeline.hindcast(model_path, args.start, args.end, out_png=png)
    m = out["metrics"]
    print(f"=== hindcast {args.start}..{args.end} ===")
    daily = out["daily"]
    print(f"{'日付':<12}{'解析(JMA)':>9}{'予測640m':>9}")
    for d, row in daily.iterrows():
        print(f"{d!s:<12}{row['actual_cm']:>9.1f}{row['snow_cm']:>9.1f}")
    print(
        f"\n期間累積: 予測 {m['season_total_pred_cm']:.0f}cm / "
        f"解析 {m['season_total_actual_cm']:.0f}cm  日別MAE {m['daily_mae_cm']:.2f}cm"
    )
    if png:
        print(f"[出力] {png}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    meta = _model_path(args.name).with_suffix(".metrics.json")
    if meta.exists():
        print(meta.read_text())
    else:
        print(f"指標ファイルなし: {meta}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="yogo-snow",
        description="余呉高原リゾート・ヤップ特化 降雪予測モデル",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train", help="JMA再解析の過去冬データで学習")
    t.add_argument("--winters", type=int, default=10)
    t.add_argument("--end-year", type=int, default=2025)
    t.add_argument("--name", default="yogo_snow")
    t.set_defaults(fn=cmd_train)

    f = sub.add_parser("forecast", help="気象予報モデル出力に適用")
    f.add_argument("--wx", default="jma_msm",
                   help="Open-Meteo予報モデル (jma_msm / jma_seamless / best_match)")
    f.add_argument("--name", default="yogo_snow")
    f.add_argument("--png", action="store_true", help="日別グラフPNGを保存")
    f.set_defaults(fn=cmd_forecast)

    h = sub.add_parser("hindcast", help="過去期間にモデルを適用して実績と比較")
    h.add_argument("--start", required=True, help="開始日 YYYY-MM-DD")
    h.add_argument("--end", required=True, help="終了日 YYYY-MM-DD")
    h.add_argument("--name", default="yogo_snow")
    h.add_argument("--png", action="store_true")
    h.set_defaults(fn=cmd_hindcast)

    e = sub.add_parser("evaluate", help="保存済み検証指標を表示")
    e.add_argument("--name", default="yogo_snow")
    e.set_defaults(fn=cmd_evaluate)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
