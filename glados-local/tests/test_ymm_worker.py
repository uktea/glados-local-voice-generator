import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from scipy.io import wavfile
from glados_local.engine import ROOT
from glados_local.ymm_worker import normalize_ymm_reading


def test_ymm_reading_preserves_particles_already_converted_by_host():
    assert normalize_ymm_reading("ワタシワ/ハナガ/ス'キデス。") == 'ワタシワ ハナガ スキデス。'
    assert normalize_ymm_reading("ア_クセサリー;ス'キ+デス？") == 'アクセサリー スキデス？'
    with pytest.raises(ValueError):
        normalize_ymm_reading('<NUMK VAL=12>')


@pytest.mark.skipif(not (ROOT/'models/glados.onnx').exists(), reason='Models not installed')
def test_stdio_worker_survives_errors_and_reuses_engine(tmp_path):
    requests = [
        {'id':1,'command':'ping'},
        {'id':2,'text':'Hello, test subject.','output':str(tmp_path/'en.wav'), 'device':'cpu'},
        {'id':3,'text':'こんにちは。','language':'ja','output':str(tmp_path/'ja.wav'), 'device':'cpu'},
        {'id':4,'text':'Invalid','output':str(tmp_path/'invalid.wav'),'effects':{'pitch':99}},
        {'id':5,'command':'ping'},
        {'id':6,'text':'/わたしわ/はなが/すきです。','language':'ja','reading_format':'ymm_yukkuri_lite',
         'output':str(tmp_path/'host output.tmp'),'device':'cpu'},
        {'id':7,'text':'/げんざいの/せっていを/ふまえて、/ちょうせいばんを/せいせいしました。',
         'language':'ja','reading_format':'ymm_yukkuri_lite',
         'output':str(tmp_path/'long reading.tmp'),'device':'cpu'},
    ]
    proc = subprocess.run([sys.executable,'-m','glados_local.ymm_worker'],
        input='\n'.join(json.dumps(r) for r in requests)+'\n', capture_output=True,
        text=True, encoding='utf-8', timeout=90, cwd=ROOT,
        env={**os.environ,'PYTHONUTF8':'1'})
    assert proc.returncode == 0, proc.stderr
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [r['id'] for r in replies] == [1,2,3,4,5,6,7]
    assert [r['ok'] for r in replies] == [True,True,True,False,True,True,True]
    assert replies[0]['result']['engine_loaded'] is False
    assert replies[4]['result']['engine_loaded'] is True
    for name in ('en','ja'):
        rate, wave = wavfile.read(tmp_path/f'{name}.wav')
        assert rate==22050 and wave.size>1000
    assert not (tmp_path/'invalid.wav').exists()
    assert (tmp_path/'host output.tmp').read_bytes()[:4] == b'RIFF'
    host_meta = json.loads((tmp_path/'host output.json').read_text(encoding='utf-8'))
    assert host_meta['ymm_reading_input'] == '/わたしわ/はなが/すきです。'
    assert host_meta['text'] == 'わたしわ はなが すきです。'
    rate, wave = wavfile.read(tmp_path/'long reading.tmp')
    assert rate == 22050 and wave.size > rate
    assert replies[6]['result']['ymm_reading_input'] == requests[6]['text']
