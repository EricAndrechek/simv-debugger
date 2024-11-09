from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical, Container
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
                self.settings = json.load(f)
        else:
            self.settings = {}


class SettingsWidget(Widget):
    def __init__(self, id=None):
        super().__init__(id=id)

    def compose(self) -> ComposeResult:
        # return a container with various settings
        # that can be toggled
        with Container():
            with Vertical():
                yield Label("Settings")
                yield Checkbox("Verbose")
                yield Checkbox("Show Clock")
                yield Checkbox("Show Reset")
                yield Checkbox("Show Clock Count")
                yield Checkbox("Show Memory Writeback")
                yield Checkbox("Show Register")

