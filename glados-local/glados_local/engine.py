import json
import re
import time
from dataclasses import asdict
from pathlib import Path
import numpy as np
from num2words import num2words
from .runtime import create_session
from .phonemizer import Phonemizer
from .pronunciation import preview
from .audio import Effects, process, save_wav

ROOT = Path(__file__).resolve().parents[1]


class Engine:
    def __init__(self, device='auto'):
        config_path = ROOT/'models/glados.onnx.json'
        if not config_path.exists() or not (ROOT/'models/glados.onnx').exists():
            raise FileNotFoundError('モデル未導入です。python setup_models.py を実行してください。')
        self.config = json.loads(config_path.read_text(encoding='utf-8'))
        self.rate = self.config['audio']['sample_rate']
        self.session, self.device = create_session(ROOT/'models/glados.onnx', device)
        self.phonemizer = Phonemizer()

    def synthesize(self, text, language='en', speed=1.0, effects=None, dictionary=None):
        if not np.isfinite(speed) or not .5 <= speed <= 2:
            raise ValueError('速度は0.5～2.0で指定してください。')
        effects = effects or Effects()
        effects.validate()
        spelling = preview(text, language, dictionary)
        normalized = re.sub(r'\d+(?:\.\d+)?', lambda m: num2words(m[0]), spelling)
        normalized = normalized.replace('%', ' percent ').replace('/', ' slash ')
        normalized = re.sub(r'\s+', ' ', normalized)
        # Bound model input per chunk. Batch files may contain arbitrarily many lines.
        pieces = re.split(r'(?<=[.!?])\s+', normalized)
        chunks = []
        for piece in pieces:
            current = ''
            for word in piece.split():
                if len(current)+len(word) > 180 and current:
                    chunks.append(current)
                    current = ''
                current += (' ' if current else '')+word
            if current:
                chunks.append(current)
        result, phonemes = [], []
        start = time.perf_counter()
        mapping = self.config['phoneme_id_map']
        for chunk in chunks:
            phon = self.phonemizer.convert_to_phonemes([chunk])[0]
            phonemes.append(phon)
            ids = list(mapping['^'])
            for symbol in phon:
                if symbol not in mapping:
                    raise ValueError(f'モデル未対応の音素: {symbol!r}')
                ids.extend(mapping[symbol])
                ids.extend(mapping['_'])
            ids.extend(mapping['$'])
            inputs = {'input': np.array([ids], dtype=np.int64),
                      'input_lengths': np.array([len(ids)], dtype=np.int64),
                      'scales': np.array([self.config['inference']['noise_scale'], 1/speed,
                                          self.config['inference']['noise_w']], dtype=np.float32)}
            if 'sid' in {i.name for i in self.session.get_inputs()}:
                inputs['sid'] = np.array([0], dtype=np.int64)
            try:
                audio = self.session.run(None, inputs)[0].reshape(-1)
            except Exception:
                if self.device != 'cuda':
                    raise
                self.session, self.device = create_session(ROOT/'models/glados.onnx', 'cpu')
                audio = self.session.run(None, inputs)[0].reshape(-1)
            result.extend([audio, np.zeros(round(self.rate*.12), dtype=np.float32)])
        if not result:
            raise ValueError('読み上げ可能なテキストがありません。')
        audio = process(np.concatenate(result[:-1]), self.rate, effects)
        metadata = {'text': text, 'language': language, 'pseudo_spelling': spelling,
                    'phonemes': phonemes, 'device': self.device,
                    'phonemizer_device': 'cpu', 'speed': speed, 'effects': asdict(effects),
                    'sample_rate': self.rate, 'duration_seconds': len(audio)/self.rate,
                    'generation_seconds': time.perf_counter()-start}
        return audio, metadata

    def save(self, path, text, **kwargs):
        path = Path(path)
        if path.suffix.lower() != '.wav':
            raise ValueError('出力拡張子は.wavが必要です。')
        audio, metadata = self.synthesize(text, **kwargs)
        path.parent.mkdir(parents=True, exist_ok=True)
        save_wav(path, audio, self.rate)
        path.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        return metadata
