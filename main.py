from ucli import UCLI
from tui import SIMVApp
import sys
import os
import requests

VERSION = "v1.0.7"

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
        print(f"A new version of the debugger is available! ({latest_version}) (Current: {VERSION})")
        print("Would you like to update? (y/n)")

        choice = input()

        if choice.lower() != "y":
            print("Downloading latest version...")

            # download the latest version
            r = requests.get(latest_url)
            with open("debugger_new", "wb") as f:
                f.write(r.content)

            # make a new file to
            # wait for the python process to close
            # delete this version of the program (debugger executable)
            # move the new version to the current version
            # restart the program
            # deleting itself

            lines = []
            lines.append("#!/bin/bash") # shebang
            lines.append(f"sleep 1") # wait for the python process to close
            lines.append(f"rm {sys.argv[0]}") # delete this version of the program
            lines.append(f"mv debugger_new {sys.argv[0]}") # move the new version to the current version
            lines.append(f"echo 'New version installed. Run the debugger again to start.'") # restart the program
            lines.append(f"rm .updater.sh")

            with open(".updater.sh", "w") as f:
                f.write("\n".join(lines))

            os.system("chmod +x .updater.sh")
            os.system("./.updater.sh &")

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
