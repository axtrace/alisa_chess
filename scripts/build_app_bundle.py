#!/usr/bin/env python3
"""Build Cloud Functions ZIPs from an explicit list of runtime modules."""

import argparse
import hashlib
import re
import struct
import zipfile
from pathlib import Path

COMMON = (
    'game.py',
    'game_state.py',
    'skill_state.py',
    'move_extractor.py',
    'metrics.py',
    'position_query.py',
    'speaker.py',
)
SKILL = ('alice_serverless.py', 'alice_chess.py', 'logging_config.py', 'text_preparer.py', 'texts.py', 'tts_builder.py')


def build(engine, destination, include_skill=False, *, target=None):
    if target is None:
        target = 'testing' if include_skill else 'api-testing'
    if target not in ('testing', 'production', 'api-testing'):
        raise ValueError('Unknown function target')
    root = Path(__file__).resolve().parents[1]
    raw = engine.read_bytes()
    if raw[:6] != b'\x7fELF\x02\x01' or struct.unpack('<H', raw[18:20])[0] != 62:
        raise ValueError('Нужен ELF64 Linux x86-64')
    versions = [tuple(map(int, m.split(b'.'))) for m in re.findall(rb'GLIBC_([0-9]+\.[0-9]+)', raw)]
    if versions and max(versions) > (2, 35):
        raise ValueError('Бинарник требует GLIBC новее 2.35')
    files = [root / name for name in COMMON]
    if target != 'production':
        files.append(root / 'app_serverless.py')
        files.extend((root / 'shared_chess').glob('*.py'))
    # Общий сервис использует штатный диалог и при авторизованном вызове /v1/skill.
    files.extend(root / name for name in SKILL)
    for directory in ('handlers', 'request_validators'):
        files.extend((root / directory).glob('*.py'))
    if target == 'testing':
        files.append(root / 'shared_alice_serverless.py')
    if target == 'production':
        requirements = 'requirements.txt'
        license_file = engine.parent / 'copyright'
        source = 'Stockfish 14.1-1 (Ubuntu). https://launchpad.net/ubuntu/+source/stockfish/14.1-1\n'
    else:
        requirements = 'requirements-app.txt'
        license_file = engine.parent / 'Copying.txt'
        if not license_file.exists():
            license_file = engine.parent / 'COPYING'
        source = 'Stockfish 19. https://github.com/official-stockfish/Stockfish/tree/sf_19\n'

    def write(name, data, mode=0o100644):
        # Fixed timestamps, modes and order make the digest independent of checkout time.
        info = zipfile.ZipInfo(name)
        info.create_system = 3
        info.external_attr = mode << 16
        bundle.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w') as bundle:
        for path in sorted(files):
            write(path.relative_to(root).as_posix(), path.read_bytes())
        write('requirements.txt', (root / requirements).read_bytes())
        write('stockfish', raw, 0o100755)
        write('STOCKFISH_COPYING.txt', license_file.read_bytes())
        write('STOCKFISH_SOURCE.txt', source.encode())
    return hashlib.sha256(destination.read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stockfish', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=Path('prototype-data/cloud/app-testing.zip'))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--target', choices=('testing', 'production', 'api-testing'), default='api-testing')
    group.add_argument(
        '--include-skill', dest='target', action='store_const', const='testing', help='Alias for --target testing'
    )
    args = parser.parse_args()
    print(build(args.stockfish, args.output, target=args.target))
