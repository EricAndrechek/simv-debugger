from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical, Container
from textual.widgets import Button, Footer, Header, Static, Label, Input, Pretty, Checkbox, RichLog, Tabs, Tab, TabbedContent, TabPane
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
from make import MakeTargets, MakeTarget, load_makefile
from ucli import UCLI

# TODO: how to get values from structs in vars?
# TODO: should remove variable from variables list if it is in watching and add back if removed

class ClockDisplay(Widget):
    clock = reactive("0x0 Cycles")
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
            yield Label(f"{self.clock} Cycles", classes="clock")
            yield Static("Simulation Time:")
            yield Input(f"{self.simtime}", placeholder="absolute target time (ps)", classes="simtime", type="integer")
    
    def on_input_submitted(self, event):
        self.post_message(self.Submit(event.value))

class VariableDisplay(Widget):
    """A static widget that displays the value of a variable."""

    class Selected(Message):
        def __init__(self, id):
            self.id = id
            super().__init__()

    var_name = ""
    var_val = reactive(0)

    def __init__(self, variable: str, id=None) -> None:
        self.var_name = variable
        super().__init__(id=id)

    def on_mount(self) -> None:
        pass

    def compose(self) -> ComposeResult:
        with Container(classes="variable_content"):
            yield Static(self.var_name, classes="variable_name")
            # TODO: change to text box to allow changing?
            yield Label(f"{self.var_val}", classes="variable_value")
        with Container(classes="variable_remove"):
            yield Checkbox("", id=f"{self.var_name.replace('.', '_dot_')}-button")

    def on_checkbox_changed(self, event):
        self.post_message(self.Selected(self.var_name))

class AddVarValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        """Check a string is in the list of variables."""
        if value in Globals().variables:
            return self.success()
        else:
            return self.failure("Variable not found")


class VariableDisplayList(Widget):
    """A static widget that displays the value of all watched variables."""

    watched_variables = reactive(list, recompose=True)
    unused_variables = reactive(list, recompose=True)

    def __init__(self, *children, name = None, id = None, classes = None, disabled = False):
        super().__init__(*children, name=name, id=id, classes=classes, disabled=disabled)

        if "watching" in Globals().settings:
            self.watched_variables = list(Globals().settings["watching"].keys())
            # remove any variables that are not in the global list of variables
            self.watched_variables = [
                var for var in self.watched_variables if var in Globals().variables
            ]
        else:
            self.watched_variables = []

        self.unused_variables = [
            var for var in Globals().variables if var not in self.watched_variables
        ]

    def compose(self) -> ComposeResult:
        """Create the text to display in the widget."""

        if len(self.watched_variables) > 0:
            yield Static("Variables being watched:")
            with Container(id="variable_list"):
                for var in self.watched_variables:
                    yield VariableDisplay(var, id=f"vd_{var.replace('.', '_dot_')}")
        else:
            yield Static("No variables being watched")

        yield Label("Add a variable to watch")
        yield Input(
            placeholder="variable name to add",
            id="add_var",
            suggester=SuggestFromList(self.unused_variables, case_sensitive=False),
            validators=[AddVarValidator()],
            valid_empty=True,
        )

    def on_variable_display_selected(self, message):

        # TODO: check if in watch list and remove it if so

        var = message.id.split("-button")[0].replace("_dot_", ".")

        if "watching" in Globals().settings:
            watching = Globals().settings["watching"]
        else:
            watching = False

        if watching and var in watching and var in self.watched_variables:
            del watching[var]
            self.watched_variables.remove(var)
            self.unused_variables.append(var)
            self.mutate_reactive(VariableDisplayList.watched_variables)
            self.mutate_reactive(VariableDisplayList.unused_variables)
            Globals().save_settings()

        if "." in var:
            var = var.replace(".", "_dot_")
        self.query_one(f"#vd_{var}").remove()

    async def on_input_submitted(self, event) -> None:
        """Add a variable to the watch list."""

        if event.value == "" or event.value is None:
            return

        # check validation
        if event.validation_result is None or not event.validation_result.is_valid:
            return

        # make sure not already watching
        if event.value in self.watched_variables and event.value in self.unused_variables:
            self.query_one("#add_var").clear()
            return

        if "watching" not in Globals().settings:
            Globals().settings["watching"] = {}
            Globals().settings["watching"][event.value] = ""
        elif event.value not in Globals().settings["watching"]:
            Globals().settings["watching"][event.value] = ""
        else:
            # don't overwrite the value or change settings
            pass

        # save settings
        Globals().save_settings()

        # TODO: clear the input and remove focus
        self.query_one("#add_var").clear()

        self.unused_variables.remove(event.value)
        self.watched_variables.append(event.value)
        self.mutate_reactive(VariableDisplayList.watched_variables)
        self.mutate_reactive(VariableDisplayList.unused_variables)


