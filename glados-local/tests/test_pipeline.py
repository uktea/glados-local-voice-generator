import json
import socket
import pickle
import io
import re
from pathlib import Path
import numpy as np
import pytest
from scipy.io import wavfile
from glados_local.audio import Effects, process, analyze, save_wav
from glados_local.pronunciation import parse_dictionary, preview, split_long_pseudo_words
from glados_local.engine import Engine, ROOT
from glados_local.runtime import create_session
from setup_models import DataOnlyUnpickler


def test_dictionary_longest_match():
    assert preview('実験開始。', 'ja', {'実験':'experiment','実験開始':'begin test'}) == 'begin test .'
    assert preview('Hello', 'ja', {}) == 'Hello'
    with pytest.raises(ValueError):
        parse_dictionary('{"": "abc"}')
    with pytest.raises(ValueError):
        preview('日本語', 'en')


def test_long_japanese_pseudo_spelling_is_bounded_without_losing_letters():
    # Actual YMM4 failure: this 24-letter spelling cannot fit the model's 64 slots.
    converted = preview('せいせいしました。', 'ja', {})
    assert converted.replace(' ', '') == 'seheeseheesheemahsheetah.'
    assert len(converted.split()) > 2
    assert split_long_pseudo_words('kah' * 10) == 'kah' * 6 + ' ' + 'kah' * 4
    for text in ('せいせいしました', 'おはようございます', 'あ' * 60):
        converted = preview(text, 'ja', {})
        assert all(len(w) <= 20 for w in re.findall(r'[a-zA-Z]+', converted))
    for word in ('seheeseheesheemahsheetah', 'a' * 47, 'z' * 43):
        parts = split_long_pseudo_words(word).split()
        assert ''.join(parts) == word
        assert all(len(part) <= 20 for part in parts)
    assert preview('登録語', 'ja', {'登録語':'z' * 43}).replace(' ', '') == 'z' * 43
    assert split_long_pseudo_words('short, hello!') == 'short, hello!'


@pytest.mark.parametrize('opening,closing', [('"','"'),("'","'"),('“','”'),('‘','’'),('′','′'),('″','″'),('「','」'),('『','』')])
def test_quote_variants_in_preview_and_batch(opening, closing):
    from app import conversion
    wrapped = opening + '実験' + closing + 'を開始します。'
    assert preview(wrapped, 'ja', {}) == preview('実験 を開始します。', 'ja', {})
    assert preview(opening + 'Hello' + closing + ' world', 'en') == 'Hello world'
    batch = wrapped + '\n' + opening + 'こんにちは' + closing
    assert conversion(batch, 'ja', '{}', True) == '\n'.join(preview(line, 'ja', {}) for line in batch.splitlines())


def test_quote_normalization_keeps_contractions_and_rejects_empty_speech():
    assert preview('“Don’t panic.” It′s GLaDOS’s experiment.', 'en') == "Don't panic. It's GLaDOS's experiment."
    with pytest.raises(ValueError, match='引用符以外'):
        preview('“”′\"', 'ja')


def test_gui_batch_preview_matches_per_line_conversion():
    from app import conversion
    text = 'こんにちは。\n実験。'
    raw = '{"こんにちは": "hello", "実験": "test"}'
    assert conversion(text, 'ja', raw, True) == 'hello .\ntest .'


def test_data_only_pickle():
    assert DataOnlyUnpickler(io.BytesIO(pickle.dumps({'a':[1]}))).load() == {'a':[1]}
    with pytest.raises(pickle.UnpicklingError):
        DataOnlyUnpickler(io.BytesIO(pickle.dumps(Path('x')))).load()


def test_effects_and_pitch(tmp_path):
    rate = 22050
    times = np.arange(rate*2)/rate
    wave = sum(.12/k*np.sin(2*np.pi*180*k*times) for k in range(1, 9))
    assert np.allclose(process(wave, rate, Effects()), wave, atol=1e-7)
    processed = process(wave, rate, Effects(pitch=12))
    a, b = tmp_path/'a.wav', tmp_path/'b.wav'
    save_wav(a, wave, rate)
    save_wav(b, processed, rate)
    assert 1.8 < analyze(b)['f0_median_hz']/analyze(a)['f0_median_hz'] < 2.2
    assert np.max(np.abs(processed)) <= .98
    with pytest.raises(ValueError):
        process(wave, rate, Effects(pitch=float('nan')))


def test_auto_fallback(monkeypatch):
    import glados_local.runtime as runtime
    monkeypatch.setattr(runtime.ort, 'get_available_providers', lambda: ['CPUExecutionProvider'])
    monkeypatch.setattr(runtime.ort, 'InferenceSession', lambda *a, **kw: kw['providers'])
    with pytest.warns(UserWarning):
        session, device = create_session('unused', 'auto')
    assert session == ['CPUExecutionProvider'] and device == 'cpu'
    with pytest.raises(RuntimeError):
        create_session('unused', 'cuda')


@pytest.mark.skipif(not (ROOT/'models/glados.onnx').exists(), reason='Download models first')
def test_real_offline_english_japanese_and_unknown_word(tmp_path, monkeypatch):
    # Deliberately deny outbound sockets after imports. Models and dictionaries must be local.
    def blocked(*a, **k):
        raise AssertionError('Network access during synthesis')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    tts = Engine('cpu')
    for lang, text in [('en', 'Hello, test subject. Quorvex.'), ('ja', 'こんにちは。実験を開始します。'),
                       ('en', '“Hello,” she said. Don’t panic. ′Test subject′.'),
                       ('ja', '「実験」、“テスト”、\'開始\'、′準備′。')]:
        out = tmp_path/f'{lang}.wav'
        meta = tts.save(out, text, language=lang)
        rate, data = wavfile.read(out)
        assert rate == 22050 and data.dtype == np.int16 and len(data) > rate*.5
        assert np.sqrt(np.mean(data.astype(float)**2)) > 10
        assert meta['device'] == 'cpu'
        assert json.loads(out.with_suffix('.json').read_text(encoding='utf-8'))['text'] == text
        if lang == 'en' and 'Don’t' in text:
            # The shipped dictionary stores contractions with apostrophes removed.
            assert tts.phonemizer.phoneme_dict['dont'] in ''.join(meta['phonemes'])
