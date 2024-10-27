from ucli import UCLI
from tui import SIMVApp
import sys

def main(cmd):
    """Main function to run the UCLI and TUI together."""

    # add "-ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc" to the command
    cmd += " -ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc"

    ucli = UCLI(cmd)
    ucli.start()

    app = SIMVApp(ucli)
    app.run()

if __name__ == "__main__":
    # take everything after the script name as the command
    # example command for running test_1 in project 3 / lab 4
    cmd = "./build/simv +MEMORY=programs/mem/test_1.mem +OUTPUT=output/test_1"

    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])

    main(cmd)
