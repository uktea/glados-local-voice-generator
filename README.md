# GLaDOS Local Voice Generator

Windows 11向けのローカル音声生成アプリと、YMM4の通常のボイスアイテムから利用する音声合成プラグインです。

英語GLaDOSモデルをONNX Runtimeで実行し、WAVを生成します。日本語は読みを英語向けの擬似スペルに変換する実験的な対応です。**元サイトや本物の音声との完全一致、日本語ネイティブの発音品質には達していません。**

## 機能

- Gradioによる英語・日本語入力、発音プレビュー、WAV再生・保存。
- 1行1セリフのWAV一括生成とZIP保存。
- 話速、ピッチ、スペクトル包絡、抑揚、ゲインの調整。
- 編集可能な日本語→擬似スペル辞書。
- CPU推論、利用可能な場合のCUDA選択、CPUフォールバック。
- YMM4の声質として登録し、字幕と発音を分けて編集。
- セットアップ後の音声生成はオフライン。Gradioはlocalhostのみで待ち受けます。

## セットアップ

64bit Python **3.12**を用意し、`glados-local/Setup.cmd`を実行してください。初回は依存関係とモデルをダウンロードします。`pyworld`のビルドでC++コンパイラーを求められた場合は、Visual Studio Build ToolsのC++ビルド環境が必要です。

PowerShellの場合:

```powershell
cd glados-local
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_models.py
.\.venv\Scripts\python.exe app.py
```

次回からは`glados-local/Start.cmd`で起動します。Web画面は通常 <http://127.0.0.1:7860/> です。利用中のポートがある場合はGradioの起動ログを確認してください。

モデル重み・学習辞書データ・生成音声・YMM4本体DLL・個人用設定は同梱していません。モデル取得先とSHA256は`setup_models.py`に固定し、実行時の自動取得は行いません。

## CLI

`glados-local/`内から:

```powershell
.\.venv\Scripts\python.exe -m glados_local doctor
.\.venv\Scripts\python.exe -m glados_local say "Hello, test subject." --device cpu --output generated\hello.wav
.\.venv\Scripts\python.exe -m glados_local say "こんにちは。" --language ja --device cpu --output generated\ja.wav
.\.venv\Scripts\python.exe -m glados_local batch samples\script-ja.txt --language ja --output generated\batch01
```

台本はUTF-8、空行を除いた1行が1セリフです。CLIのバッチ出力先には新しいフォルダーを指定します。各WAVと同名のJSONへ、元の入力・実際の音素・生成設定を記録します。

## YMM4プラグイン

音声アプリをセットアップしてから、[プラグインのビルド・導入手順](ymm4-glados-plugin/README.md)に従ってください。検証対象はYMM4 Lite **4.56.1.0** / .NET **10**です。Gradioを起動せず、専用Pythonワーカーとの標準入出力通信で動作します。

日本語版はYMM4の読み変換を利用するため、助詞「は→わ」「へ→え」と字幕を分離できます。ただし数値・助数詞の読み変換には既知の問題があります。

## 制約と調整

- 日本語の漢字読み・数字・助数詞・アクセント・促音・長音は不完全です。発音プレビューと生成情報を確認し、必要に応じてかなや辞書で調整してください。
- YMM4で`COUNTER`が文字として混ざる例を確認しています。「二三人」は発音欄を`にさんにん`にするなど、読みをかなへ修正してください。自動修正は未実装です。
- YMM4のアクセント記号や無声化指定、音素単位の正確な口パク情報は再現しません。未対応の読みタグはエラーになります。
- 長い日本語の擬似スペルは発音モデルの長さ制限に合わせて自動分割します。英語の長い未知語には入力長チェックがあります。
- `"`・`'`・`“ ”`・`‘ ’`・`′`・`″`・`「 」`・`『 』`などを整理して生成します。英語の単語内アポストロフィーは保持します。
- スペクトル包絡の移動はフォルマント加工の近似です。スペクトル重心をF1/F2の実測値として扱いません。
- CPUでの実推論は確認済み。**CUDA実機推論は未検証**です。既定の依存関係はCPU版ONNX Runtimeで、GPU版を使う場合は対応するCUDA/cuDNN/ドライバーを別途確認してください。
- モデルの確率的推論により、同一設定でも音声が完全一致するとは限りません。

## テスト

```powershell
cd glados-local
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp .test-tmp
```

モデル導入済み環境で18件のテストを確認しています。モデルがない場合、実音声生成を伴う2件はskipされます。[検証範囲](glados-local/docs/VALIDATION.md)、[元サイト・公開コードの調査](glados-local/docs/RESEARCH.md)も参照してください。

## 配布条件とクレジット

このリポジトリ全体に対する追加のライセンスは、現時点では指定していません。第三者由来部分の通知は[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)と同梱のMIT全文を参照してください。

コードの許諾と、モデル重み・学習元音声・生成音声・キャラクターの権利は別です。モデルの再配布・商用利用条件がすべて確認済みという意味ではありません。本リポジトリは非公式の実験的プロジェクトです。
