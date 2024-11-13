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


class CodeWidget(Widget):

    def __init__(self, id=None):
        super().__init__(id=id)

    def compose(self) -> ComposeResult:
        # return a container with various settings
        # that can be toggled
        with Container():
            yield RichLog(classes="code", id="code")
