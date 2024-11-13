from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical, Container
from textual.widgets import Button, Footer, Header, Static, Label, Input, Pretty, Checkbox, RichLog, Tabs, Tab, TabbedContent, TabPane, Rule
from textual.reactive import reactive
from textual import events
from textual.suggester import SuggestFromList
from textual.validation import Function, Number, ValidationResult, Validator
from textual.message import Message
from textual.widget import Widget
from textual.binding import Binding

from rich.syntax import Syntax

import os
import json
import click
import time

from settings import Globals, SettingsWidget
from variables import VariableDisplayList, VariableDisplay
from make import MakeTargets, MakeTarget, load_makefile
from codeview import CodeWidget
from ucli import UCLI

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

# TODO: how to get values from structs in vars?
# TODO: should remove variable from variables list if it is in watching and add back if removed


class ucliData(Message):
    def __init__(self, data=None, cmd=None, msg=None, error=None):
        self.data = data
        self.cmd = cmd
        self.msg = msg
        self.error = error
        super().__init__()

class ClockDisplay(Widget):
    clock = reactive("0x0")
    simtime = reactive("0", recompose=True)

    def __init__(self, id=None) -> None:
        super().__init__(id=id)

    class Submit(Message):
        def __init__(self, value):
            self.value = value
            super().__init__()

    def compose(self) -> ComposeResult:
        with Container(classes="clock_display"):
            yield Static("Clock:")
            # TODO: allow users to change clock cycle as well as time
            yield Label(f"{self.clock} Cycles", classes="clock")
            yield Rule(orientation="vertical", line_style="heavy")
            yield Static("Simulation Time:")
            yield Input(f"{self.simtime}", placeholder="absolute target time (ps)", classes="simtime", type="integer")

    def on_input_submitted(self, event):
        self.post_message(self.Submit(event.value))

