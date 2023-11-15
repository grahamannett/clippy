import asyncio
from dataclasses import dataclass
from os import environ
from typing import Optional, Union

from simple_parsing import ArgumentParser, choice, subparsers

from clippy.clippy_helper import Clippy
from clippy.constants import default_objective, default_start_page


def _check_startup() -> None:
    """checks for api key.  if other keys/values should be set"""
    # TODO: check for device ratio issue.
    api_key = environ.get("COHERE_KEY")
    if api_key is None:
        raise Exception("COHERE_KEY not set in environment")


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
    llm: bool = True
    action_delay: float = 0.5
    max_actions: int = 5

    confirm_actions: bool = True


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

    command: Union[Assist, Capture, Replay, DataManager] = subparsers(
        {
            "assist": Assist,
            "capture": Capture,
            "replay": Replay,
            "datamanager": DataManager,
        },
        default=Capture,
    )

    objective: str = default_objective
    seed: int = None

    headless: bool = False  # should run without a browser window
    exec_type: str = choice("sync", "async", default="async")  # should run in async or sync mode
    start_page: str = default_start_page
    task_gen_from: str = choice("llm", "taskbank", default="taskbank")  # generate random task from task/word bank

    key_exit: bool = True  # should exit on key press
    confirm_actions: bool = False
    task_id: int | str = None

    def __post_init__(self):
        self.cmd = self.command.__class__.__name__.lower()


def get_args(to_dict: bool = False) -> ClippyArgs | dict[str, str | bool | int | None]:
    parser = ArgumentParser()
    parser.add_arguments(ClippyArgs, dest="clippy_args")
    args = parser.parse_args()

    clippy_args: ClippyArgs = args.clippy_args

    if to_dict:
        return vars(clippy_args)
    return clippy_args


def setup_run(
    check_startup: bool = True,
    check_command: bool = True,
) -> tuple[Clippy, dict[str, str | bool | int | None]]:
    if check_startup:
        _check_startup()

    clippy_args = get_args()
    kwargs = vars(clippy_args)
    clippy = Clippy(**kwargs)
    if check_command:
        clippy.check_command(**kwargs)

    return clippy, kwargs


if __name__ == "__main__":
    clippy, kwargs = setup_run()
    asyncio.run(clippy.run_capture(**kwargs))
