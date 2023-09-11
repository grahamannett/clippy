import argparse
import asyncio
from os import environ

from clippy.clippy_helper import Clippy
from clippy.constants import default_objective, default_start_page


def check_startup() -> None:
    """checks for api key.  if other keys/values should be set"""
    # TODO: check for device ratio issue.
    api_key = environ.get("COHERE_KEY")
    if api_key is None:
        raise Exception("COHERE_KEY not set in environment")


def put_extra_args_on_namespace(args: argparse.Namespace, extra_args: list[str]) -> argparse.Namespace:
    """converts extra args to kwargs"""
    kwargs = {}
    for arg in extra_args:
        val = True
        if arg.startswith("--"):
            arg = arg[2:]
        if "=" in arg:
            arg, val = arg.split("=")
            # kwargs[key] = val
        setattr(args, arg, val)
        breakpoint()
        # else:
        #     kwargs[arg] = True
    return args


def get_args():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--objective", type=str, default=default_objective)
    common.add_argument("--seed", type=int, default=None)
    common.add_argument("--headless", action="store_true")
    common.add_argument("--exec_type", type=str, choices=["sync", "async"], default="async")
    common.add_argument("--start_page", type=str, default=default_start_page)
    common.add_argument("--random_task", action="store_true", default=False)
    common.add_argument("-nk", "--no_keyexit", action="store_true", default=False)
    common.add_argument("--confirm", action="store_true", default=False)
    common.add_argument(
        "--task",
        "-t",
        nargs="?",
        type=int,
        default=None,
        const=-1,
        help="task bank index to sample from - or random to sample a random task",
    )

    parser = argparse.ArgumentParser(description="🤠 clippy")

    # SUBPARSERS ---
    subparsers = parser.add_subparsers(dest="cmd")
    replay_subparser = subparsers.add_parser("replay", help="replay a task", parents=[common])
    replay_subparser.add_argument("--file", type=str, default=None, help="path to file to replay")

    capture_subparser = subparsers.add_parser("capture", help="capture a task", parents=[common])
    capture_subparser.add_argument("--llm", default=False, action="store_true")

    assist_subparser = subparsers.add_parser("assist", help="assist a task", parents=[common])
    assist_subparser.add_argument("--file", type=str, default=None, help="path to file to replay")

    datamanager_subparser = subparsers.add_parser("datamanager", help="assist a task", parents=[common])
    datamanager_subparser.add_argument("subcmd", type=str, default=None, help="datamanager cmd to do")
    datamanager_subparser.add_argument("--move_current", type=bool, default=False, help="move ")
    datamanager_subparser.add_argument("--override", type=bool, default=False)
    # db related args
    datamanager_subparser.add_argument("--table", type=str, default=None, help="table name")
    datamanager_subparser.add_argument("--droplast", action="store_true", help="only drop last from table")

    # GET' EM ---
    args, _ = parser.parse_known_args()

    # flip the keyexit flag
    args.key_exit = not args.no_keyexit

    return args


def run() -> tuple[Clippy, argparse.Namespace]:
    check_startup()

    args = get_args()
    kwargs = vars(args)
    clippy = Clippy(**kwargs)

    clippy.check_command(cmd=args.cmd, kwargs=kwargs)
    return clippy, args


if __name__ == "__main__":
    clippy, args = run()
    asyncio.run(clippy.run_capture(args=args))
