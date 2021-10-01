#!/bin/bash
set -ex
cd $(dirname $0)/..
mkdir -p target

if [ ! -f ./target/stockfish ]; then
    echo "Download stockfish binary"
    cd target
    wget http://mirror.yandex.ru/ubuntu/pool/universe/s/stockfish/stockfish_8-3_amd64.deb
    ar -x stockfish_8-3_amd64.deb
    tar -xvf data.tar.xz
    chmod +x ./usr/games/stockfish
    cp ./usr/games/stockfish ./stockfish
fi

cd $(dirname $0)/..
rm -f ./target/chess.zip
zip -Dj target/chess.zip alice_serverless.py alice_chess.py texts.py game.py move_extractor.py speaker.py text_preparer.py target/stockfish requirements.txt
