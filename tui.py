from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical, Container
from textual.widgets import Button, Footer, Header, Static, Label, Input, Pretty, Checkbox, RichLog
from textual.reactive import reactive
from textual import events
from textual.suggester import SuggestFromList
from textual.validation import Function, Number, ValidationResult, Validator
from textual.message import Message
from textual.widget import Widget

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
    clock = reactive(0)

    def render(self) -> str:
        return f"Clock Cycle: {self.clock}"

    async def watch_clock(self, clock_value: int):
        # self.clock = clock_value
        await self.mount(Static())
        self.query_one(Static).update(f"Clock Cycle: {clock_value}")

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
            yield Static(f"{self.var_val}", classes="variable_value")
        with Container(classes="variable_remove"):
            yield Checkbox("", id=f"{self.var_name}-button")

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

    variables = reactive(list, recompose=True)

    def __init__(self, *children, name = None, id = None, classes = None, disabled = False):
        super().__init__(*children, name=name, id=id, classes=classes, disabled=disabled)

        if "watching" in settings:
            self.variables = list(settings["watching"].keys())

    def compose(self) -> ComposeResult:
        """Create the text to display in the widget."""

        if len(self.variables) > 0:
            yield Static("Variables being watched:")
            with Container(id="variable_list"):
                for var in self.variables:
                    yield VariableDisplay(var, id=f"vd_{var}")
        else:
            yield Static("No variables being watched")

        yield Label("Add a variable to watch")
        yield Input(
            placeholder="variable name to add",
            id="add_var",
            suggester=SuggestFromList(variables, case_sensitive=False),
            validators=[
                AddVarValidator()
            ],
            valid_empty=True
        )

    def on_variable_display_selected(self, message):

        # TODO: check if in watch list and remove it if so

        var = message.id.split("-button")[0]

        if "watching" in settings:
            watching = settings["watching"]
        else:
            watching = False

        if watching and var in watching and var in self.variables:
            del watching[var]
            self.variables.remove(var)
            save_settings()

        self.query_one(f"#vd_{var}").remove()

    async def on_input_submitted(self, event) -> None:
        """Add a variable to the watch list."""

        if event.value == "" or event.value is None:
            return

        # check validation
        if event.validation_result is None or not event.validation_result.is_valid:
            return

        # make sure not already watching
        if event.value in self.variables:
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

        self.variables.append(event.value)
        self.mutate_reactive(VariableDisplayList.variables)


class SIMVApp(App):
    """Textual application for simv debugging"""

    CSS_PATH = "debugger.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def __init__(self, ucli=None):
        super().__init__()

        self.ucli = ucli

        self.dark = settings.get("dark", False)

    def on_mount(self):
        def run_on_clock_change(clock_value: int):
            self.refresh_bindings()
        self.watch(self.query_one(ClockDisplay), "clock", run_on_clock_change)

    def check_action(self, action: str, parameters):
        """Check if an action can run (eg if simulation is finished, disable next)"""
        # can update which bindings are runnable via self.refresh_bindings() and def check_action()
        # or can bindings=True on reactive for checking automatically
        # https://textual.textualize.io/guide/actions/#dynamic-actions
        # could be useful for disabling next, run, etc when finished running
        return True

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # yield Header()
        yield VariableDisplayList(id="left-pane")

        with Container(id="main-screen"):
            yield ClockDisplay()
            with Container():
                yield RichLog(highlight=True, markup=True, id="log")
            with Container(id="clock-controls"):
                yield Container() # spacer for top left
                yield Button("Line Back", name="previous_line", id="previous_line") # top center
                yield Container() # spacer for top right

                # bottom row
                yield Button("Clock Back", name="previous_clock", id="previous_clock")
                yield Button("Line Next", name="next_line", id="next_line")
                yield Button("Clock Next", name="next_clock", id="next_clock")

        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        # store in settings
        self.dark = not self.dark

    def action_quit(self) -> None:
        """An action to quit the app."""
        # quit and cleanup settings and ucli
        if self.ucli:
            self.ucli.close()
        self.exit()

    # TODO: can seperate into different functions with @on(Button.Pressed, CSS Selector)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "previous_clock":
            if self.ucli:
                clock = await self.ucli.clock_cycle(-1, blocking=True)
                self.query_one(ClockDisplay).clock = clock
            else:
                # used for testing without UCLI
                self.query_one(ClockDisplay).clock -= 1
        elif event.button.id == "next_clock":
            if self.ucli:
                clock = await self.ucli.clock_cycle(-1, blocking=True)
                self.query_one(ClockDisplay).clock = clock
            else:
                # used for testing without UCLI
                self.query_one(ClockDisplay).clock += 1
        elif event.button.id == "previous_line":
            if self.ucli:
                # TODO: needs checkpoint to go back
                self.query_one("#log").write(Syntax("end\n", "verilog"))
            else:
                self.query_one("#log").write(Syntax("always @(posedge clock) begin\n", "verilog"))
        elif event.button.id == "next_line":
            if self.ucli:
                code = await self.ucli.read("step", blocking=True, run=True)
                self.query_one("#log").write(Syntax("end\n", "verilog"))
            else:
                self.query_one("#log").write(Syntax("end\n", "verilog"))


if __name__ == "__main__":

    # if running on its own, don't hook in a UCLI
    app = SIMVApp()
    app.run()
