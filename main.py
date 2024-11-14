from tui import SIMVApp
import sys
import os
from os import path
import requests
import click
import json
import subprocess
import selectors
import time

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

VERSION = "v1.0.21"

def main(cmd, verbose=False):
    """Main function to run the UCLI and TUI together."""
    
    if verbose:
        click.secho("Launching UI...", fg="black")

    app = SIMVApp(cmd, verbose)
    app.run()

    if verbose:
        click.secho("UI closed.", fg="black")
    del app
    if verbose:
        click.secho("UI cleaned up.", fg="black")
    
    if verbose:
        click.echo("Exiting...", fg="black")
    sys.exit(0)

def updater(update=False, check=True, verbose=False):
    # if update is true, check for updates and update automatically
    # otherwise, check for updates and prompt user to update
    # if check is false, do not check for updates

    # if both update and check are true, tell the user that they cannot be used together
    if update and check:
        click.secho("Cannot use --update and --no-update together. Make up your mind and try again.", fg="red")
        sys.exit(1)

    if check:
        if verbose:
            click.secho("Checking for updates...", fg="black")
        # check for updates
        r = requests.get("https://api.github.com/repos/EricAndrechek/simv-debugger/releases/latest", timeout=5)
        latest = r.json()
        latest_version = latest["tag_name"]
        latest_url = latest["assets"][0]["browser_download_url"]

        if latest_version != VERSION:
            if update is False:
                click.echo(f"A new version of the debugger is available! ({latest_version}) (Current: {VERSION})")
                choice = click.confirm("Would you like to update?")
                if choice:
                    update = True

            if update:
                click.echo("Downloading latest version...")

                # download the latest version
                r = requests.get(latest_url, timeout=30)
                with open("debugger_new", "wb") as f:
                    f.write(r.content)

                # make a new file to
                # wait for the python process to close
                # delete this version of the program (debugger executable)
                # move the new version to the current version
                # restart the program
                # deleting itself

                lines = []
                lines.append("#!/bin/bash")
                lines.append("sleep 1")  # wait for the python process to close
                lines.append(f"rm {sys.argv[0]}")  # delete this version of the program
                lines.append(
                    f"mv debugger_new {sys.argv[0]}"
                )  # move the new version to the current version
                lines.append("rm .updater.sh")

                with open(".updater.sh", "w") as f:
                    f.write("\n".join(lines))

                os.system("chmod +x .updater.sh")
                os.system("./.updater.sh &")

                sys.exit(0)
            else:
                if verbose:
                    click.secho("User chose not to update. Returning to main execution...", fg="black")
        else:
            if verbose:
                click.secho("No updates available.", fg="black")
    else:
        if verbose:
            click.secho("Skipping update check...", fg="black")


def check_version(check=False):
    if check:
        click.echo(f"Simv Debugger version: {VERSION}")
        sys.exit(0)


@click.command(epilog="Check out https://github.com/EricAndrechek/simv-debugger for more")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--version", is_flag=True, help="Print the version of the debugger.")
@click.option("--update", "-u", is_flag=True, help="Check for updates and update if available.")
@click.option("--no-update", is_flag=True, help="Do not check for updates.")
@click.option("--web", "-w", is_flag=True, default=False, help="Forward the debugger UI to a public URL.")
# @click.option("--term", "-t", is_flag=True, default=False, help="Forward the terminal to a public URL. Can be combined with --web.")
@click.option("--internal-textual", is_flag=True, default=False, help="Do not use this flag manually.")
@click.argument("command", nargs=-1)
def cli(verbose, version, update, no_update, command, web, internal_textual):
    """Debugger for the simv simulator.
    
    COMMAND is the simv file to run with the debugger, followed by any arguments to pass to the simv executable. It can be omitted if you want to run the debugger without a simv executable.

    Example:
    debugger ./build/test1.simv +MEMORY=programs/mem/test_1.mem +OUTPUT=output/test
    """

    term = False

    if internal_textual:
        # get command from settings
        settings = {}
        if os.path.exists(".settings.json"):
            with open(".settings.json", "r") as f:
                try:
                    settings = json.load(f)
                except json.JSONDecodeError:
                    settings = {}
        else:
            settings = {}
        
        cmd = settings.get("cmd", None)
        if cmd == "":
            cmd = None
        
        print(f"Running debugger with command: {cmd}")
        time.sleep(10)

        main(cmd, verbose)

    check_version(version)
    updater(update, not no_update, verbose)

    cmd = None

    if len(command) == 0:
        if verbose:
            click.secho("No simv executable specified", fg="black")
    else:
        cmd = " ".join(command)
        # add "-ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc" to the command
        cmd += " -ucli -suppress=ASLR_DETECTED_INFO -ucli2Proc"
    
    settings = ""
    if os.path.exists(".settings.json"):
        with open(".settings.json", "r") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                settings = {}
    else:
        settings = {}
    
    settings["cmd"] = cmd if cmd else ""

    with open(".settings.json", "w") as f:
        json.dump(settings, f, indent=4)
    
    if web or term:
        bundle_dir = path.abspath(path.dirname(__file__))

        if web and term:
            click.echo("Running both web and term forwarding...")
            path_to_toml = path.join(bundle_dir, 'both.toml')
        elif web:
            click.echo("Running web forwarding...")
            path_to_toml = path.join(bundle_dir, 'debugger.toml')
        elif term:
            click.echo("Running term forwarding...")
            path_to_toml = path.join(bundle_dir, 'terminal.toml')

        # run "textual-web --config serve.toml"
        subprocess.run(["textual-web", "--config", path_to_toml])

    else:
        main(cmd, verbose)

    
    if verbose:
        click.secho("Exiting...", fg="black")

if __name__ == "__main__":
    cli()
