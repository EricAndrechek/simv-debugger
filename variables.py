from textual.app import App, ComposeResult
from textual.containers import (
    ScrollableContainer,
    Horizontal,
    Vertical,
    Container,
    VerticalScroll,
)
from textual.widgets import Button, Footer, Header, Static, Label, Input, Pretty, Checkbox, RichLog, Tabs, Tab, TabbedContent, TabPane, Select, Collapsible
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

from settings import Globals

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


class VariableDisplay(Widget):
    """A static widget that displays the value of a variable."""

    class Selected(Message):
        def __init__(self, id):
            self.id = id
            super().__init__()

    var_name = ""
    var_val = reactive(0)

    # dictionary of values mapped to time
    values = reactive({}, recompose=True)

    def __init__(self, variable: str, id=None, var_type="") -> None:
        self.var_name = variable
        self.var_type = var_type
        super().__init__(id=id)

    def on_mount(self) -> None:
        self.query_one(Static).tooltip = f"Type: {self.var_type}"
        self.query_one(Checkbox).tooltip = f"Remove {self.var_name} from the watch list"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="variable_content"):
            yield Static(self.var_name, classes="variable_name")
            # TODO: change to text box to allow changing?
            yield Label(f"{self.var_val}", classes="variable_value")
            yield Checkbox(
                "",
                id=f"{self.var_name.replace('.', '_dot_')}-button",
                classes="variable_remove",
            )
            with Collapsible(collapsed=True, title="Show Drivers and Loads"):
                yield RichLog(
                    id=f"{self.var_name.replace('.', '_dot_')}-drivers",
                    highlight=True,
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                )

            # TODO: sparkline of values over time here

    def on_collapsible_expanded(self, event):
        if Globals().ucli is not None:
            drivers = Globals().ucli.read(f"drivers {self.var_name} -full", blocking=True, run=True)
            if drivers == "":
                drivers = "None"
            # if read is a list, convert to a string
            if isinstance(drivers, list):
                drivers = "\n".join(drivers)
            loads = Globals().ucli.read(
                f"loads {self.var_name} -full", blocking=True, run=True
            )
            if loads == "":
                loads = "None"
            # if read is a list, convert to a string
            if isinstance(loads, list):
                loads = "\n".join(loads)

            self.query_one(RichLog).clear()
            self.query_one(RichLog).write("[dim] Note: These do not auto-update - please collapse and expand to manually update these values.")
            self.query_one(RichLog).write("[bold] Drivers:")
            self.query_one(RichLog).write(drivers)
            self.query_one(RichLog).write("[bold] Loads:")
            self.query_one(RichLog).write(loads)

    def on_checkbox_changed(self, event):
        self.post_message(self.Selected(self.var_name))

    def watch_var_val(self, old_val, new_val):
        self.values[Globals().simtime] = new_val


class VariableDisplayList(Widget):
    """A static widget that displays the value of all watched variables."""

    all_variables = reactive({}, recompose=True)
    watched_variables = reactive(list, recompose=True)
    unused_variables = reactive(list, recompose=True)
    dropdown_options = reactive(list, recompose=True)

    def update_variable_list(self):
        # turn Globals().variables list of tuples into a dictionary
        if hasattr(Globals(), "variables") and Globals().variables is not None:
            self.all_variables = {}
            for var_tuple in Globals().variables:
                self.all_variables[var_tuple[0]] = var_tuple[1]

            if "watching" in Globals().settings:
                self.watched_variables = list(Globals().settings["watching"].keys())
                # remove any variables that are not in the all_variables dictionary
                self.watched_variables = [
                    var for var in self.watched_variables if var in self.all_variables
                ]
            else:
                self.watched_variables = []

            self.unused_variables = [
                var for var in self.all_variables if var not in self.watched_variables
            ]

            if self.is_mounted:
                self.dropdown_options = [(var, var) for var in self.unused_variables]
                self.query_one("#add_var").set_options(self.dropdown_options)
                self.mutate_reactive(VariableDisplayList.dropdown_options)
                self.query_one("#add_var").set_options(self.dropdown_options)

    def __init__(self, *children, name = None, id = None, classes = None, disabled = False):
        super().__init__(*children, name=name, id=id, classes=classes, disabled=disabled)

        self.update_variable_list()

        # self.query_one("#add_var").set_options((var, var) for var in self.unused_variables)

    def on_mount(self) -> None:
        self.update_variable_list()

        self.dropdown_options = [(var, var) for var in self.unused_variables]
        self.query_one("#add_var").set_options(self.dropdown_options)
        self.mutate_reactive(VariableDisplayList.dropdown_options)
        self.query_one("#add_var").set_options(self.dropdown_options)

    def compose(self) -> ComposeResult:
        """Create the text to display in the widget."""

        if len(self.watched_variables) > 0:
            yield Static("Variables being watched:")
            with Container(id="variable_list"):
                for var in self.watched_variables:
                    yield VariableDisplay(var, id=f"vd_{var.replace('.', '_dot_')}", var_type=self.all_variables[var])
        else:
            yield Static("No variables being watched")

        yield Label("Add a variable to watch")
        yield Input(placeholder="Filter options")
        yield Select(prompt="Select a variable to add", id="add_var", allow_blank=True, options=self.dropdown_options)

    def on_input_changed(self, event: Input.Changed) -> None:
        filter_text = event.value.lower()
        temp_options = [
            (label, value)
            for label, value in self.dropdown_options
            if filter_text in label.lower()
        ]
        self.query_one("#add_var").set_options(temp_options)

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

        # clear input from the filter
        self.query_one(Input).value = ""

        self.dropdown_options = [(var, var) for var in self.unused_variables]
        self.query_one("#add_var").set_options(self.dropdown_options)
        self.mutate_reactive(VariableDisplayList.dropdown_options)
        self.query_one("#add_var").set_options(self.dropdown_options)

    async def on_select_changed(self, event) -> None:
        """Add a variable to the watch list."""

        if self.query_one("#add_var").is_blank():
            return

        if (
            event.value == ""
            or event.value == None
            or str(event.value) == "None"
            or str(event.value) == ""
            or str(event.value) == " "
            or str(event.value) == "BLANK"
            or str(event.value) == "Select.BLANK"
        ):
            return

        # make sure not already watching
        if (
            event.value in self.watched_variables
            and event.value in self.unused_variables
        ):
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

        self.unused_variables.remove(event.value)
        self.watched_variables.append(event.value)

        self.dropdown_options = [
            (var, var) for var in self.unused_variables
        ]
        self.query_one("#add_var").set_options(self.dropdown_options)
        self.mutate_reactive(VariableDisplayList.dropdown_options)
        self.query_one("#add_var").set_options(self.dropdown_options)

        self.mutate_reactive(VariableDisplayList.watched_variables)
        self.mutate_reactive(VariableDisplayList.unused_variables)
