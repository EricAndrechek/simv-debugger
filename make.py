# make.py: used to show make commands that can be directly run via gui from the makefile

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
)
from textual.reactive import reactive
from textual import events
from textual.suggester import SuggestFromList
from textual.validation import Function, Number, ValidationResult, Validator
from textual.message import Message
from textual.widget import Widget
from textual.binding import Binding
from textual.worker import Worker, get_current_worker

from rich.syntax import Syntax

import os
import json

import subprocess
import asyncio
import selectors


async def load_makefile():
    # run shell command to get bash completion for makefile targets
    # from https://unix.stackexchange.com/a/230050/524300 since caen
    # make has bash completion but no --print-targets
    cmd = '''make -qp | awk -F':' '/^[a-zA-Z0-9][^$#\/\t=]*:([^=]|$)/ {split($1,A,/ /);for(i in A)print A[i]}' | sort -u'''
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait()
    if proc.returncode != 0:
        return []
    error = proc.stderr.read().decode("utf-8")
    output = proc.stdout.read().decode("utf-8")
    if error:
        return []
    targets = output.split("\n")
    # remove targets that are empty or end in %
    resp = [target for target in targets if target and not target.endswith("%")]
    return resp

class MakeTarget(Widget):
    """Widget to show a make target that can be run and run it"""

    class LogData(Message):
        def __init__(self, data: str):
            super().__init__()
            self.data = data

    class RunInDebugger(Message):
        def __init__(self, target: str):
            super().__init__()
            self.target = target

    def __init__(self, target: str, id=None):
        super().__init__(id=id)
        self.target = target

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button(self.target, variant="default")
            if self.target.endswith(".out"):
                yield Button(f"Debug {self.target.replace('.out', '')}", variant="primary")

    async def button_press_thread(self):
        # run the make command
        cmd = f"make {self.target}"
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        sel.register(proc.stderr, selectors.EVENT_READ)

        # run this loop in a thread to not block the main thread
        while True:
            for key, events in sel.select():
                if key.fileobj is proc.stdout:
                    line = key.fileobj.readline().decode("utf-8").replace("(B[m", "")
                    if line:
                        # detect color codes and replace them with [color] tags
                        line = line.replace("\033[30m", "[black]")
                        line = line.replace("\033[31m", "[red]")
                        line = line.replace("\033[32m", "[green]")
                        line = line.replace("\033[33m", "[yellow]")
                        line = line.replace("\033[34m", "[blue]")
                        line = line.replace("\033[35m", "[magenta]")
                        line = line.replace("\033[36m", "[cyan]")
                        line = line.replace("\033[37m", "[white]")
                        line = line.replace("\033[0m", "")
                        line = line.replace("\033[m", "")
                        self.post_message(self.LogData(line))
                elif key.fileobj is proc.stderr:
                    line = key.fileobj.readline().decode("utf-8").replace("(B[m", "")
                    if line:
                        # detect color codes and replace them with [color] tags
                        line = line.replace("\033[30m", "[black]")
                        line = line.replace("\033[31m", "[red]")
                        line = line.replace("\033[32m", "[green]")
                        line = line.replace("\033[33m", "[yellow]")
                        line = line.replace("\033[34m", "[blue]")
                        line = line.replace("\033[35m", "[magenta]")
                        line = line.replace("\033[36m", "[cyan]")
                        line = line.replace("\033[37m", "[white]")
                        line = line.replace("\033[0m", "")
                        line = line.replace("\033[m", "")
                        # if the line doesn't start with a [color], make it red
                        if not line.startswith("["):
                            line = "[red]" + line
                        self.post_message(self.LogData(line))
            if proc.poll() is not None:
                break

        # re-enable the button
        for button in self.query(Button):
            button.disabled = False

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        # set button to disabled
        for button in self.query(Button):
            button.disabled = True

        # if the button pressed was the debug button, run the make command in the visual debugger
        if "primary" in str(event.button):
            self.post_message(self.LogData(f"Running {self.target} in the visual debugger..."))
            # TODO: can we compile the simv first and then run it in the debugger?
            # use make -n to get the commands that would be run
            self.post_message(self.RunInDebugger(f"./build/{self.target.replace('.out', '.simv')}"))

            for button in self.query(Button):
                button.disabled = False

            return

        # run the make command in a thread
        self.run_worker(self.button_press_thread, thread=True)


class MakeTargets(Widget):
    """MakeTargets widget to show make commands that can be run"""

    makefile_targets = reactive(list, recompose=True)

    def __init__(self, id=None):
        super().__init__(id=id)

    async def on_mount(self) -> None:
        self.makefile_targets = await load_makefile()
        self.mutate_reactive(MakeTargets.makefile_targets)

    def compose(self) -> ComposeResult:
        yield Label("Make Targets")
        yield Static("Click a make target to run it. If the target ends in \".out\", it will run in the visual debugger.")

        if len(self.makefile_targets) == 0:
            with ScrollableContainer():
                yield Label("No make targets found")
        else:
            with ScrollableContainer():
                for target in self.makefile_targets:
                    yield MakeTarget(target)
                    # yield MakeTarget(target, id=target.replace(" ", "_").replace(".", "_dot_"))

if __name__ == "__main__":
    # print the make commands that can be run
    make_targets = asyncio.run(load_makefile())
    print(make_targets)
