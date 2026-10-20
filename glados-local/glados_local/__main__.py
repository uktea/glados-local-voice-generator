import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import onnxruntime as ort
from .engine import Engine, ROOT
from .audio import Effects, analyze


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='完全ローカル GLaDOS風 WAV生成')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor')
    for name in ('say', 'batch'):
        p = commands.add_parser(name)
        p.add_argument('input', help='text (say) or UTF-8 text file (batch)')
        p.add_argument('--output', type=Path, required=True)
        p.add_argument('--language', choices=['en','ja'], default='en')
        p.add_argument('--device', choices=['auto','cpu','cuda'], default='auto')
        p.add_argument('--speed', type=float, default=1)
        p.add_argument('--pitch', type=float, default=0)
        p.add_argument('--formant', type=float, default=0)
        p.add_argument('--intonation', type=float, default=1)
        p.add_argument('--gain', type=float, default=0)
    p = commands.add_parser('analyze')
    p.add_argument('wav', type=Path)
    p.add_argument('--reference', type=Path)
    args = parser.parse_args()
    if args.command == 'doctor':
        smi = shutil.which('nvidia-smi')
        if not smi:
            candidate = Path('C:/Windows/System32/nvidia-smi.exe')
            smi = str(candidate) if candidate.exists() else None
        status = subprocess.run([smi], capture_output=True, text=True, timeout=15).stdout if smi else 'nvidia-smi not found; GPU presence is unconfirmed'
        print(json.dumps({'python': platform.python_version(), 'platform': platform.platform(),
            'onnxruntime': ort.__version__, 'available_providers': ort.get_available_providers(),
            'nvidia_smi': status, 'models_installed': (ROOT/'models/manifest.json').exists()}, indent=2))
        return
    if args.command == 'analyze':
        data = {'generated': analyze(args.wav)}
        if args.reference:
            data['reference'] = analyze(args.reference)
            data['duration_ratio'] = data['generated']['duration_seconds']/data['reference']['duration_seconds']
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    engine = Engine(args.device)
    options = dict(language=args.language, speed=args.speed,
                   effects=Effects(args.pitch, args.formant, args.intonation, args.gain))
    if args.command == 'say':
        print(json.dumps(engine.save(args.output, args.input, **options), ensure_ascii=False, indent=2))
    else:
        lines = [line.strip() for line in Path(args.input).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        if not lines:
            parser.error('台本が空です。')
        # Avoid overwriting previous batch output. Failed batches retain completed lines.
        args.output.mkdir(parents=True, exist_ok=False)
        rows = []
        for index, line in enumerate(lines, 1):
            path = args.output/f'{index:04d}.wav'
            rows.append(engine.save(path, line, **options))
            print(path, flush=True)
        (args.output/'manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
