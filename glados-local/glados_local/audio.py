from dataclasses import dataclass, asdict
import numpy as np
import pyworld as pw
from scipy.io import wavfile


@dataclass
class Effects:
    pitch: float = 0.0
    formant: float = 0.0
    intonation: float = 1.0
    gain: float = 0.0

    def validate(self):
        for name, lo, hi in [('pitch', -12, 12), ('formant', -6, 6), ('intonation', 0, 2), ('gain', -24, 12)]:
            value = getattr(self, name)
            if not np.isfinite(value) or not lo <= value <= hi:
                raise ValueError(f'{name}: {lo}～{hi} の範囲が必要です。')


def world_features(audio, rate):
    x = np.ascontiguousarray(audio, dtype=np.float64)
    f0, times = pw.harvest(x, rate, f0_floor=65, f0_ceil=600, frame_period=5)
    f0 = pw.stonemask(x, f0, times, rate)
    return f0, pw.cheaptrick(x, f0, times, rate), pw.d4c(x, f0, times, rate)


def process(audio, rate, settings):
    settings.validate()
    x = np.asarray(audio, dtype=np.float64).reshape(-1)
    if not x.size or not np.isfinite(x).all():
        raise ValueError('空または非有限の音声です。')
    if settings.pitch or settings.formant or settings.intonation != 1:
        f0, spectral, ap = world_features(x, rate)
        voiced = f0 > 0
        if voiced.any():
            logf = np.log2(f0[voiced])
            center = np.median(logf)
            f0[voiced] = 2 ** (center + (logf-center)*settings.intonation + settings.pitch/12)
        if settings.formant:
            bins = np.arange(spectral.shape[1])
            source = bins / 2**(settings.formant/12)
            spectral = np.stack([np.interp(source, bins, row) for row in spectral])
        x = pw.synthesize(f0, spectral, ap, rate, 5.0)
    x *= 10**(settings.gain/20)
    peak = float(np.max(np.abs(x)))
    # Apply headroom only when necessary; do not normalize away gain controls.
    if peak > 0.98:
        x *= 0.98 / peak
    return x.astype(np.float32)


def save_wav(path, audio, rate):
    wavfile.write(str(path), rate, np.round(np.clip(audio, -1, 1)*32767).astype(np.int16))


def analyze(path):
    rate, raw = wavfile.read(str(path))
    if raw.dtype.kind in 'iu':
        if raw.dtype.kind == 'u':
            audio = (raw.astype(float)-128) / 128
        else:
            audio = raw.astype(float) / (-np.iinfo(raw.dtype).min)
    else:
        audio = raw.astype(float)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if rate < 16000 or len(audio) < rate*.1 or not np.isfinite(audio).all():
        raise ValueError('解析には16kHz以上、0.1秒以上の有限なWAVが必要です。')
    f0, spectral, _ = world_features(audio, rate)
    voiced = f0[f0 > 0]
    bins = np.linspace(0, rate/2, spectral.shape[1])
    return {
        'sample_rate': rate, 'duration_seconds': len(audio)/rate,
        'rms_dbfs': float(20*np.log10(max(np.sqrt(np.mean(audio**2)), 1e-12))),
        'peak': float(np.max(np.abs(audio))), 'voiced_fraction': float(np.mean(f0 > 0)),
        'f0_median_hz': float(np.median(voiced)) if voiced.size else None,
        'f0_p10_p90_hz': np.percentile(voiced, [10, 90]).tolist() if voiced.size else None,
        'spectral_centroid_hz': float(np.mean((spectral @ bins)/np.maximum(spectral.sum(axis=1), 1e-12))),
        'note': 'F0は推定値。centroidはスペクトル指標でありF1/F2フォルマント測定ではありません。発話速度の比較は同一テキストで実施。',
    }
