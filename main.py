from ucli import UCLI
from tui import SIMVApp
import sys
import os

def main(cmd):
    """Main function to run the UCLI and TUI together."""

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
