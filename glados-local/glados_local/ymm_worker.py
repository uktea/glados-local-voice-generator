"""YMM4 bridge: newline-delimited JSON over stdio, with no network listener."""
import contextlib
import json
import sys
from pathlib import Path
import re


def normalize_ymm_reading(text):
    # YMM owns kanji/particle conversion. Remove only accent/phrase notation.
    # Unsupported numeric/other tags must not be silently pronounced as English.
    if '<' in text or '>' in text:
        raise ValueError('未対応の読みタグがあります。YMM4の発音欄をかなで修正してください。')
    # Pitch reset (;) and devoicing (_) have no equivalent in this English model.
    # Keep a phrase boundary for ;, but never feed these control symbols as words.
    return re.sub(r"[’'`+_]", '', text).replace('/', ' ').replace(';', ' ').strip()


def run(stream_in=None, stream_out=None):
    stream_in = stream_in or sys.stdin
    stream_out = stream_out or sys.stdout
    engine = None
    active_device = None
    for line in stream_in:
        request_id = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError('Request must be an object')
            request_id = request.get('id')
            command = request.get('command', 'synthesize')
            if command == 'ping':
                result = {'protocol': 1, 'engine_loaded': engine is not None}
            elif command == 'synthesize':
                text = request.get('text')
                if not isinstance(text, str) or not text.strip():
                    raise ValueError('text is required')
                reading_input = text
                reading_format = request.get('reading_format', 'text')
                if reading_format == 'ymm_yukkuri_lite':
                    text = normalize_ymm_reading(text)
                elif reading_format != 'text':
                    raise ValueError('Unsupported reading format')
                output = request.get('output')
                if not isinstance(output, str) or not Path(output).is_absolute():
                    raise ValueError('output must be an absolute WAV path')
                device = request.get('device', 'auto')
                if device not in ('auto', 'cpu', 'cuda'):
                    raise ValueError('Invalid device')
                from .audio import Effects, save_wav
                from .pronunciation import preview
                effects = Effects(**request.get('effects', {}))
                effects.validate()
                language = request.get('language', 'en')
                preview(text, language)
                # Keep non-protocol output out of stdout even if a dependency prints.
                with contextlib.redirect_stdout(sys.stderr):
                    if engine is None or active_device != device:
                        from .engine import Engine
                        engine = Engine(device)
                        active_device = device
                    audio, result = engine.synthesize(text, language=language,
                                         speed=request.get('speed', 1.0), effects=effects)
                    # YMM supplies a temporary filename (often .tmp), not necessarily .wav.
                    # The file content must be PCM WAV irrespective of its extension.
                    Path(output).parent.mkdir(parents=True, exist_ok=True)
                    save_wav(Path(output), audio, engine.rate)
                    result['ymm_reading_input'] = reading_input
                    result['reading_format'] = reading_format
                    Path(output).with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            else:
                raise ValueError(f'Unknown command: {command}')
            response = {'id': request_id, 'ok': True, 'result': result}
        except Exception as exc:
            response = {'id': request_id, 'ok': False,
                        'error': f'{type(exc).__name__}: {exc}'}
        stream_out.write(json.dumps(response, ensure_ascii=False, allow_nan=False)+'\n')
        stream_out.flush()


if __name__ == '__main__':
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    run()
