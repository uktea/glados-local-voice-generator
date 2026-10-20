"""The only model-network entrypoint. Inference never downloads anything."""
import argparse
import hashlib
import io
import json
import pickle
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMIT = '27b1ae489acc4404f9248a85361cdaf47d1b433f'
REPO = f'https://raw.githubusercontent.com/nimaid/GLaDOS-TTS/{COMMIT}/glados/models/'
RELEASE = 'https://github.com/dnhkng/GLaDOS/releases/download/0.1/'
ASSETS = {
    'glados.onnx': (RELEASE, '17ea16dd18e1bac343090b8589042b4052f1e5456d42cad8842a4f110de25095'),
    'phomenizer_en.onnx': (RELEASE, 'b64dbbeca8b350927a0b6ca5c4642e0230173034abd0b5bb72c07680d700c5a0'),
    'glados.onnx.json': (REPO, '01f5e602e1ec04daec6d54960e4d641b5de305f39186e40bf9b4a47bd757a489'),
    'idx_to_token.pkl': (REPO, '398c6fb9016d9ee380684c3b0f2ac6b10f959edc202e9a5fbd6be009bdfcdecb'),
    'token_to_idx.pkl': (REPO, '32b4f54ac2c662b4e6cd9e9dc77461ad08c27c531992ab38359c11375a154e43'),
    'lang_phoneme_dict.pkl': (REPO, '9250e3841742081397ef98765e75eecfa7b11d55520bad57a9e22eccb4d3152e'),
}


class DataOnlyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError('Only primitive dictionary data is permitted')


def setup(cache=None):
    target = ROOT/'models'
    target.mkdir(exist_ok=True)
    manifest = {}
    for name, (base, expected) in ASSETS.items():
        cached = Path(cache)/name if cache else None
        installed = target/name
        if cached and cached.exists():
            data = cached.read_bytes()
        elif installed.exists() and not name.endswith('.pkl'):
            data = installed.read_bytes()
        else:
            print('Downloading', name, flush=True)
            with urllib.request.urlopen(base+name, timeout=120) as response:
                data = response.read()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError(f'{name}: SHA256 mismatch (upstream may have replaced the asset)')
        outname = name
        if name.endswith('.pkl'):
            outname = name.removesuffix('.pkl')+'.json'
            data = json.dumps(DataOnlyUnpickler(io.BytesIO(data)).load(), ensure_ascii=False).encode('utf-8')
        dest = target/outname
        temp = dest.with_suffix(dest.suffix+'.part')
        temp.write_bytes(data)
        temp.replace(dest)
        manifest[outname] = {'source': base+name, 'source_sha256': digest,
                             'local_sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    (target/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Models ready:', target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, help='Optional local asset cache (original filenames)')
    setup(parser.parse_args().cache)
