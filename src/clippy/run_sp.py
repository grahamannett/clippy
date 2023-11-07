import argparse
import asyncio
from dataclasses import dataclass
from os import environ

from simple_parsing import ArgumentParser, subparsers, field

from clippy.clippy_helper import Clippy
from clippy.constants import default_objective, default_start_page
from simple_parsing import ArgumentParser, field
from typing import Optional, Union


@dataclass
class Replay:
    """Arguments for the 'replay' command"""

    file: Optional[str] = None


@dataclass
class Capture:
    """Arguments for the 'capture' command"""

    llm: bool = False


@dataclass
class Assist:
    """Arguments for the 'assist' command"""

    file: Optional[str] = None


@dataclass
class DataManager:
    """Arguments for the 'datamanager' command"""

    subcmd: Optional[str] = None
    move_current: bool = False
    override: bool = False
    table: Optional[str] = None
    droplast: bool = False


@dataclass
class ClippyArgs:
    """class docstring"""

    command: Union[Assist, Capture, Replay, DataManager]

    objective: str = default_objective
    seed: int = None

    headless: bool = False  # should run without a browser window
    exec_type: str = "async"  # should run in async or sync mode
    start_page: str = default_start_page
    random_task: bool = False
    key_exit: bool = True  # should exit on key press
    confirm_actions: bool = False
    task: int = None


def get_args():
    parser = ArgumentParser()
    parser.add_arguments(ClippyArgs, "prog")
    args = parser.parse_args()

    # flip the keyexit flag
    breakpoint()
    args.key_exit = not args.no_keyexit

    return args


def setup_run():
    args = get_args()
    breakpoint()


if __name__ == "__main__":
    clippy, kwargs = setup_run()
    asyncio.run(clippy.run_capture(**kwargs))