class SIMVApp(App):
    """Textual application for simv debugging"""

    show_help = False

    CSS_PATH = "debugger.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("?", "help", "Show help"),
        Binding("down", "next_clock", "Next clock cycle", show=False),
        Binding("up", "previous_clock", "Previous clock cycle", show=False),
        Binding("n", "next_line", "Next line", show=False),
    ]

    def action_help(self):
        """Show help."""
        # toggle showing the help panel
        self.show_help = not self.show_help
        if self.show_help:
            self.action_show_help_panel()
        else:
            self.action_hide_help_panel()

    def run_ucli(self, cmd):

        if not os.path.exists(cmd.split()[0]):
            self.post_message(ucliData(msg=f"[red]Executable {cmd.split()[0]} does not exist\n"))
            # self.exit()
            return
        if self.verbose:
            self.post_message(ucliData(msg="[dim]Booting up simv simulation...\n"))

        try:
            self.ucli = UCLI(cmd)
            Globals().ucli = self.ucli
        except (FileNotFoundError, ValueError) as e:
            self.ucli = None
            Globals().ucli = None
            self.post_message(ucliData(msg=e, error=True))

            # if the error is a FileNotFoundError, try to help
            if isinstance(e, FileNotFoundError):
                # search build directory (if it exists) for .simv executable files
                if os.path.exists("build"):
                    files = os.listdir("build")
                    simv_files = [f for f in files if f.endswith(".simv")]

                    if len(simv_files) > 0:
                        self.post_message(ucliData(msg="Did you mean one of these simv executables I found?"))
                        for f in simv_files:
                            self.post_message(ucliData(msg=f"./build/{f}\n"))

            # self.exit()
            return

        if self.verbose:
            self.post_message(ucliData(msg="[dim]Simulation booted.\n"))
            self.post_message(ucliData(msg="[dim]Starting simulation...\n"))

        try:
            self.ucli.start()
        except (FileNotFoundError, ValueError) as e:
            self.post_message(ucliData(msg=e, error=True))
            # self.exit()
            return

        if self.verbose:
            self.post_message(ucliData(msg="[dim]Simulation started.\n"))

    def __init__(self, cmd, verbose=False):
        super().__init__()

        self.verbose = verbose
        self.cmd = cmd
        self.ucli = None
        Globals().ucli = None

        self.dark = Globals().settings.get("dark", True)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        yield Header(show_clock=True)

        with Horizontal(classes="clock_controls"):
            yield Button("<-- Clock Back", name="previous_clock", id="previous_clock")
            yield ClockDisplay(id="clock-display")
            yield Button("Clock Next -->", name="next_clock", id="next_clock")
            yield Button("Step Line -->", name="next_line", id="next_line")

        # check if remember last tab is set
        remember_last_tab = Globals().settings.get("remember_last_tab", True)
        tab = "gui-tab"
        if remember_last_tab:
            tab = Globals().settings.get("tab", "gui-tab")
            if tab not in ["make-tab", "log-tab", "variables-tab", "gui-tab", "code-tab", "settings-tab"]:
                tab = "gui-tab"

        with TabbedContent(initial=tab):
            with TabPane("Make", id="make-tab"):
                yield MakeTargets()

            with TabPane("Log", id="log-tab"):
                yield RichLog(highlight=True, markup=True, wrap=True, auto_scroll=True, id="log")

            with TabPane("Variables", id="variables-tab"):
                yield VariableDisplayList(id="variable_list")

            with TabPane("GUI", id="gui-tab"):
                # TODO
                yield Static("Visual elements for each stage will go here")

            with TabPane("Code", id="code-tab"):
                yield CodeWidget(id="codeview")

            with TabPane("Settings", id="settings-tab"):
                yield SettingsWidget(id="settings")

        yield Footer()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Show the selected tab."""
        id = event.tab.id.split("--content-tab-")[1]
        # self.query_one(TabbedContent).active = event.tab.id
        Globals().change_tab(id)

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(TabbedContent).active = tab

    def on_ucli_data(self, message) -> None:
        """Handle the UCLI being ready."""
        if message.msg:
            if message.error:
                self.query_one("#log").write(f"[red]Error: {message.msg}\n")
                return
            else:
                self.query_one("#log").write(f"{message.msg}\n")

        if message.cmd == "update_variable_list":
            self.query_one(VariableDisplayList).update_variable_list()

            self.run_worker(
                self.update_variables,
                thread=True,
                exclusive=True,
                group="update_variables",
            )

            # write the variables to the log
            self.query_one("#log").write("Variables found in simulation:\n")
            for var in Globals().variables:
                if var[0] != "extra":
                    self.query_one("#log").write(f"{var[0]}: {var[1]}\n")
        elif message.cmd == "update_clock":
            self.query_one(ClockDisplay).clock = message.data
        elif message.cmd == "update_simtime":
            self.query_one(ClockDisplay).simtime = message.data
            Globals().simtime = message.data
        elif message.cmd is not None and message.cmd.startswith("update_var_"):
            var_name = message.cmd.split("update_var_")[1]
            self.query_one(f"#vd_{var_name} .variable_value").update(message.data)
        elif message.cmd == "update_code":
            if isinstance(message.data, str):
                self.query_one("#code").clear()
                self.query_one("#code").write(Syntax(message.data, "verilog"))
            else:
                self.query_one("#code").clear()
                for line in message.data:
                    self.query_one("#code").write(Syntax(line, "verilog"))

    def mount_work(self):
        if self.cmd is not None:
            self.post_message(ucliData(msg=f"Running simv executable `{self.cmd}`...\n"))
            self.run_ucli(self.cmd)
            if self.ucli:
                Globals().variables = self.ucli.list_vars()
                self.post_message(ucliData(cmd="update_variable_list"))
                self.notify(
                    f"VCS setup and ready to use!", severity="information", timeout=2
                )
                return
        self.ucli = None
        Globals().ucli = None
        self.notify(f"No simv executable provided", severity="warning", timeout=2)
        self.post_message(ucliData(msg="No simv executable provided", error=True))

    def on_mount(self) -> None:
        """Mount the app, click a tab, and update the variables."""

        self.title = "SIMV Debugger"
        self.sub_title = "Made w/ <3 by the Speculative Dispatchers"

        # focus tabs
        self.query_one(Tabs).focus()

        # run the work in a thread
        self.run_worker(self.mount_work, thread=True)

    def update_variables(self):
        """Update the values of the list of variables being watched."""
        # get variables from ucli
        if self.ucli:
            # check if ucli is still running
            if self.ucli.stop is True:
                self.post_message(ucliData(msg="Simulation has stopped.\n", error=True))
                return

            # update the clock cycle
            try:
                clock = self.ucli.get_clock()
                if clock is None or clock == -1:
                    self.post_message(ucliData(msg="Simulation has ended.\n", error=True))
                    return
            except IndexError:
                # simulation has ended
                self.post_message(ucliData(msg="Simulation has ended.\n", error=True))
                return
            self.post_message(ucliData(data=hex(clock), cmd="update_clock"))
            # update the simulation time
            simtime = self.ucli.get_time()
            if simtime == -1:
                self.post_message(ucliData(msg="Simulation time not available. This probably means you ran past the last clock cycle and the simulation ended.\n", error=True))
            else:
                self.post_message(ucliData(data=simtime, cmd="update_simtime"))

            # update the values of the variables being watched
            for var in self.query(VariableDisplay):
                var_name = var.var_name.replace(".", "_dot_")

                var_val = self.ucli.get_var(var.var_name)

                if var_val.startswith("'b"):
                    var_val = var_val[2:]
                    # catch unintialized values
                    if 'x' in var_val or "X" in var_val or "z" in var_val or "Z" in var_val:
                        var_val = str(var_val)
                    else:
                        try:
                            var_val = hex(int(var_val, 2))
                        except ValueError:
                            var_val = str(var_val)
                    self.post_message(ucliData(data=var_val, cmd=f"update_var_{var_name}"))
                else:
                    # not a binary value. if not a struct or array, just display the value
                    if var_val.startswith("((") and var_val.endswith("))"):
                        var_val = var_val[2:-2]
                        var_val = var_val.split(",")
                        tmp_val_dict = {}
                        for sub_var in var_val:
                            sub_var = sub_var.split(" => ")
                            tmp_val_dict[sub_var[0]] = sub_var[1]

                        # if dict is not empty, render table
                        if tmp_val_dict:
                            var_val = ""
                            for key, val in tmp_val_dict.items():
                                if val.startswith("'b"):
                                    val = val[2:]
                                    # catch unintialized values
                                    if 'x' in val or "X" in val or "z" in val or "Z" in val:
                                        val = str(val)
                                    else:
                                        try:
                                            val = hex(int(val, 2))
                                        except ValueError:
                                            val = str(val)
                                var_val += f"{key}: {val}\n"
                        else:
                            var_val = "Empty struct"

                        self.post_message(ucliData(data=var_val, cmd=f"update_var_{var_name}"))
                    else:
                        var_val = str(var_val)
                        self.post_message(ucliData(data=var_val, cmd=f"update_var_{var_name}"))

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        # store in settings
        self.dark = not self.dark
        Globals().settings["dark"] = self.dark
        Globals().save_settings()

    def action_quit(self) -> None:
        """An action to quit the app."""
        # quit and cleanup settings and ucli
        if self.ucli:
            self.query_one("#log").write("Exiting simulation...\n")
            self.ucli.close()
            self.query_one("#log").write("Simulation exited.\n")
        self.exit()

    def _action_next_clock(self) -> None:
        if self.ucli:
            success, output = self.ucli.clock_cycle(1)
            if success:
                if output != "":
                    self.post_message(ucliData(msg=output))
            else:
                self.post_message(ucliData(msg="Error stepping to next clock cycle.\n", error=True))

            self.run_worker(
                self.update_variables,
                thread=True,
                exclusive=True,
                group="update_variables",
            )

    def action_next_clock(self) -> None:
        """An action to go to the next clock cycle."""
        self.run_worker(self._action_next_clock, thread=True, exclusive=True, group="ucli_control")

    def _action_previous_clock(self) -> None:
        if self.ucli:
            success, output = self.ucli.clock_cycle(-1)
            if success:
                if output != "":
                    self.post_message(ucliData(msg=output))
            else:
                self.post_message(ucliData(msg="Error stepping to previous clock cycle.\n", error=True))

            self.run_worker(
                self.update_variables,
                thread=True,
                exclusive=True,
                group="update_variables",
            )

    def action_previous_clock(self) -> None:
        """An action to go to the previous clock cycle."""
        self.run_worker(self._action_previous_clock, thread=True, exclusive=True, group="ucli_control")

    def _action_next_line(self) -> None:
        if self.ucli:
            code = self.ucli.step_next()
            self.post_message(ucliData(data=code, cmd="update_code"))
            self.run_worker(
                self.update_variables,
                thread=True,
                exclusive=True,
                group="update_variables",
            )

    def action_next_line(self) -> None:
        """An action to go to the next line."""
        self.run_worker(self._action_next_line, thread=True, exclusive=True, group="ucli_control")

    def _action_previous_line(self) -> None:
        if self.ucli:
            # TODO: needs checkpoint to go back
            self.run_worker(
                self.update_variables,
                thread=True,
                exclusive=True,
                group="update_variables",
            )

    def action_previous_line(self) -> None:
        """An action to go to the previous line."""
        self.run_worker(self._action_previous_line, thread=True, exclusive=True, group="ucli_control")

    # TODO: can seperate into different functions with @on(Button.Pressed, CSS Selector)?
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "previous_clock":
            self.action_previous_clock()
        elif event.button.id == "next_clock":
            self.action_next_clock()
        elif event.button.id == "previous_line":
            self.action_previous_line()
        elif event.button.id == "next_line":
            self.action_next_line()

    def on_clock_display_submit(self, event: ClockDisplay.Submit) -> None:
        # TODO: make this happen in background thread
        if self.ucli:
            try:
                target_time = int(event.value)
                success, output = self.ucli.set_time(target_time)

                if success:
                    self.post_message(ucliData(msg=f"Simulation time set to {target_time} ps.\n"))

                if output != "":
                    self.post_message(ucliData(msg=output))

                if success:
                    self.run_worker(
                        self.update_variables,
                        thread=True,
                        exclusive=True,
                        group="update_variables",
                    )
                else:
                    self.post_message(ucliData(msg="Error setting simulation time.\n", error=True))
            except ValueError:
                self.post_message(ucliData(msg="Invalid time format. Please enter a positive integer.\n", error=True))
                return

    def on_make_target_log_data(self, message: MakeTarget.LogData) -> None:
        """Log data from the make target."""
        self.query_one("#log").write(message.data)

    def on_make_target_run_in_debugger(self, event: MakeTarget.RunInDebugger) -> None:
        """Run the make target in the visual debugger."""
        self.query_one("#log").write(f"Running {event.target}\n")

        self.notify(f"Running {event.target}...", severity="information", timeout=2)

        self.cmd = event.target + " -ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc"

        self.run_worker(self.mount_work, thread=True)


if __name__ == "__main__":
    app = SIMVApp(None, verbose=True)
    app.run()
