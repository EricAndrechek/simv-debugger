from textual.app import App, ComposeResult
from textual.containers import (
    ScrollableContainer,
    Horizontal,
    Vertical,
    Container,
    VerticalScroll,
)
from textual.widgets import Button, Footer, Header, Static, Label, Input, Pretty, Checkbox, RichLog, Tabs, Tab, TabbedContent, TabPane, Select
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

    def __init__(self, variable: str, id=None) -> None:
        self.var_name = variable
        super().__init__(id=id)

    def on_mount(self) -> None:
        pass

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
            # TODO: sparkline of values over time here

    def on_checkbox_changed(self, event):
        self.post_message(self.Selected(self.var_name))


class VariableDisplayList(Widget):
    """A static widget that displays the value of all watched variables."""

    all_variables = reactive(list, recompose=True)
    watched_variables = reactive(list, recompose=True)
    unused_variables = reactive(list, recompose=True)
    dropdown_options = reactive(list, recompose=True)

    def update_variable_list(self):
        self.all_variables = Globals().variables

        if "watching" in Globals().settings:
            self.watched_variables = list(Globals().settings["watching"].keys())
            # remove any variables that are not in the global list of variables
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
                    yield VariableDisplay(var, id=f"vd_{var.replace('.', '_dot_')}")
        else:
            yield Static("No variables being watched")

        yield Label("Add a variable to watch")
        yield Select(prompt="Select a variable to add", id="add_var", allow_blank=True, options=self.dropdown_options)

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
