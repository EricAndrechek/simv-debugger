from ucli import UCLI
from tui import SIMVApp
import sys
import os
import requests

VERSION = "v0.1.0"

def main(cmd):
    """Main function to run the UCLI and TUI together."""

    # first check if update is available via github releases
    # if so, prompt user to update
    # if user declines, continue as normal
    # if user accepts, download the new release and restart the program

    # check for updates
    r = requests.get("https://api.github.com/repos/EricAndrechek/simv-debugger/releases/latest")
    latest = r.json()
    latest_version = latest["tag_name"]
    latest_url = latest["assets"][0]["browser_download_url"]

    if latest_version != VERSION:
        print("Update available! Downloading latest version...")

        # download the latest version
        r = requests.get(latest_url)
        with open("debugger_new", "wb") as f:
            f.write(r.content)
        
        # move the new version to the correct location
        # can't overwrite the current script, so we need to move it to a temp location
        os.system("mv debugger_new debugger")
        os.system("chmod +x debugger")
        os.system("./debugger " + cmd)
        sys.exit(0)

    print("Booting up simv simulation...")

    # add "-ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc" to the command
    cmd += " -ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc"

    ucli = UCLI(cmd)

    print("Simulation booted.")
    print("Starting simulation...")

    ucli.start()

    print("Simulation started.")
    print("Launching UI...")

    app = SIMVApp(ucli)
    app.run()

    print("UI closed.")
    del app
    print("UI cleaned up.")

    print("Shutting down simulation...")
    ucli.close()
    del ucli
    print("Simulation shut down.")

    print("Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    # take everything after the script name as the command
    # example command for running test_1 in project 3 / lab 4
    cmd = "./build/simv +MEMORY=programs/mem/test_1.mem +OUTPUT=output/test_1"

    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])

    main(cmd)
