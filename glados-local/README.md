# Local voice app

セットアップ・CLI・制約は[リポジトリのREADME](../README.md)を参照してください。

Windows 11 / 64bit Python 3.12を対象にしています。`Setup.cmd`で環境・モデルを導入し、`Start.cmd`で起動します。モデルを導入した後の音声生成はローカルで完結します。

`pronunciation.json`は日本語の表記からASCII擬似スペルへの辞書です。GUIからも編集・保存できます。例:

```json
{"こんにちは": "kohn nee chee wah", "テスト": "teh soo toh"}
```

加工値の範囲は、話速0.5〜2.0倍、ピッチ±12半音、スペクトル包絡移動±6半音相当、抑揚0〜2、ゲイン−24〜12dBです。YMM4標準側の速度・音程調整と併用すると効果が重なります。

モデル取得は`setup_models.py`でのみ行います。上流URLとSHA256を照合し、辞書pickleはクラス参照を禁止してJSONへ変換します。実行時にはpickleを読み込みません。

`requirements-lock.txt`は開発時の依存関係一覧です。通常は`requirements.txt`、開発・テストには`requirements-dev.txt`を使用します。

[調査報告](docs/RESEARCH.md) / [検証範囲](docs/VALIDATION.md)
