import subprocess
import shlex
import select
import time
import threading

BUSY_WAIT_TIME = 0.001

class UCLI():
    def __init__(self, cmd):
        self.proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        self.poll_obj = select.poll()
        self.poll_obj.register(self.proc.stdout, select.POLLIN)

        # when run is called add it to the queue of commands to be run
        # the loop automatically handles running commands in the order they were added,
        # and will move the command string to the running command variable when popped from the command queue
        # when the next values are read in, the command string will be the key to the output dictionary
        # this allows for easy access to the output of the command without worrying about "consuming" the output
        # and ensures that identical commands always give the latest output

        self.commands = []
        self.running_command = None
        self.output = {}

        self.EOF = False
        self.waitingForPrompt = False

        self.thread = None
        self.stop = False

    def start(self):
        """Initialize the simulation and start the UCLI loop, blocking until ready"""

        # run the loop in a separate thread
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.run("run -delta")
        self.run("run -event clock_count")

        # block until all commands are finished, then clear output
        while self.commands or self.running_command:
            time.sleep(BUSY_WAIT_TIME)
        self.output.clear()

    # -------------------- public methods --------------------

    def run(self, cmd):
        """Run a custom command in the UCLI"""

        self.commands.append(cmd)

        # if there is no command currently running, just run it now
        if self.waitingForPrompt:
            self._run()

    def read(self, command, blocking=False, run=False):
        """
        Read the output of a command,
        optionally blocking until the output is available.
        If the run flag is set, this function calls run first.
        """

        if run:
            self.run(command)

        if blocking:
            while command not in self.output:
                time.sleep(BUSY_WAIT_TIME)

        # this will remove the command from the output dictionary
        # do we want this behavior to allow blocking, or
        # should we allow "caching" of the output for repeated access?
        return self.output.pop(command)

    def get_clock(self):
        """Special function to get the clock cycle and parse it instead of relying on get_var"""

        self.run("get clock_count")
        cc = self.read("get clock_count", blocking=True)[0]
        cc = cc.split("'b")[1]
        return int(cc, 2)

    def get_time(self):
        """Special function to get the simulation time and parse it instead of relying on get_var"""

        tm = self.read("senv time", blocking=True, run=True)
        return tm[0]

    def list_vars(self):
        """List all variables found in the Verilog code currently being simulated"""
        return self.read("show", blocking=True, run=True)

    def get_var(self, var):
        """Get the value of a variable in the Verilog code currently being simulated"""
        return self.read(f"get {var}", blocking=True, run=True)[0]

    def clock_cycle(self, cycles, blocking=False):
        """Run the simulation for a number of clock cycles"""

        if cycles <= 0:
            # not implemented yet...
            return self.get_clock()

        # TODO: need a way to incrementally read values and clock cycles between runs

        # TODO: can't possibly be the best way to do this...
        # get the current clock cycle
        cc = self.get_clock()
        # run the simulation for the specified number of cycles
        for _ in range(cycles):
            self.run("run -event clock_count")

        if blocking:
            # block until all commands are finished, which should be whatever was before
            # this function call plus the number of cycles since we just added them all
            # and (assuming no other threads) no one else can add any until we're done
            while self.commands or self.running_command:
                time.sleep(BUSY_WAIT_TIME)

        # get the new clock cycle
        cc_new = self.get_clock()
        return cc_new

    # TODO: add a way to run the simulation for a certain amount of time

    # TODO: add checkpoints (or something else?) to go backwards in time

    # TODO: run gdb commands with cbug::gdb gdb-cmd

    # TODO: add breakpoints

    # TODO: add support for changing variables

    # -------------------- private methods --------------------

    def _run(self):
        if self.commands:
            cmd = self.commands.pop(0)
            self.running_command = cmd
            self.proc.stdin.write((cmd + "\n").encode())
            self.proc.stdin.flush()
            self.waitingForPrompt = False
            return True
        # if no incoming commands, do nothing and just wait for the prompt
        return False

    def _loop(self):
        command_output = []
        line = ""

        while True:
            c = self.proc.stdout.read(1)
            if c == b"":
                self.EOF = True
                break
            elif c == b"\n":
                command_output.append(line)
                line = ""
            else:
                line += c.decode()

            if "ucli% " in line:
                # grab the command string and use it as the key for the output dictionary
                if self.running_command:
                    self.output[self.running_command] = command_output
                    self.running_command = None
                else:
                    self.output["undefined"] = command_output

                command_output = []
                line = ""

                if self.stop:
                    self.run("exit")
                    break
                else:
                    ran_cmd = self._run()
                    if not ran_cmd:
                        self.waitingForPrompt = True

        # gracefully close the process and cleanup
        self.close()

    def close(self):
        self.stop = True
        self.proc.kill()
        self.proc.wait()

        # self.thread.join()

    def __del__(self):
        self.close()
