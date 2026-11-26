#!/usr/bin/env bash
# GitHub-hosted Ubuntu runner. This step has no cloud credentials.
set -euo pipefail
target=$1
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
case "$target" in
  testing|api-testing)
    url=https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-linux-x86-64-universal.tar.gz
    sha=9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f
    ;;
  production)
    url=https://mirror.yandex.ru/ubuntu/pool/universe/s/stockfish/stockfish_14.1-1_amd64.deb
    sha=d232c613e94320740ee9e046a252a583a498818d7431a47ec65712258786adef
    ;;
  *) exit 2 ;;
esac
curl --fail --silent --show-error --location --retry 3 "$url" -o "$work/engine"
echo "$sha  $work/engine" | sha256sum --check
if [[ "$target" == production ]]; then
  dpkg-deb -x "$work/engine" "$work/deb"
  cp "$work/deb/usr/games/stockfish" "$work/stockfish"
  cp "$work/deb/usr/share/doc/stockfish/copyright" "$work/copyright"
  engine="$work/stockfish"
  entrypoint=alice_serverless
else
  tar -xzf "$work/engine" -C "$work" stockfish/stockfish-linux-x86-64-universal stockfish/Copying.txt
  engine="$work/stockfish/stockfish-linux-x86-64-universal"
  entrypoint=app_serverless
  if [[ "$target" == testing ]]; then entrypoint=shared_alice_serverless; fi
fi
python scripts/build_app_bundle.py --target "$target" --stockfish "$engine" --output dist/function.zip
(cd dist && sha256sum function.zip > function.sha256)
# Test imports and a real UCI move with only the files/dependencies shipped to this function.
unzip -q dist/function.zip -d "$work/app"
python -m venv "$work/venv"
cd "$work/app"
"$work/venv/bin/python" -m pip install -q -r requirements.txt
"$work/venv/bin/python" - "$entrypoint" <<'PY'
import importlib
import sys

from game import Game

assert callable(importlib.import_module(sys.argv[1]).handler)
with Game() as game:
    assert game.comp_move()
PY
