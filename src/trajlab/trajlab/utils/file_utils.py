import json
from pathlib import Path
from typing import List

from trajlab.trajlab_constants import TASKS_DIR


def _as_path(path: str | Path) -> Path:
    """
    Convert a string to a Path object.

    :param path: The path to convert.
    :return: The converted path.
    """
    if isinstance(path, str):
        path = Path(path)

    return path


def truncate_string(input_str: str, max_length: int, suffix_str: str = "...") -> str:
    """
    Truncate a string to a specified length, appending '...' if it exceeds the limit.

    :param input_str: The string to truncate.
    :param max_length: The maximum length of the string.
    :return: The truncated string.
    """
    return f"{input_str[:max_length]}{suffix_str}" if len(input_str) > max_length else input_str


def get_tasks(tasks_dir: str = TASKS_DIR) -> List[Path]:
    """
    Get a list of task directories from a specified directory.

    :param tasks_dir: The directory where the tasks are stored.
    :return: A list of task directory names.
    """
    return [f for f in _as_path(tasks_dir).iterdir() if f.is_dir()]


def load_task_json_file(filepath: str = None, id: str = None, get_path_func=None) -> dict:
    """
    Load a JSON file from a specified path or using an ID.

    :param filepath: The path of the file to load.
    :param id: The ID used to get the file path.
    :param get_path_func: The function used to get the file path from the ID.
    :return: The loaded data as a dictionary.
    """
    if (filepath is None) and (id is not None) and (get_path_func is not None):
        filepath = get_path_func(id)

    if isinstance(filepath, Path):
        filepath = str(filepath.resolve())

    with open(filepath) as f:
        data = json.load(f)

    return data


def get_task_file_path(task_id: str, tasks_dir: str | Path = TASKS_DIR, filename: str = "task.json") -> str:
    """
    Get the full path of a file using an ID.

    :param id: The ID used to get the file path.
    :param dir: The directory where the files are stored.
    :param filename: The name of the file.
    :return: The full path of the file.
    """

    filepath = _as_path(tasks_dir) / task_id / filename
    return str(filepath.resolve())
