from ucli import UCLI
from tui import SIMVApp

def main():
    # example command for testing in project 3
    cmd = "./build/simv +MEMORY=programs/mem/test_1.mem +OUTPUT=output/test_1 -ucli -suppress=ASLR_DETECTED_INFO"

    ucli = UCLI(cmd)
    ucli.start()

    app = SIMVApp()
    app.run()

if __name__ == "__main__":
    main()