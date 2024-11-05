#!/bin/bash

set -x

git pull

# python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# read input to ask if clean build --> store clean bool in variable clean
read -p "Do you want to clean the build folder? (y/n) " clean

# if clean is true, add --clean to the pyinstaller command
if [ $clean == "y" ]; then
    pyinstaller --onefile --name debugger --add-data "debugger.tcss:." --clean main.py
else
    pyinstaller --onefile --name debugger --add-data "debugger.tcss:." main.py
fi

cp dist/debugger .
git add debugger
git commit -m "Updated debugger"
git push
