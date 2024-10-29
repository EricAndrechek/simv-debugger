from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical, Container
from textual.widgets import Button, Footer, Header, Static, Label, Input, Pretty, Checkbox, RichLog
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

# try to grab settings from .settings.json
if os.path.exists(".settings.json"):
    with open(".settings.json", "r") as f:
        settings = json.load(f)
else:
    settings = {}

def save_settings():
    with open(".settings.json", "w") as f:
        json.dump(settings, f, indent=4)

# replace with actual variables
variables=["clock", "reset", "clock_count", "mem_wb", "reg"]

# TODO: how to get values from structs in vars?
# TODO: should remove variable from variables list if it is in watching and add back if removed

class ClockDisplay(Widget):
    clock = reactive("0x0 Cycles")
    simtime = reactive("0", recompose=True)

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
        if value in variables:
            return self.success()
        else:
            return self.failure("Variable not found")


class VariableDisplayList(Widget):
    """A static widget that displays the value of all watched variables."""

    watched_variables = reactive(list, recompose=True)
    unused_variables = reactive(list, recompose=True)

    def __init__(self, *children, name = None, id = None, classes = None, disabled = False):
        super().__init__(*children, name=name, id=id, classes=classes, disabled=disabled)

        if "watching" in settings:
            self.watched_variables = list(settings["watching"].keys())
            # remove any variables that are not in the global list of variables
            self.watched_variables = [
                var for var in self.watched_variables if var in variables
            ]
        else:
            self.watched_variables = []

        self.unused_variables = [
            var for var in variables if var not in self.watched_variables
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

        if "watching" in settings:
            watching = settings["watching"]
        else:
            watching = False

        if watching and var in watching and var in self.watched_variables:
            del watching[var]
            self.watched_variables.remove(var)
            self.unused_variables.append(var)
            self.mutate_reactive(VariableDisplayList.watched_variables)
            self.mutate_reactive(VariableDisplayList.unused_variables)
            save_settings()

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

        if "watching" not in settings:
            settings["watching"] = {}
            settings["watching"][event.value] = ""
        elif event.value not in settings["watching"]:
            settings["watching"][event.value] = ""
        else:
            # don't overwrite the value or change settings
            pass

        # save settings
        save_settings()

        # TODO: clear the input and remove focus
        self.query_one("#add_var").clear()

        self.unused_variables.remove(event.value)
        self.watched_variables.append(event.value)
        self.mutate_reactive(VariableDisplayList.watched_variables)
        self.mutate_reactive(VariableDisplayList.unused_variables)


class SIMVApp(App):
    """Textual application for simv debugging"""
    global variables

    show_help = False

    CSS_PATH = "debugger.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("?", "help", "Show help"),
        Binding("right", "next_clock", "Next clock cycle", show=False),
        Binding("left", "previous_clock", "Previous clock cycle", show=False),
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

    def __init__(self, ucli=None):
        global variables
        super().__init__()

        self.ucli = ucli

        self.dark = settings.get("dark", False)

        # get variables from ucli
        if self.ucli:
            variables = self.ucli.list_vars()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # yield Header()
        yield VariableDisplayList(id="left-pane")

        with Container(id="main-screen"):
            yield ClockDisplay()
            with Container():
                yield RichLog(highlight=True, markup=True, id="log")
            with Container(id="clock-controls"):
                yield Button("Clock Back", name="previous_clock", id="previous_clock")
                yield Button("Clock Next", name="next_clock", id="next_clock")

        yield Footer()

    def update_variables(self):
        """Update the values of the list of variables being watched."""
        # get variables from ucli
        if self.ucli:
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
                        var_val = hex(int(var_val, 2))
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
                                        val = hex(int(val, 2))
                                var_val += f"{key}: {val}\n"
                        else:
                            var_val = "Empty struct"

                        self.query_one(f"#vd_{var_name} .variable_value").update(var_val)
                    else:
                        var_val = str(var_val)
                        self.query_one(f"#vd_{var_name} .variable_value").update(var_val)

            # update the clock cycle
            clock = self.ucli.get_clock()
            self.query_one(ClockDisplay).clock = hex(clock)
            # update the simulation time
            simtime = self.ucli.get_time()
            self.query_one(ClockDisplay).simtime = simtime

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        # store in settings
        self.dark = not self.dark
        settings["dark"] = self.dark
        save_settings()

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


if __name__ == "__main__":

    # if running on its own, don't hook in a UCLI
    app = SIMVApp()
    app.run()
