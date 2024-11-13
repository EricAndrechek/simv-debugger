from textual.app import App, ComposeResult
from textual.containers import (
    ScrollableContainer,
    Horizontal,
    Vertical,
    Container,
    VerticalScroll,
)
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
    Switch,
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


class CodeWidget(Widget):

    def __init__(self, id=None):
        super().__init__(id=id)

    def compose(self) -> ComposeResult:
        # return a container with various settings
        # that can be toggled
        with Container():
            yield RichLog(classes="code", id="code")