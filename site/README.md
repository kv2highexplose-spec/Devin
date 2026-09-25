# MIDI Pocket

Android向けオフラインMIDI + SoundFontプレイヤー。1000曲規模の生成MIDIライブラリを
同梱し、曲をタップして即試聴・SoundFontをワンタップで切り替えられる。
最終形はCapacitor製APKとして完全オフラインで動作する。

## 構成

```
site/
  index.html            アプリシェル（一覧・検索・フィルタ・プレイヤーシート・SFシート）
  js/app.js             UI + プレイヤー制御 (spessasynth WorkletSynthesizer + Sequencer)
  js/db.js              IndexedDBラッパー (userMidi / userFonts / recents)
  css/app.css           スマホ片手操作優先のダークUI
  vendor/spessasynth/   spessasynth_lib v4.3.14 (Apache-2.0) + worklet — 完全ローカル
  library/
    catalog.json        {version,count,seed,genres,parts} — 分割catalogの入口
    catalog/part-*.json 各100曲のtrackエントリ (id,title,file,genre,mood,bpm,tags,
                        durationSec,sizeBytes,recommendedSoundfonts)
    midi/               生成MIDI 1008ファイル (GM/GS互換, タイプ1)
    soundfonts/         fonts.json + SF2/SF3 4本 (再配布可能なもののみ)
  sw.js                 PWA用サービスワーカー (ネイティブAPK内では自動無効化)
  manifest.webmanifest  PWAマニフェスト
app/                    Capacitor 7 Androidプロジェクト (webDir=../site)
tools/
  genmidi.py            MIDI量産ジェネレータ (12ジャンル×84曲, seed固定で再現可)
  midilib.py            genmidi用のヘルパー (SMF組立・パース共用)
  mksf2.py              Chip Pocket用SF2をプロシージャル生成するRIFFライタ
tests/
  test_library.py       catalog整合 / 全MIDIパース / 無音・長さ / Program・Bank・ドラム /
                        重複・近似重複 / SoundFontメタデータ (15件)
  test_e2e_web.py       headless Chrome + CDPの最小E2E (5件)
docs/soundfonts.md      SoundFont調査マトリクス (同梱4本+除外候補と理由)
```

## Web版として使う

```bash
cd site && python3 -m http.server 8000
# http://localhost:8000 — Android Chrome / デスクトップブラウザで開く
```

依存は一切なし。`vendor/spessasynth` だけで完結するためネットワーク不要。

## APKビルド

前提: JDK **21** (Temurin推奨), Android SDK, Node 20。

```bash
cd app
npm install                 # @capacitor/{core,cli,android}@7
npx cap sync android        # site/ -> android assets にコピー
cd android
JAVA_HOME=/path/to/jdk-21 ./gradlew assembleDebug
# 出力: app/android/app/build/outputs/apk/debug/app-debug.apk (~59MB)
```

`adb install -r app-debug.apk` でインストール。署名・リリースビルドは
`./gradlew assembleRelease` (+ `key.properties` で署名設定)。

### 既知の注意点

- Maven Central が 429 を返す環境では `~/.gradle/init.d/` に
  `https://maven-central.storage-download.googleapis.com/maven2/` を
  pluginManagement / buildscript / allprojects の先頭に指すinitスクリプトを置く。
- WebView内ではServiceWorkerが古いアセットを掴み続けるため、ネイティブでは
  `navigator.serviceWorker.unregister()` を起動時に呼んでいる (app.js末尾)。

## 挙動 (エミュレータ実測: sdk_gphone64_x86_64 / Android 14)

- インストール→起動→catalog 1009曲表示: 動作する
- 機内モードで全機能 (一覧/検索/フィルタ/再生/SF切替/インポート) が動作する
- フォアグラウンド再生: AAudio 48kHz、声部数~150 (非無音を実測)
- HOMEでバックグラウンド: **再生継続** (mediaPlaybackフォアグ���ウンドサービス+
  PARTIAL_WAKE_LOCK + MediaSession playbackState を実装)
- 画面OFF: エミュレータではWebViewのオクルージョンにより音声出力が止まる
  (実機ではOSの音声HALがwakelockを保持するため継続する機種が多い。
  上記サービスで最大限の対策は済み — 実機での確認推奨)
- 30MB級SoundFontの切替: ~250ms、初回タップ→音声開始 ~1s (冷起動含む ~8s)
- メモリ: フォント8連続切替後 ~142MB PSS (GC範囲、リークなし)

## データ追加

### MIDIを追加

1. アプリ右上の「＋」→ ファイルピッカーから `.mid/.midi/.smf` を選択
2. IndexedDB (`userMidi` store) に保存され、一覧の先頭ジャンル「マイMIDI」に出る
3. catalogへの永続登録は行わない (ユーザー追加データとして分離)

### 生成MIDIを差し替え・増量

```bash
pip install mido
python3 tools/genmidi.py            # seed固定で site/library 全体を再生成
python3 tools/genmidi.py --seed 42 --count 120  # 別バリエーション
```

生成後は `python3 -m pytest tests/test_library.py` で整合性を確認。

### SoundFontを追加

1. プレイヤーシート → SoundFont行の「変更」→「＋ SF2 / SF3 / DLS を追加」
2. IndexedDB (`userFonts`) に保存・選択可能になる
3. アプリ同梱にしたい場合は `site/library/soundfonts/` にファイルを置き、
   `fonts.json` にエントリを追加:

```json
{
  "id": "myfont",
  "name": "My Font",
  "file": "myfont.sf2",
  "license": "…",
  "sourceUrl": "https://…",
  "sizeMB": 12.3,
  "tags": ["gm"],
  "notes": "…",
  "redistributionAllowed": true
}
```

ライセンス/再配布可否が不明なものは同梱しないこと (`docs/soundfonts.md` 参照)。

## テスト

```bash
pip install mido pytest websocket-client sf2utils
python3 -m pytest tests/            # 20件: ライブラリ15 + E2E5
python3 -m pytest tests/test_e2e_web.py   # E2Eのみ (Chrome必須)
```

## 既知の制約

- ドラムチャンネルのSF差し替えは未対応 (GMドラムキットを既定で使う)
- Web版でSWが古いアセットを掴むことがある → ハードリロードで解消
- `.dls` ファイルは対応宣言済みだが検証はSF2/SF3のみ
