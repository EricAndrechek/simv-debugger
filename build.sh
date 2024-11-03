#!/bin/bash

set -x

python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pyinstaller --onefile --name debugger --add-data "debugger.tcss:." main.py