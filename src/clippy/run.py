import argparse
import asyncio


from os import environ

from clippy.clippy_helper import Clippy
from clippy.dm.task_bank import TaskBankManager

from clippy.constants import default_objective, default_start_page


def check_startup():
    # TODO: check for device ratio issue.
    api_key = environ.get("COHERE_KEY")
    if api_key is None:
        raise Exception("COHERE_KEY not set in environment")


def get_args():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--objective", type=str, default=default_objective)
    common.add_argument("--headless", action="store_true")
    common.add_argument("--exec_type", type=str, choices=["sync", "async"], default="async")
    common.add_argument("--start_page", type=str, default=default_start_page)
    common.add_argument("--random_task", action="store_true", default=False)
    common.add_argument("-nk", "--no_keyexit", action="store_true", default=False)
    common.add_argument("--confirm", action="store_true", default=False)

    parser = argparse.ArgumentParser(description="🤠 clippy")

    # SUBPARSERS ---
    subparsers = parser.add_subparsers(dest="cmd")
    replay_subparser = subparsers.add_parser("replay", help="replay a task", parents=[common])
    replay_subparser.add_argument("--file", type=str, default=None, help="path to file to replay")

    capture_subparser = subparsers.add_parser("capture", help="capture a task", parents=[common])
    capture_subparser.add_argument("--llm", default=False, action="store_true")

    assist_subparser = subparsers.add_parser("assist", help="assist a task", parents=[common])
    assist_subparser.add_argument("--file", type=str, default=None, help="path to file to replay")

    # GET' EM ---
    args = parser.parse_args()

    breakpoint()

    return args


def run():
    check_startup()

    args = get_args()

    clippy = Clippy(
        objective=args.objective,
        headless=args.headless,
        start_page=args.start_page,
        key_exit=not args.no_keyexit,
        confirm=args.confirm,
    )

    clippy.check_command(cmd=args.cmd)
    return clippy


if __name__ == "__main__":
    clippy = run()
    asyncio.run(clippy.run_capture(use_llm=False))
