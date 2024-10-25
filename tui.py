from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static, Label, Input, Pretty
from textual.reactive import Reactive
from textual import events
from textual.suggester import SuggestFromList
from textual.validation import Function, Number, ValidationResult, Validator
from textual.message import Message

import os
import json

# try to grab settings from .settings.json
if os.path.exists(".settings.json"):
    with open(".settings.json", "r") as f:
        settings = json.load(f)
else:
    settings = {}

# replace with actual variables
variables=["clock", "reset", "clock_count", "mem_wb", "reg"]

# TODO: how to get values from structs in vars?
# TODO: should remove variable from variables list if it is in watching and add back if removed

class Spacer(Static):
    """A static widget that adds space."""

class ClockDisplay(Static):
    """A static widget that displays the processor clock cycle."""


class VariableName(Static):
    """A static widget that displays the name of a variable."""


class VariableValue(Static):
    """A static widget that displays the value of a variable."""

class VariableRemove(Static):
    """A static widget that removes a variable from the watch list."""


class VariableDisplay(Static):
    """A static widget that displays the value of a variable."""

    variable = ""
    value = ""

    def __init__(self, variable: str) -> None:
        self.variable = variable
        super().__init__()

    def on_mount(self) -> None:
        pass

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield VariableName(self.variable)
            yield VariableValue(self.value)
            remove_text = """
            [@click=app.remove_watching("{self.variable}")] x [/]
            """
            yield VariableRemove(remove_text)


class AddVarValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        """Check a string is in the list of variables."""
        if value in variables:
            return self.success()
        else:
            return self.failure("Variable not found")


class VariableDisplayList(Static):
    """A static widget that displays the value of all watched variables."""

    def compose(self) -> ComposeResult:
        """Create the text to display in the widget."""
        if "watching" in settings:
            watching = settings["watching"]
        else:
            watching = False

        with Vertical():
            if watching:
                yield Static("Variables being watched:")
                for var in watching:
                    yield VariableDisplay(var)
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
            )
    
    async def on_input_submitted(self, value: str) -> None:
        """Add a variable to the watch list."""

        # check validation
        if value not in variables:
            return

        if "watching" not in settings:
            settings["watching"] = {}
            settings["watching"][value] = ""
        elif value not in settings["watching"]:
            settings["watching"][value] = ""
        else:
            # don't overwrite the value or change settings
            pass
        with open(".settings.json", "w") as f:
            json.dump(settings, f)

        # clear the input
        self.mount()
        self.query_one("#add_var").value = ""
        self.query_one("#add_var").refresh()


class SIMVApp(App):
    """Textual application for simv debugging"""

    CSS_PATH = "debugger.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # yield Header()
        yield Footer()
        with Horizontal():
            yield VariableDisplayList()

            with Vertical():
                yield Spacer()
                with Horizontal():
                    yield Button("Previous Clock", name="previous_clock")
                    yield Button("Next Clock", name="next_clock")

            yield ClockDisplay("Clock cycle: 0")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        # store in settings
        self.dark = not self.dark

if __name__ == "__main__":
    app = SIMVApp()
    app.run()
