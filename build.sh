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

# textual-web path
tw_path=~/.local/bin/textual-web

echo "textual-web path: $tw_path"

# check if --clean flag is passed
if [[ $* == *--clean* ]]; then
    pyinstaller --onefile --name debugger --add-data "debugger.tcss:." --add-data "*.toml:." --collect-submodules textual.widgets --collect-all sentry_sdk --collect-all textual-web --add-binary "$tw_path:." --clean main.py
else
    pyinstaller --onefile --name debugger --add-data "debugger.tcss:." --add-data "*.toml:." --collect-submodules textual.widgets --collect-all sentry_sdk --collect-all textual-web --add-binary "$tw_path:." main.py
fi

cp dist/debugger .

# check if --push flag is passed
if [[ $* == *--push* ]]; then
    git add debugger
    git commit -m "Updated debugger"
    git push
fi
