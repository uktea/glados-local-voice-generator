import os
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
os.environ['HF_HUB_OFFLINE'] = '1'
import json
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
import zipfile
import gradio as gr
from glados_local.engine import Engine, ROOT
from glados_local.pronunciation import DICT, preview, parse_dictionary
from glados_local.audio import Effects, analyze


@lru_cache(maxsize=3)
def engine(device):
    return Engine(device)


def conversion(text, lang, raw, batch=False):
    try:
        mapping = parse_dictionary(raw)
        if batch:
            return '\n'.join(preview(line, lang, mapping) for line in text.splitlines() if line.strip())
        return preview(text, lang, mapping)
    except Exception as exc:
        raise gr.Error(str(exc)) from exc


def save_dictionary(raw):
    mapping = parse_dictionary(raw)
    temp = DICT.with_suffix('.tmp')
    temp.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(DICT)
    return '辞書を保存しました。'


def generate(text, lang, raw, device, speed, pitch, formant, intonation, gain, batch):
    try:
        mapping = parse_dictionary(raw)
        lines = [x.strip() for x in text.splitlines() if x.strip()] if batch else [text]
        if not lines or len(lines) > 500:
            raise ValueError('1～500セリフを入力してください。')
        for line in lines:
            preview(line, lang, mapping)
        folder = ROOT/'generated'/uuid4().hex
        folder.mkdir(parents=True)
        files, rows = [], []
        tts = engine(device)
        for i, line in enumerate(lines, 1):
            file = folder/f'{i:04d}.wav'
            rows.append(tts.save(file, line, language=lang, dictionary=mapping, speed=speed,
                effects=Effects(pitch, formant, intonation, gain)))
            files.append(file)
        archive = folder/'batch.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for file in files:
                z.write(file, file.name)
                z.write(file.with_suffix('.json'), file.with_suffix('.json').name)
        return str(files[0]), [str(f) for f in files]+[str(archive)], rows
    except Exception as exc:
        raise gr.Error(str(exc)) from exc


def compare(wav, reference):
    if not wav:
        raise gr.Error('解析対象WAVを指定してください。')
    result = {'generated': analyze(wav)}
    if reference:
        result['reference'] = analyze(reference)
        result['duration_ratio'] = result['generated']['duration_seconds']/result['reference']['duration_seconds']
    return result


def build_app():
    with gr.Blocks(title='GLaDOS Local Voice Generator', analytics_enabled=False) as demo:
        gr.Markdown('# GLaDOS Local Voice Generator\nローカル音声生成MVP。日本語は英語モデルによる近似発音です。元サイトとの一致は未達です。')
        with gr.Row():
            with gr.Column():
                lang = gr.Radio(['en','ja'], value='en', label='入力言語')
                text = gr.Textbox(label='英語 / 日本語台本', lines=7, value='Hello, test subject. The experiment begins now.')
                batch = gr.Checkbox(label='改行ごとに別のWAVを生成', value=False)
                with gr.Accordion('発音辞書（JSON）', open=False):
                    raw = gr.Textbox(value=DICT.read_text(encoding='utf-8'), lines=8, label='表記 → 擬似スペル')
                    save = gr.Button('辞書を保存')
                    status = gr.Textbox(label='保存結果')
                preview_button = gr.Button('発音変換プレビュー')
                spelling = gr.Textbox(label='TTSに渡すスペル', interactive=False)
            with gr.Column():
                device = gr.Dropdown(['auto','cpu','cuda'], value='auto', label='実行先（autoはCPUへフォールバック）')
                speed = gr.Slider(.5, 2, value=1, step=.05, label='発話速度（倍率）')
                pitch = gr.Slider(-12, 12, value=0, step=.5, label='ピッチ（半音）')
                formant = gr.Slider(-6, 6, value=0, step=.5, label='スペクトル包絡の移動（半音相当）')
                intonation = gr.Slider(0, 2, value=1, step=.05, label='抑揚（0=平坦、1=原音）')
                gain = gr.Slider(-24, 12, value=0, step=1, label='ゲイン（dB・ピーク制限あり）')
                run = gr.Button('WAVを生成', variant='primary')
        audio = gr.Audio(label='再生（バッチ時は先頭）', type='filepath')
        files = gr.File(label='WAV・ZIPの保存', file_count='multiple')
        meta = gr.JSON(label='生成記録・実際の実行先')
        with gr.Accordion('WAV比較（同じ英文を使用）', open=False):
            wav = gr.File(label='生成WAV', file_types=['.wav'], type='filepath')
            ref = gr.File(label='比較用WAV', file_types=['.wav'], type='filepath')
            compare_button = gr.Button('F0・長さ・スペクトルを比較')
            metrics = gr.JSON(label='推定値（フォルマントF1/F2の測定ではありません）')
        preview_button.click(conversion, [text,lang,raw,batch], spelling)
        save.click(save_dictionary, raw, status)
        run.click(generate, [text,lang,raw,device,speed,pitch,formant,intonation,gain,batch], [audio,files,meta], concurrency_limit=1)
        compare_button.click(compare, [wav,ref], metrics)
    return demo


if __name__ == '__main__':
    build_app().queue().launch(server_name='127.0.0.1', share=False, inbrowser=True,
        theme=gr.themes.Base(font=['Arial'], font_mono=['Consolas']))
