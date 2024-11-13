#!/bin/bash

set -x

# get the latest release from github
url=$(curl -s https://api.github.com/repos/EricAndrechek/simv-debugger/releases/latest | grep "browser_download_url" | cut -d '"' -f 4)

echo "Downloading the latest release from $url"

# download the latest release
curl -L $url -o debugger

echo "Download complete"

# make the debugger executable
chmod +x debugger

echo "Debugger is now executable and ready to use with the ./debugger command"

