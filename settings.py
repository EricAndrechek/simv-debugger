from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical, Container, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Static,
    Label,
    Input,
    Pretty,
    Checkbox,
    RichLog,
    Tabs,
    Tab,
    TabbedContent,
    TabPane,
    Switch
)
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

class Globals:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "settings"):
            self.load_settings()
        if not hasattr(self, "variables"):
            self.variables = ["clock", "reset", "clock_count", "mem_wb", "reg"]

    def save_settings(self):
        with open(".settings.json", "w") as f:
            json.dump(self.settings, f, indent=4)
    
    def load_settings(self):
        if os.path.exists(".settings.json"):
            with open(".settings.json", "r") as f:
                try:
                    self.settings = json.load(f)
                except json.JSONDecodeError:
                    self.settings = {}
        else:
            self.settings = {}
    
    def change_tab(self, tab):
        self.settings["tab"] = tab
        self.save_settings()

class SettingSwitch(Widget):
    def __init__(self, id=None, name="", value=False):

        self.switch_name = name
        self.value = reactive(value)
        if self.switch_name != "":
            # check if the setting is in the settings
            if self.switch_name in Globals().settings:
                self.value = Globals().settings[self.switch_name]
            self.switch_name += ":      "

        super().__init__(id=id)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.switch_name)
            yield Switch(value=self.value)

    def on_switch_changed(self, event):
        self.value = event.value
        Globals().settings[self.switch_name.split(":")[0]] = event.value
        Globals().save_settings()
        # TODO: throw event to update other widgets as needed

class SettingsWidget(Widget):

    # TODO: move verbose setting here?
    # verbose = reactive(False)
    # TODO: move update process and setting here?

    def __init__(self, id=None):
        super().__init__(id=id)

    def compose(self) -> ComposeResult:
        # return a container with various settings
        # that can be toggled
        with Container():
            yield SettingSwitch(name="Remember last tab", value=True)
