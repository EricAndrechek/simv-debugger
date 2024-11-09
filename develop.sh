#!/bin/bash

# how to install python and development environment on caen

set -x

curl https://pyenv.run | bash

# Add multi line to .bashrc
echo 'export PYENV_ROOT="$HOME/.pyenv"\n[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init -)"\n\neval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

source ~/.bashrc

pyenv install 3.8.3
pyenv global 3.8.3

python3.8 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt