#!/bin/bash

set -x

# check if --pull flag is passed
# flag check from:
# https://stackoverflow.com/a/2876177/7974356
if [[ $* == *--pull* ]]; then
    git pull
fi

source venv/bin/activate

# check if --pip flag is passed
if [[ $* == *--pip* ]]; then
    pip install -r requirements.txt
fi

# check if --clean flag is passed
if [[ $* == *--clean* ]]; then
    pyinstaller --onefile --name debugger --add-data "debugger.tcss:." --clean --collect-submodules textual.widgets --collect-all sentry_sdk main.py
else
    pyinstaller --onefile --name debugger --add-data "debugger.tcss:." --collect-submodules textual.widgets --collect-all sentry_sdk main.py
fi

cp dist/debugger .

# check if --push flag is passed
if [[ $* == *--push* ]]; then
    git add debugger
    git commit -m "Updated debugger"
    git push
fi
