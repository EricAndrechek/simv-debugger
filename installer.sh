#!/bin/bash

set -x

curl https://pyenv.run | bash

# Add multi line to .bashrc
echo 'export PYENV_ROOT="$HOME/.pyenv"\n[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init -)"\n\neval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

source ~/.bashrc

pyenv install 3.8.3
pyenv global 3.8.3

git clone https://github.com/EricAndrechek/simv-debugger.git

cd simv-debugger

# this assumes you have a requirements.txt file in the same directory as this script
pip3.8 install -r requirements.txt

# make executable for running in parent directory
