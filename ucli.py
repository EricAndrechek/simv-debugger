import subprocess
import shlex
import select
import time
import threading
import click
import sentry_sdk

sentry_sdk.init(
    dsn="https://c15cc5692675ac611b7bb01f8eee2d87@o4506596663427072.ingest.us.sentry.io/4508288337903616",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

BUSY_WAIT_TIME = 0.001

def convert_time(time_str):
    """Convert a time string to an integer in ps"""
    time, base = time_str.split(" ")
    time = int(time)
    if base == "fs":
        # TODO: don't support this for now
        time = 0
    if base == "ps":
        time *= 1
    elif base == "ns":
        time *= 10**3
    elif base == "us":
        time *= 10**6
    elif base == "ms":
        time *= 10**9
    elif base == "s":
        time *= 10**12
    else:
        click.secho(f"Unknown time base: {base}", fg="red")
        time = 0

    return time

def convert_time_to_str(time_int):
    """Take a time in ps and convert it to a string"""
    # if time_int == 0:
    #     return "0 ps"
    # if time_int % 10**12 == 0:
    #     return f"{time_int // 10**12} s"
    # if time_int % 10**9 == 0:
    #     return f"{time_int // 10**9} ms"
    # if time_int % 10**6 == 0:
    #     return f"{time_int // 10**6} us"
    # if time_int % 10**3 == 0:
    #     return f"{time_int // 10**3} ns"
    # TODO: seems like run command doesn't want a space?
    return f"{time_int}ps"

class UCLI():
    def __init__(self, cmd, verbose=False):
        self.cmd = cmd
        self.verbose = verbose
        self.proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        self.poll_obj = select.poll()
        self.poll_obj.register(self.proc.stdout, select.POLLIN)

        # when run is called add it to the queue of commands to be run
        # the loop automatically handles running commands in the order they were added,
        # and will move the command string to the running command variable when popped from the command queue
        # when the next values are read in, the command string will be the key to the output dictionary
        # this allows for easy access to the output of the command without worrying about "consuming" the output
        # and ensures that identical commands always give the latest output

        self.clock_name = ""
        self.clock_speed = 0 # ps

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

        # check that the command ran and didn't immediately exit
        if self.proc.poll() is not None:
            raise FileNotFoundError(f"Executable {self.cmd.split()[0]} does not exist or exited immediately")

        # initialize the simulation
        self.run("config -autocheckpoint on")
        # precheckpoint seems to default to run, step, next
        # we are (at least for now?) only allowing run as checkpoints
        self.run("config -precheckpoint -remove synopsys::step")
        self.run("config -precheckpoint -remove synopsys::next")
        self.run("run -delta")

        # now find the name of the clock
        # TODO: should this use list_vars instead to recursively search for the clock?
        # this is a bit of a hack, but it seems to work
        variables = self.read("show", blocking=True, run=True)
        for var in variables:
            if "clock" in var or "clk" in var:
                self.clock_name = var
                break
        # handle the case where no clock is found
        if not self.clock_name:
            raise ValueError("Could not find clock variable")

        # TODO: would it be better to read the makefile and find the clock speed there?
        # now find the speed of the clock
        self.read(f"run -change {self.clock_name}", blocking=True, run=True)
        try:
            time_returned = self.read("senv time", blocking=True, run=True)[0]
        except IndexError:
            raise ValueError("Could not find clock speed")
        # now parse out the " ps" and convert to an integer
        self.clock_speed = convert_time(time_returned) * 2 # the clock is half the speed of the time returned

        # go back one checkpoint
        self.run("checkpoint -join 2")

        # block until all commands are finished, then clear output
        while self.commands or self.running_command:
            time.sleep(BUSY_WAIT_TIME)
        self.output.clear()

    # -------------------- public methods --------------------

    def run(self, cmd):
        """Run a custom command in the UCLI"""

        if self.proc.poll() is not None:
            click.secho(f"Command '{cmd}' can not run, simulation has ended.", fg="red")
            return

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
            while command not in self.output and self.proc.poll() is None:
                time.sleep(BUSY_WAIT_TIME)

        # this will remove the command from the output dictionary
        # do we want this behavior to allow blocking, or
        # should we allow "caching" of the output for repeated access?
        try:
            return self.output.pop(command)
        except KeyError:
            return []

    def get_clock(self):
        """Special function to get the clock cycle and parse it instead of relying on get_var"""

        total_time = self.get_time()
        if total_time == -1:
            return -1
        cc = total_time // self.clock_speed
        return cc

    def get_time(self):
        """Special function to get the simulation time and parse it instead of relying on get_var"""

        try:
            total_time = self.read("senv time", blocking=True, run=True)[0]
            return convert_time(total_time)
        except IndexError:
            return -1

    def list_vars(self):
        """List all variables found in the Verilog code currently being simulated"""

        variables = []
        top_vars = self.read("show -type", blocking=True, run=True)
        for var in top_vars:
            var_name = var.split(" ")[0]
            if len(var_name) >= 3 and var_name[0] == "{" and var_name[-1] == "}":
                var_name = var_name[1:-1]
            if var_name == "extra" or var_name == "":
                continue
            is_instance = var.split(" ")[1] == "{INSTANCE"
            if is_instance:
                sub_variables = self._recurse_list_vars(var_name)
                variables.extend(sub_variables)
            else:
                variables.append((var_name, " ".join(var.split(" ")[1:])))
        return variables

    def _recurse_list_vars(self, var):
        """Recursively list all variables found in the Verilog code currently being simulated"""

        # TODO: where is the "extra" variable coming from?

        variables = []
        # get the children of the current variable

        # handle generate blocks
        if len(var) >= 3 and var[0] == "{" and var[-1] == "}":
            var = var[1:-1]
        
        children = self.read(f"show -type {{{var}.*}}", blocking=True, run=True)
        for child in children:
            child_name = child.split(" ")[0]
            if len(child_name) >= 3 and child_name[0] == "{" and child_name[-1] == "}":
                child_name = child_name[1:-1]
            if child_name == "extra" or child_name == "":
                continue
            is_instance = child.split(" ")[1] == "{INSTANCE"
            if is_instance:
                sub_variables = self._recurse_list_vars(child_name)
                variables.extend(sub_variables)
            else:
                variables.append((child_name, " ".join(child.split(" ")[1:])))
        return variables

    def get_var(self, var):
        """Get the value of a variable in the Verilog code currently being simulated"""
        return self.read(f"get {{{var}}}", blocking=True, run=True)[0]

    def get_vars(self, vars):
        """Get the values of multiple variables in the Verilog code currently being simulated"""
        variables = {}
        for var in vars:
            variables[var] = self.get_var(var)
        return variables

    # Ok don't do it this way it's way too slow to read in big variables like memory
    # def get_vars(self):
    #     """Get the values of all variables in the Verilog code currently being simulated"""

    #     var_dict = {}
    #     top_vars = self.read("show -type", blocking=True, run=True)
    #     values = self.read("show -value", blocking=True, run=True)
    #     for value in values:
    #         var_name = value.split(" ")[0]
    #         var_value = " ".join(value.split(" ")[1:])
    #         var_dict[var_name] = var_value
    #     for var in top_vars:
    #         var_name = var.split(" ")[0]
    #         is_instance = var.split(" ")[1] == "{INSTANCE"
    #         if is_instance:
    #             sub_values = self._recurse_get_vars(var_name)
    #             # combine the dictionaries
    #             for key in sub_values:
    #                 var_dict[key] = sub_values[key]
    #     return var_dict

    # def _recurse_get_vars(self, var):
    #     """Recursively get the values of all variables in the Verilog code currently being simulated"""

    #     values = {}
    #     # get the children of the current variable
    #     children = self.read(f"show -type {var}.*", blocking=True, run=True)
    #     child_values = self.read(f"show -value {var}.*", blocking=True, run=True)
    #     for child_value in child_values:
    #         child_name = child_value.split(" ")[0]
    #         child_value = " ".join(child_value.split(" ")[1:])
    #         values[child_name] = child_value
    #     for child in children:
    #         child_name = child.split(" ")[0]
    #         is_instance = child.split(" ")[1] == "{INSTANCE"
    #         if is_instance:
    #             sub_values = self._recurse_get_vars(child_name)
    #             # combine the dictionaries
    #             for key in sub_values:
    #                 values[key] = sub_values[key]
    #     return values

    def set_time(self, target_time, relative=False):
        """Set the simulation time to a specific (relative?) value in ps"""

        # can't go to negative absolute time
        if not relative and target_time < 0:
            return False, ""

        # if relative time and target time is 0, do nothing
        if relative and target_time == 0:
            return True, ""

        current_time = self.get_time()

        # if negative relative time, convert to absolute time
        if relative and target_time < 0:
            target_time = current_time + target_time
            relative = False

        # if absolute time and target time is > current time, convert to relative time
        if not relative and target_time > current_time:
            target_time = target_time - current_time
            relative = True

        # this should handle all future times (relative or absolute, but always converted to relative before here)
        # if relative time, just run to there
        if relative:
            output = self.read(f"run -relative {convert_time_to_str(target_time)}", blocking=True, run=True)
            return True, output

        # here we have absolute time and target time < current time

        # now, calculate the difference
        time_diff = target_time - current_time

        # if time is 0, do nothing
        if time_diff == 0:
            return True, ""

        if time_diff > 0:
            output = self.read(f"run -relative {convert_time_to_str(time_diff)}", blocking=True, run=True)
            return True, output

        # get checkpoints and see which has the closest time (but is still less than the target time)
        checkpoints = self.read("checkpoint -list", blocking=True, run=True)
        closest_checkpoint = None
        closest_time = 0

        # if there are checkpoints, remove first line
        if len(checkpoints) > 0:
            checkpoints.pop(0)

        for checkpoint in checkpoints:
            checkpoint_time = checkpoint.split("Time : ")[1].split(" Descr : ")[0]
            checkpoint_time = convert_time(checkpoint_time)
            if checkpoint_time < target_time and checkpoint_time > closest_time:
                closest_time = checkpoint_time
                closest_checkpoint = checkpoint.split(":")[0].strip()

        # if no checkpoints are found, go to start and then run to the target time
        if not closest_checkpoint:
            self.read("checkpoint -join 1", blocking=True, run=True)
            output = self.read(f"run -relative {convert_time_to_str(target_time)}", blocking=True, run=True)
            return True, output

        # if a checkpoint is found, go to that checkpoint and then run to the target time
        self.read(f"checkpoint -join {closest_checkpoint}", blocking=True, run=True)
        if closest_time < target_time:
            output = self.read(f"run -relative {convert_time_to_str(target_time - closest_time)}", blocking=True, run=True)
            return True, output

        return True, "UCLI.py: How did we get here?"

    def clock_cycle(self, cycles):
        """Run the simulation for a number of clock cycles"""

        # behind the scenes, should actually convert to time and call set_time
        target_time = (cycles * self.clock_speed) # + self.get_time() # don't need with relative=True

        success, output = self.set_time(target_time, relative=True)

        return success, output

    def step_next(self, numLines=10):
        """Run the simulation to the next step"""

        return self.read("step", blocking=True, run=True)


    def get_code(self, numLines=10):
        """Get the current code listing from the simulation"""

        code = self.read(f"listing -active {numLines}", blocking=True, run=True)

        return code

    # TODO: add a way to run the simulation for a certain amount of time

    # TODO: add a way to run the simulation until a certain variable changes

    # TODO: stop the simulation

    # TODO: reset the simulation

    # TODO: handle crashes / infinite loops

    # TODO: run gdb commands with cbug::gdb gdb-cmd

    # TODO: add breakpoints

    # TODO: add support for changing variables

    # TODO: add ucli command line input

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

        # while proc is running
        while not self.EOF and not self.stop and self.proc.poll() is None:
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

        # TODO: handle the case where the process has ended
        # ie, should we restart the process? or just let it die?

        if self.verbose:
            if self.commands:
                click.secho("Commands left in queue:", fg="black")
                for cmd in self.commands:
                    click.secho(cmd, fg="black")

        # gracefully close the process and cleanup
        self.close()

    def close(self):
        self.stop = True
        if "proc" in dir(self):
            # run exit command to close the simulation
            try:
                self.proc.stdin.write("exit\n".encode())
                self.proc.stdin.flush()
                self.proc.stdin.close()
                self.proc.stdout.close()
                self.proc.stderr.close()
                self.proc.kill()
                # self.proc.wait()
            except (BrokenPipeError, ValueError):
                pass

        # self.thread.join()

    def __del__(self):
        self.close()

if __name__ == "__main__":
    import sys

    # take everything after the script name as the command
    cmd = "./build/simv +MEMORY=programs/mem/test_1.mem +OUTPUT=output/test_1"

    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])

    # example command for running test_1 in project 3 / lab 4
    print("Booting up simv simulation...")

    # add "-ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc" to the command
    cmd += " -ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc"

    ucli = UCLI(cmd)

    print("Simulation booted.")
    print("Starting simulation...")

    ucli.start()

    print("Simulation started.")

    print("Clock speed:", ucli.clock_speed)
    print("Clock cycles:", ucli.get_clock())
    print("Simulation time:", ucli.get_time())

    print("Listing variables...")
    print(ucli.list_vars())
