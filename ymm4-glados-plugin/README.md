# YMM4 GLaDOS Local Voice プラグイン

YMM4の通常のボイスアイテムへ、GLaDOSの声質を追加します。字幕と発音を分け、YMM4のかな読み変換を利用します。日本語音声は英語モデルによる近似です。

## 前提

- `../glados-local`をセットアップ済みであること。
- .NET **10 SDK**。
- YMM4本体。検証対象はYMM4 Lite **4.56.1.0**です。

YMM4のPlugin/Controls DLLを参照してビルドします。本体DLLは同梱しません。別のYMM4バージョンではビルド・読込を再確認してください。

## ビルドと導入

このフォルダーからPowerShellで実行します。パスは自分の環境に置き換えてください。

```powershell
.\Build.ps1 `
  -YMM4DirPath 'C:\path\to\YukkuriMovieMaker_v4_Lite' `
  -PythonExe 'C:\path\to\glados-local\.venv\Scripts\python.exe' `
  -AppDirectory 'C:\path\to\glados-local'
```

`dist/GladosLocalVoice.dll`、`dist/glados-config.json`と、導入用の`GladosLocalVoice.ymme`を作成します。設定には指定したPython・アプリの絶対パスが入るため、生成済み設定をそのまま別PCへ配布しないでください。

`.ymme`をYMM4で導入するか、DLLと設定JSONをYMM4の`user/plugin/GladosLocalVoice/`へ配置してください。編集中のプロジェクトを保存してYMM4を再起動し、キャラクターの声質で次を選びます。

- **GLaDOS Local / GLaDOS English**: 英語。
- **GLaDOS Local / GLaDOS 日本語近似（試作）**: 日本語のかな変換を利用。

既存のボイスアイテムも声質を変更して再生成できます。発音欄が以前のエンジン用のままの場合は「発音を生成」も実行してください。

## 設定

`glados-config.json`の例:

```json
{
  "PythonExe": "C:\\path\\to\\glados-local\\.venv\\Scripts\\python.exe",
  "AppDirectory": "C:\\path\\to\\glados-local",
  "Device": "cpu",
  "TimeoutSeconds": 180
}
```

`Device`は`cpu`/`auto`/`cuda`。CPU版ONNX Runtimeのまま`cuda`を指定するとエラーになります。話速・ピッチ・包絡移動・抑揚・ゲインをボイス設定から調整できます。

`YMM4 → C#プラグイン → 常駐Pythonワーカー → WAV`の経路で動作します。GradioやHTTPサーバーは不要です。同時の生成要求は直列処理し、通信エラー後は次回要求でワーカーを起動し直します。

## 制約

字幕「私は花が好きです」に対する読み「わたしわ／はなが／すきです」はYMM4側で処理します。数字＋助数詞には未解決の例があるため、不自然な場合は発音欄をかなへ修正してください。アクセント指定・無声化・口パク用の音素時刻は完全再現しません。

YMM4の一時出力先が`.tmp`でもWAV形式で保存します。未対応の読みタグはエラーとし、発音欄の修正を案内します。

## 開発者向けホストテスト

`tests/HostSmoke`は対象YMM4の公開インターフェースを使った実WAV生成テストです。ビルド後、実行ディレクトリへ上記の`glados-config.json`を用意して実行します。

```powershell
dotnet build tests/HostSmoke -c Release '-p:YMM4DirPath=C:\path\to\YukkuriMovieMaker_v4_Lite'
dotnet tests/HostSmoke/bin/Release/net10.0-windows10.0.19041.0/HostSmoke.dll synthesize 'C:\path\to\YukkuriMovieMaker_v4_Lite' 'C:\path\to\test-output'
```

モデル・学習元音声の条件については[プロジェクトREADME](../README.md)と[第三者通知](../THIRD_PARTY_NOTICES.md)を参照してください。
