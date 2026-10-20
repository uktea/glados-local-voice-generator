# 調査・実現可能性報告

調査日: 2026-10-19（日本時間）。公開ソースの実装と取得したWAVを確認しました。

## 結論

完全ローカルのGLaDOS風英語音声生成は実現可能で、今回CPU推論による実WAV生成を確認しました。元サイトとの完全一致は、現行TTS音声・加工設定が不明なため保証できません。英語モデルに日本語の擬似スペルを入力する方式は試作可能ですが、日本語の自然さと明瞭さは別途改善が必要です。

## 調査対象の固定点

| 対象 | 調査したcommit | 役割・所見 |
|---|---|---|
| [EtiennePerot/gladosvoicegen](https://github.com/EtiennePerot/gladosvoicegen) | `5dc6f72de850b2afab2a530ecce3b27e95fc25e3` | 合成済みWAVのMelodyne GUI加工。TTS本体は収録されていない |
| [nimaid/GLaDOS-TTS](https://github.com/nimaid/GLaDOS-TTS) | `27b1ae489acc4404f9248a85361cdaf47d1b433f` | ONNXの音素予測＋VITS音声合成。MVPに採用 |
| [R2D2FISH/glados-tts](https://github.com/R2D2FISH/glados-tts) | `1f49d17cd40960d600ec16752a10c07cb8ca5ba5` | Forward Tacotron＋HiFiGAN。今回の推論には未採用 |

全リポジトリを作業用領域に取得し、READMEだけでなく推論コードとファイル配置を確認しました。古いGUI操作コードや同梱taskkill.exeは実行していません。

## 旧版: 確認できた処理

[README](https://github.com/EtiennePerot/gladosvoicegen/blob/5dc6f72de850b2afab2a530ecce3b27e95fc25e3/README.md)と[glados.py](https://github.com/EtiennePerot/gladosvoicegen/blob/5dc6f72de850b2afab2a530ecce3b27e95fc25e3/glados.py)から、Windows XP・Python 2・Melodyne 3.2・固定画面テーマ/色深度への依存が分かります。処理順は次の通りです。

1. `Z:\files` 内の `.glados.wav` を開く。
2. 全選択してピッチ補正ダイアログを開き、画像一致に基づく座標をクリック。
3. Pitch Modulationツールに切替え、選択音符の画像差分を探索してダブルクリック。
4. Formantツールに切替え、表示欄へ数値100を入力。
5. 44,100 HzのWAV書き出しを選び、`ok-*.done.wav` として保存。

このコードからピッチ補正・モジュレーション・フォルマント操作の存在は確認できます。ただし、座標クリックを厳密なDSPパラメータへ換算したものではありません。「100」を100 Hz、100半音などと決めつける根拠はなく、MVPの初期設定に転用していません。Melodyneのアルゴリズム自体も公開コードにありません。

旧TTSエンジン/音声名は、このリポジトリには記載が見つかりませんでした。特定の商用TTSやMicrosoft音声だったという説は、今回確認した一次資料から確定できません。忠実な旧構成の復元には元のTTS入力WAVとMelodyneの設定・実行環境が追加で必要です。

## 現行サイトとの差

[現行公開ページ](https://glados.c-net.org/)は、旧プロジェクトを基に、精度改善・異なるTTS音声への対応・インフラ適応を行ったと説明しています。入力上限256文字、`/generate?text=...` のAPI、生成待ちと再試行、サイト生成サンプルのWTFPLも記載されています。

現行TTSの製品名・音声名・処理の全構成・現行Melodyneの利用有無・数値設定は、このページから確定できません。「現行サイトも旧コードと同一設定」「ONNXモデルが現行サイトの内部モデル」という扱いはしていません。取得した比較WAVは44,100 Hzで、22,050 Hzの採用モデル出力とはサンプルレートも異なりました。レートを揃えても、それだけで音色や帯域は一致しません。

## 代替モデルの採用理由と障害

nimaidの[tts.py](https://github.com/nimaid/GLaDOS-TTS/blob/27b1ae489acc4404f9248a85361cdaf47d1b433f/glados/tts.py)はVITS/Piper形式の入力ID・length/noise scaleをONNXへ渡します。[phonemizer.py](https://github.com/nimaid/GLaDOS-TTS/blob/27b1ae489acc4404f9248a85361cdaf47d1b433f/glados/phonemizer.py)の実体は辞書とONNXによる英語音素予測で、コメント内のespeak説明と実装は区別しました。今回の経路にespeakの外部インストールは不要です。上流の[取得スクリプト](https://github.com/nimaid/GLaDOS-TTS/blob/27b1ae489acc4404f9248a85361cdaf47d1b433f/download_models_linux.bash)と同じreleaseから2モデルを取得し、実際にロードできました。

R2D2FISHの[README](https://github.com/R2D2FISH/glados-tts/blob/1f49d17cd40960d600ec16752a10c07cb8ca5ba5/README.md)はLJSpeechとゲーム由来の音声による学習を説明しています。調査した[glados.py](https://github.com/R2D2FISH/glados-tts/blob/1f49d17cd40960d600ec16752a10c07cb8ca5ba5/glados.py)は `models/glados-new.pt` を要求しますが、取得したtreeにあったのは `glados.pt` です。両者を同じものと断定してファイル名だけ変更することは避けました。PyTorchの古い依存指定、NLTKの実行時ダウンロード、CPU/GPUの配置もWindows/オフライン用の修正対象になります。

MVPではONNX方式を採用し、未知語の長さによる音素モデル入力切り捨てを検出してエラー化、複数チャンクの音声結合を一次元で処理、通常起動時のネット取得を排除しました。辞書データはJSON化し、音声デバイス用ライブラリを必須にせずWAV保存とブラウザー再生を使用しています。

## 音声の比較

比較文: `Hello, test subject. The experiment begins now.`

サイトAPIは最初503を返しましたが、時間を置いた再試行でRIFF/WAVEを取得できました。比較元音声は公開リポジトリへ同梱しません。解析値は [comparison.json](comparison.json) にあります。

| 指標 | 元サイト | 無加工ローカル | 初期合わせ候補 |
|---|---:|---:|---:|
| 長さ（秒） | 3.901 | 3.475 | 3.745 |
| 有声F0中央値（Hz、推定） | 180.66 | 155.44 | 178.34 |
| 有声F0 10–90%（Hz） | 146.12–207.00 | 132.18–192.04 | 141.40–225.18 |
| RMS（dBFS） | −21.30 | −13.21 | −21.27 |
| スペクトル重心（Hz） | 1882.14 | 1316.62 | 1320.28 |

候補設定はspeed=0.8909、pitch=+2.6半音、gain=−8.1 dB、formant=0、intonation=1です。F0中央値と音量の数値は近づきましたが、抑揚幅・スペクトルは一致せず、主観的忠実度の改善を確認したものではありません。モデルのランダム性もあるため毎回完全同値にはなりません。

WORLDのF0推定はロボット声や倍音で誤ることがあり、フォルマントF1/F2の追跡、音素位置合わせ、無音を除いた発話速度、複数文での聴感評価は未実装/未検証です。スペクトル重心をフォルマント測定と呼んでいません。

## ライセンスで確認した範囲

| 対象 | 確認結果 | MVPでの扱い |
|---|---|---|
| EtiennePerot公開tree | 調査時に独立したLICENSEファイルを確認できず | 加工手順を調査。コード/実行ファイルを製品へ転用しない |
| [nimaid LICENSE](https://github.com/nimaid/GLaDOS-TTS/blob/27b1ae489acc4404f9248a85361cdaf47d1b433f/LICENSE.txt) | MIT、David Ngの著作権通知 | 改変した音素処理コードとMIT全文通知を同梱 |
| [R2D2FISH LICENSE](https://github.com/R2D2FISH/glados-tts/blob/1f49d17cd40960d600ec16752a10c07cb8ca5ba5/LICENSE) | MIT、Timmy Knightの著作権通知 | 今回コード・重みを製品へ同梱しない |
| [dnhkng release 0.1](https://github.com/dnhkng/GLaDOS/releases/tag/0.1) の重み | 採用2モデルの個別モデルカード・学習音声権利・生成物許諾を今回確定できず | ユーザーのPCへ上流から取得。ソースZIPから除外し、再配布条件確定とはしない |
| 元サイト生成WAV | 公開ページにWTFPLの記載 | 比較資料。ローカルモデル出力へ条件を流用しない |

この表は確認した公開記載の整理です。コードのMITが学習元音声や重み・キャラクター等のすべての権利を保証する、という判断はしていません。

## 次の開発段階

GPUの追加診断ではnvidia-smi実行に成功し、572.83 / CUDA上限12.8 / VRAM 6144 MiBを確認しました。[ONNX Runtimeの公式資料](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)では1.27以降の既定GPUパッケージはCUDA 13です。このPCで最新GPUパッケージを無条件導入できるとは推測せず、CUDA 12向けパッケージの選択・DLLとドライバーの適合を次段階の障害として扱います。

1. NVIDIA用環境で実CUDA推論、ドライバー/DLLの整合、VRAM、長時間バッチを検証。
2. 同一テキストを複数用意し、元サイト/無加工/候補をレベル合わせして聴感比較。
3. 音素位置合わせ、F0曲線、F1/F2追跡を追加し、WORLDの倍/半周波数エラーも監視。
4. 日本語を読み・モーラ・音素列へ明示的に分解し、擬似スペルと英語G2Pの実出力を対応付け。現状のローマ字ベース試作から改善。
5. 元サイトの現行TTSが公開される場合は別バックエンドとして実装し、比較して採否を決める。
