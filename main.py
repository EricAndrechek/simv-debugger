from ucli import UCLI
from tui import SIMVApp
import sys
import os
import requests

VERSION = "v1.0.15"

def main(cmd):
    """Main function to run the UCLI and TUI together."""

    # first check if update is available via github releases
    # if so, prompt user to update
    # if user declines, continue as normal
    # if user accepts, download the new release and restart the program

    # check if --version is passed as an argument
    if "--version" in cmd or "-v" in cmd:
        print(f"Debugger version: {VERSION}")
        sys.exit(0)

    # check if --no-update is passed as an argument
    if "--no-update" in cmd:
        cmd = cmd.replace("--no-update", "")
    else:
        choice = False

        if "--update" in cmd or "--upgrade" in cmd or "-u" in cmd:
            # remove the flag from the command
            cmd = cmd.replace("--update", "").replace("--upgrade", "").replace("-u", "")
            choice = "y"
        
        # check for updates
        r = requests.get("https://api.github.com/repos/EricAndrechek/simv-debugger/releases/latest", timeout=5)
        latest = r.json()
        latest_version = latest["tag_name"]
        latest_url = latest["assets"][0]["browser_download_url"]

        if latest_version != VERSION:
            # check if they ran --update or --upgrade or -u
            if not choice:
                print(f"A new version of the debugger is available! ({latest_version}) (Current: {VERSION})")
                choice = input("Would you like to update? (y/n): ")

            if choice.lower() == "y":
                print("Downloading latest version...")

                # download the latest version
                r = requests.get(latest_url, timeout=30)
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
    
    # ensure cmd is a string and first element is the executable that exists
    if not isinstance(cmd, str):
        print("Command must be a string")
        sys.exit(1)
    if len(cmd.split()) == 0:
        print("Command must not be empty")
        sys.exit(1)
    if not os.path.exists(cmd.split()[0]):
        print(f"Executable {cmd.split()[0]} does not exist")
        sys.exit(1)

    print("Booting up simv simulation...")

    # add "-ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc" to the command
    cmd += " -ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc"

    try:
        ucli = UCLI(cmd)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

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
    
    if len(sys.argv) == 1 or sys.argv[1] == "--help" or sys.argv[1] == "-h":
        # print out command options
        print("Usage: ./debugger [command]")
        print("Example: ./debugger ./build/simv +MEMORY=programs/mem/test_1.mem +OUTPUT=output/test_1")
        sys.exit(1)

    main(cmd)
