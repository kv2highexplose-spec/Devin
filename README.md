# cospa-pc — 日本のPC・パーツ「今本当に買える」コスパ探索ツール

商品ページの現在価格を直接取得し、「本当にその価格で今買えるか」を重視した
スクレイピング＋コスパ分析＋ダッシュボード。

## 構成

```
run.py          — CLIエントリ (scrape / reparse / analyze / verify / serve / all)
cospa/
  models.py     — Listing / ScoredListing データモデル
  http.py       — requests フェッチャ (リトライ・エンコーディング)
  pwbrowser.py  — Playwright Chrome (JSレンダー店 & 購入ボタンDOM確認)
  specs.py      — 商品名から CPU/GPU/RAM/ストレージ/VRAM 抽出 + カテゴリ推定
  bench.py      — CPU/GPU ベンチスコア・TDP・VRAM・発売年 DB (~650 CPU / ~250 GPU)
  metrics.py    — コスパ指標 + log-log回帰による割安異常検出 + 値下げ検出
  verify.py     — 商品ページ再訪問: 価格/在庫/カートボタン実効性の再確認
  store.py      — data/shops/<shop>.json 保存 + history.jsonl 価格履歴
  scrapers/     — ショップ別スクレイパー (自動discover)
  dashboard/    — ゼロ依存サーバ + 単一HTML UI (散布図/ランキング/異常検出)
data/           — listings.json, analysis.json, shops/*.json, verify.json
```

## 使い方

```bash
python3 run.py scrape            # 全ショップ巡回
python3 run.py scrape dospara    # 一部のみ
python3 run.py reparse           # 商品名のスペック解析をやり直し + 解析
python3 run.py analyze           # スコア・異常検出 → data/analysis.json
python3 run.py verify 60         # 上位ディール60件を商品ページで再確認
python3 run.py serve             # http://localhost:8000 ダッシュボード
```

## データソース

| shop | 方式 | 備考 |
|---|---|---|
| dospara | requests (Salesforce Ajax) | 新品〜中古・ジャンク・アウトレット |
| tsukumo | requests | |
| iosys | requests | 中古専門 |
| frontier | requests | BTO + 中古 |
| sycom | requests | BTOモデル価格 |
| mouse | requests | G-TUNE等ブランドページ |
| sofmap | requests (Shift_JIS) | gid階層 |
| be-stock | requests (セッション必須) | 中古 |
| kakaku | requests (cp932) | aggregator層・要実店舗照合 |
| nttx | Playwright | NTT-X Store |
| janpara | Playwright | 中古 (レート制限あり) |
| pc-koubou | Playwright | 新品+中古・公式CPU/GPUスコア付 |
| amazon | Playwright (i18n-prefs=JPY) | 海外IP対策でJPYクッキー必須 |

## 解析指標

- 1万円あたりCPU性能 / GPU性能 (PassMark風スコア)
- AI/LLM用途: VRAMまたは統合メモリGBあたりの価格
- 省電力性能あたり価格 (score/TDP per 円)
- 割安検出: (カテゴリ×新品/中古) 群で価格~性能のlog-log回帰残差 z-score
- 値下げ検出: history.jsonl の過去最安値との比較
- 検証: 上位ディールを実際の商品ページで価格一致/在庫/カートボタン有効性を再確認

**注意**: 「カートに入れる」等のボタンはDOMの有効状態を読み取るのみで、
実際の注文・決済は一切行いません。

---

## Windows向け Everyday Tools

`windows_apps/` には、Python 3 標準ライブラリだけで動く4つのデスクトップツールがあります。
Windows 10/11 で Python 3（`py` ランチャーと Tkinter を含む）をインストール後、
`windows_apps/Start Everyday Tools.bat` をダブルクリックしてください。
またはリポジトリのルートから `py -3 -m windows_apps` で起動できます。

| ツール | 用途 |
|---|---|
| Rename files | ファイル名の検索・置換、接頭辞・接尾辞、連番をプレビューして一括改名 |
| Sort folder | 選択したフォルダ直下のファイルを種類別に分類 |
| Find duplicates | サブフォルダを含めて同一内容のファイルを検出し、CSVに出力（削除しない） |
| Text tools | 行の空白除去、空行除去、重複除去、並べ替え、空白圧縮とクリップボード操作 |

`py -3 -m windows_apps rename` のように `rename` / `sort` / `duplicates` /
`text` を指定すると対応ツールを開いた状態で起動します。ファイルを変更する
ツールは移動先をプレビューし、確認してから実行します。同じ画面で最後の操作を
元に戻せます（アプリを閉じると履歴は消えます）。移動先に同名ファイルがある場合は
処理を止めます。分類は選択したフォルダの直下だけが対象です。

開発時のロジックテスト: `python -m unittest discover -s tests`。
