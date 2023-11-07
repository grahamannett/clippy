from distutils.util import strtobool
from os import environ
from typing import Any


def _check_exec_type(exec_type: str, task: str):
    if (task == "capture") and (exec_type != "async"):
        print("==>WARNING<==")
        print("---you cannot capture task in sync mode due to needing to handle callbacks")
        print("---manually changing exec_type to async")
        print("==>WARNING END<==")
        exec_type = "async"
    return exec_type


def _device_ratio_check():
    return bool(strtobool(environ.get("KEEP_DEVICE_RATIO", "False")))


def _get_environ_var(key: str, default: Any) -> Any:
    value = environ.get(key)
    if value is not None:
        return type(default)(value)
    return default
