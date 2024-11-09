# SIMV DEBUGGER

A TUI (terminal user interface) debugger for Synopsys VCS simulator. Made for UMich EECS470 course by the Speculative Dispatchers team.

## Installation

Since this is to be used on UM CAEN computers, there are some project dependencies that need to be installed in order to develop. If you want to try developing this application, make changes, or test local builds, see the [Development](#development) section. 

Otherwise, to just use the debugger, you can install a pre-built binary by running the following command (or download and run the binary from the [releases](https://github.com/EricAndrechek/simv-debugger/releases/latest) page instead of piping to bash...):

```bash
curl https://github.com/EricAndrechek/simv-debugger/raw/main/install.sh | bash
```

## Usage

```bash
# Run the debugger
./debugger --help

# Run the debugger with a simv executable
./debugger ./path/to/simv

# Run the debugger with a simv executable and custom arguments (like memory or output file)
./debugger ./path/to/simv +MEMORY=programs/mem/test_1.mem +OUTPUT=output/test_1.out
```

## Development

Clone the repo locally (like to CAEN) and either run the `develop.sh` script, or run the following commands to set up python:

```bash
curl https://pyenv.run | bash

# Add the following to your shell profile (e.g. ~/.bashrc, ~/.zshrc, etc.)
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"

# Restart your shell or run the following command
source ~/.bashrc

# Install the required Python version
pyenv install 3.8.3
pyenv global 3.8.3

# Set up the virtual environment
python3.8 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required Python packages
pip install -r requirements.txt
```
