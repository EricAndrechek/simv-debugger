#!/bin/bash

set -x

# get the latest release from github
url=$(curl -s https://api.github.com/repos/EricAndrechek/simv-debugger/releases/latest | grep "browser_download_url" | cut -d '"' -f 4)

# download the latest release
curl -L $url -o debugger

# make the debugger executable
chmod +x debugger

