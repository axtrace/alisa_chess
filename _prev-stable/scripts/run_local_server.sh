#!/bin/bash
set -ex
cd $(dirname $0)/..
virtualenv -p python3.7 .venv
source .venv/bin/activate
pip install -r requirements.txt
FLASK_APP=alice_flask_server.py python -m flask run --with-threads -p 5000