class SIMVApp(App):
    """Textual application for simv debugging"""

    show_help = False

    # CSS_PATH = "debugger.tcss"
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
        text_log = self.query_one("#log")

        if not os.path.exists(cmd.split()[0]):
            text_log.write(f"[red]Executable {cmd.split()[0]} does not exist\n")
            # self.exit()
            return
        if self.verbose:
            text_log.write("[dim]Booting up simv simulation...\n")

        try:
            self.ucli = UCLI(cmd)
        except (FileNotFoundError, ValueError) as e:
            text_log.write(f"[red]Error: {e}\n")

            # if the error is a FileNotFoundError, try to help
            if isinstance(e, FileNotFoundError):
                # search build directory (if it exists) for .simv executable files
                if os.path.exists("build"):
                    files = os.listdir("build")
                    simv_files = [f for f in files if f.endswith(".simv")]

                    if len(simv_files) > 0:
                        text_log.write("Did you mean to run one of these executables I found?\n")
                        for f in simv_files:
                            text_log.write(f"./build/{f}\n")

            # self.exit()
            return
        
        if self.verbose:
            text_log.write("[dim]Simulation booted.\n")
            text_log.write("[dim]Starting simulation...\n")

        try:
            self.ucli.start()
        except (FileNotFoundError, ValueError) as e:
            text_log.write(f"[red]Error: {e}\n")
            # self.exit()
            return

        if self.verbose:
            text_log.write("[dim]Simulation started.\n")

    def __init__(self, cmd, verbose=False):
        super().__init__()

        self.verbose = verbose
        self.cmd = cmd

        self.dark = Globals().settings.get("dark", False)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        yield Header(show_clock=True)

        with TabbedContent(initial="gui-tab"):
            with TabPane("Make", id="make-tab"):
                yield MakeTargets()
            with TabPane("Log", id="log-tab"):
                yield RichLog(highlight=True, markup=True, wrap=True, auto_scroll=True, id="log")
            with TabPane("Variables", id="variables-tab"):
                yield VariableDisplayList(id="left-pane")
            with TabPane("GUI", id="gui-tab"):
                with Container(id="main-screen"):
                    yield ClockDisplay(id="clock-display")
                    with Container(id="clock-controls"):
                        yield Button("Clock Back", name="previous_clock", id="previous_clock")
                        yield Button("Clock Next", name="next_clock", id="next_clock")
            with TabPane("Settings", id="settings-tab"):
                yield SettingsWidget(id="settings")

        yield Footer()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Show the selected tab."""
        self.query_one(event.tab.id).focus()

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(TabbedContent).active = tab

    def on_mount(self) -> None:
        """Mount the app, click a tab, and update the variables."""

        self.title = "SIMV Debugger"
        self.sub_title = "Made w/ <3 by the Speculative Dispatchers"

        self.query_one(Tabs).focus()

        if self.cmd is not None:
            self.run_ucli(self.cmd)
            Globals().variables = self.ucli.list_vars()
            self.update_variables()
        else:
            if self.verbose:
                self.query_one("#log").write("[dim]No simv executable specified.\n")
            self.ucli = None

        # write the variables to the log
        self.query_one("#log").write("Variables found in simulation:\n")
        for var in Globals().variables:
            self.query_one("#log").write(f"{var}\n")

    def update_variables(self):
        """Update the values of the list of variables being watched."""
        # get variables from ucli
        if self.ucli:
            # check if ucli is still running
            if self.ucli.stop is True:
                self.query_one("#log").write("Simulation has stopped.\n")
                return

            # update the clock cycle
            try:
                clock = self.ucli.get_clock()
            except IndexError:
                # simulation has ended
                self.query_one("#log").write("Simulation has ended.\n")
                return
            self.query_one(ClockDisplay).clock = hex(clock)
            # update the simulation time
            simtime = self.ucli.get_time()
            self.query_one(ClockDisplay).simtime = simtime

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
                    self.query_one(f"#vd_{var_name} .variable_value").update(var_val)
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

                        self.query_one(f"#vd_{var_name} .variable_value").update(var_val)
                    else:
                        var_val = str(var_val)
                        self.query_one(f"#vd_{var_name} .variable_value").update(var_val)

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

    def action_next_clock(self) -> None:
        """An action to go to the next clock cycle."""
        if self.ucli:
            clock = self.ucli.clock_cycle(1)
        else:
            # used for testing without UCLI
            self.query_one(ClockDisplay).clock += 1
        self.update_variables()

    def action_previous_clock(self) -> None:
        """An action to go to the previous clock cycle."""
        if self.ucli:
            clock = self.ucli.clock_cycle(-1)
        else:
            # used for testing without UCLI
            self.query_one(ClockDisplay).clock -= 1
        self.update_variables()

    def action_next_line(self) -> None:
        """An action to go to the next line."""
        if self.ucli:
            code = self.ucli.read("step", blocking=True, run=True)
            self.query_one("#log").write(Syntax(code[0], "verilog"))
        else:
            self.query_one("#log").write(Syntax("end\n", "verilog"))
        self.update_variables()

    def action_previous_line(self) -> None:
        """An action to go to the previous line."""
        if self.ucli:
            # TODO: needs checkpoint to go back
            self.query_one("#log").write(Syntax("end\n", "verilog"))
        else:
            self.query_one("#log").write(Syntax("always @(posedge clock) begin\n", "verilog"))
        self.update_variables()

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
        if self.ucli:
            try:
                target_time = int(event.value)
                success = self.ucli.set_time(target_time)
                if success:
                    self.query_one("#log").write(f"Simulation time set to {target_time} ps.\n")
                    self.update_variables()
                else:
                    self.query_one("#log").write("Error setting simulation time.\n")
            except ValueError:
                self.query_one("#log").write("Invalid time format. Please enter a positive integer.\n")
                return
        else:
            self.query_one(ClockDisplay).simtime = event.value
    
    def on_make_target_run_in_debugger(self, event: MakeTarget.RunInDebugger) -> None:
        """Run the make target in the visual debugger."""
        self.query_one("#log").write(f"Running make target {event.target}\n")

        # start ucli for the make target
        self.run_ucli(event.target)


if __name__ == "__main__":
    app = SIMVApp(None, verbose=True)
    app.run()
