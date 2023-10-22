import asyncio
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple, NamedTuple, TypedDict

import reflex as rx
from loguru import logger

from clippy.run import Clippy
from trajlab.approval_status import ApprovalStatus, ApprovalStatusHelper
from trajlab.constants import image_assets, image_type, len_long, len_short, sort_options, tasks_dir
from trajlab.db_interface import db_interface
from trajlab.utils.file_utils import get_task_file_path, get_tasks, load_task_json_file, truncate_string


@lru_cache(maxsize=128)
def cache_get_tasks(tasks_dir: str = tasks_dir) -> List[str]:
    """
    This function uses a cache to store the results of the get_tasks function.
    The cache has a maximum size of 128 entries. If the cache is full, the least recently used entry will be discarded.
    However, we also have the ability to force a redo of the get_tasks function, bypassing the cache.
    """
    return get_tasks(tasks_dir=tasks_dir)


@lru_cache(maxsize=128)
def cache_load_task_json_file(filepath: str = None, id: str = None, get_path_func=None) -> dict:
    """
    This function uses a cache to store the results of the load_task_json_file function.
    The cache has a maximum size of 128 entries. If the cache is full, the least recently used entry will be discarded.
    However, we also have the ability to force a redo of the load_task_json_file function, bypassing the cache.
    """
    return load_task_json_file(filepath=filepath, id=id, get_path_func=get_path_func)


def clean_approval_status_emoji(status: str) -> str:
    """
    This function cleans up the approval status emoji.
    If the status is either "❌" or "✅", it adds spaces around the emoji.
    If the status is not recognized, it returns None.
    """
    if status in ["❌", "✅"]:
        return f" {status} "
    return None


class TaskValuesDict(TypedDict):
    """
    This is a TypedDict class for task values.
    It includes the id, short_id, status, clean_status, and datetime of a task.
    """

    id: str
    short_id: str
    status: str
    clean_status: str
    datetime: str


class State(rx.State):
    """
    This is the base state class.
    It includes the show_datetime, sort_by, sort_direction, show_task_values, and _tasks attributes.
    It also includes the tasks, load_tasks, task_list_name, toggle_show_task_value, and reload_database methods.
    """

    show_datetime: bool = False
    sort_by: str = "id"
    sort_direction: str = "descending"
    show_task_values: Dict[str, bool] = {
        "approval_status": True,
        "datetime": False,
    }

    _tasks = List[TaskValuesDict]

    @rx.var
    def tasks(self) -> List[TaskValuesDict]:
        """
        This method loads the tasks, cleans up their status, and sorts them.
        It returns a list of TaskValuesDict.
        """
        self.load_tasks()

        self._tasks = [
            TaskValuesDict(
                id=t[0],
                short_id=truncate_string(t[0], len_short, suffix_str=""),
                status=t[1],
                clean_status=clean_approval_status_emoji(t[1]),
                datetime=datetime.fromtimestamp(t[2]).strftime("%m-%d %H:%M"),
            )
            for t in self._tasks
        ]
        self._tasks.sort(key=lambda v: v.get(self.sort_by), reverse=self.sort_direction == "descending")
        return self._tasks

    def load_tasks(self) -> None:
        """
        This method loads the tasks from the cache and logs the number of tasks loaded.
        """
        tasks: List[Path] = cache_get_tasks(tasks_dir)
        tasks = [
            [
                f.name,
                ApprovalStatusHelper.get_emoji(ApprovalStatusHelper.get_status(f.name)),
                f.stat().st_mtime,
            ]
            for f in tasks
        ]
        logger.info(f"loaded {len(tasks)} tasks")
        self._tasks = tasks

    def task_list_name(self, task_values: TaskValuesDict) -> str:
        """
        This method returns the short_id of a task.
        """
        return task_values[1]

    def toggle_show_task_value(self, property: str) -> None:
        """
        This method toggles the visibility of a task value.
        """
        self.show_task_values[property] = not self.show_task_values[property]

    def reload_database(self) -> None:
        """
        This method reloads the database.
        """
        db_interface.reload_database()


class MenuState(State):
    """
    This is the MenuState class, which inherits from the State class.
    It includes the show_right, show_task_extra, right, close_drawer, check_main, and check_main_arg methods.
    """

    show_right: bool = False
    show_task_extra: bool = False

    def right(self):
        """
        This method toggles the visibility of the right menu.
        """
        self.show_right = not (self.show_right)

    def close_drawer(self) -> None:
        """
        This method closes the right menu.
        """
        self.show_right = False

    def check_main(self) -> None:
        """
        This method prints "secondary value".
        """
        print("secondary value")

    def check_main_arg(self, arg) -> None:
        """
        This method prints "secondary value" and the argument.
        """
        print("secondary value", arg)


class StepState(State):
    """
    This is the StepState class, which inherits from the State class.
    It includes the step_id, url, image_path, approved, short_url, short_id, parse_step, approve_step, and reject_step methods.
    """

    step_id: str = None
    url: str = None
    image_path: str = None
    approved: bool = False

    short_url: str = None
    short_id: str = None

    @classmethod
    def parse_step(cls, step: Dict[str, str], task_id: str):
        """
        This class method parses a step and returns an instance of StepState.
        """
        short_url = truncate_string(step["url"], len_long)
        short_id = truncate_string(step["id"], len_long)
        image_path = f"{image_assets}/{task_id}/{step['id']}.{image_type}"

        inst = cls(
            step_id=step["id"],
            url=step["url"],
            image_path=image_path,
            short_url=short_url,
            short_id=short_id,
        )
        return inst

    def approve_step(self):
        """
        This method is a placeholder for approving a step.
        """
        pass

    def reject_step(self):
        """
        This method is a placeholder for rejecting a step.
        """
        pass


class TaskState(State):
    """
    This is the TaskState class, which inherits from the State class.
    It includes the task_id, task_id_short, objective, timestamp, status, _steps, _clippy, full_path, load_task, goto_task, is_task_loaded, task_status_color, len_steps, steps, approve_task, reject_task, remove_task_status, launch_from_state, initiate_new_random_task, generate_new_task, new_task_on_load, start_new_task, and end_new_task methods.
    """

    task_id: str = None
    task_id_short: str = None
    objective: str = None
    timestamp: str = None
    status: str = ApprovalStatus.PENDING
    full_path: str = None  # full_path to the json which is needed b/c we have to cd to trajlab

    # backend vars
    _steps: List[Dict[str, str]] = []
    _clippy: Clippy = None

    # steps: List[Step] = None

    def load_task(self, task_id: str):
        """
        This method loads a task and logs the task id.
        """
        logger.info(f"loading task {task_id}...")
        self.full_path = get_task_file_path(tasks_dir=Path(tasks_dir), task_id=task_id)
        data = cache_load_task_json_file(filepath=self.full_path)

        self.task_id = data["id"]
        self.task_id_short = self.task_id[:len_short]
        self.objective = data["objective"]
        self.timestamp = data["timestamp"]
        self._steps = data["steps"]

        self.status = ApprovalStatusHelper.get_status(task_id=task_id)

    def goto_task(self, task_id: str):
        """
        This method loads a task and redirects to the task page.
        """
        self.load_task(task_id)
        return rx.redirect(f"/task/{task_id}")

    def is_task_loaded(self):
        """
        This method checks if a task is loaded.
        If the task is not loaded, it loads the task.
        """
        MenuState.show_task_extra = True
        task_id = self.get_query_params().get("task_id", "no task id")
        logger.info(f"checking if loaded for task_id: {task_id}")
        # im not sure exactly when either of these happen, i.e. when is self.task_id set but query params not and vice versa
        if self.task_id and (self.objective == None):
            logger.info("self.task_id is set but no objective")
            self.load_task(self.task_id)
        elif task_id != "no task id" and task_id != self.task_id:
            logger.info("task_id from query params")
            self.load_task(task_id)
        elif task_id == "no task id":
            logger.info("no task id")
        else:
            logger.info("seems like task is already loaded")

    @rx.var
    def task_status_color(self) -> str:
        """
        This method returns the color of the task status.
        """
        return ApprovalStatusHelper.get_color(self.status)

    @rx.var
    def len_steps(self) -> int:
        """
        This method returns the number of steps in a task.
        """
        return len(self._steps)

    @rx.var
    def steps(self) -> List[StepState]:
        """
        This method parses the steps of a task and returns a list of StepState.
        """
        logger.info(f"parsing {len(self._steps)} steps for task {self.task_id}")
        if self._steps != []:
            return [StepState.parse_step(s, task_id=self.task_id) for s in self._steps]
        return []

    def approve_task(self) -> None:
        """
        This method approves a task and updates the task status.
        """
        db_interface.update_approval_id(self.task_id, True)
        self.status = ApprovalStatus.APPROVED

    def reject_task(self) -> None:
        """
        This method rejects a task and updates the task status.
        """
        db_interface.update_approval_id(self.task_id, False)
        self.status = ApprovalStatus.REJECTED

    def remove_task_status(self) -> None:
        """
        This method removes the task status and updates the task status to PENDING.
        """
        db_interface.remove_obj_id(self.task_id)
        self.status = ApprovalStatus.PENDING

    def launch_from_state(self, step_id: str):
        """
        This method is a placeholder for launching from a state.
        """
        logger.info(f"should launch from this state {step_id}")

    def initiate_new_random_task(self) -> None:
        """
        This method initiates a new random task and redirects to the new task page.
        """
        self._clippy = Clippy()
        self.generate_new_task()
        return rx.redirect(f"/newtask")

    def generate_new_task(self) -> None:
        """
        This method generates a new task.
        """
        self.objective = self._clippy._get_random_task()

    def new_task_on_load(self) -> None:
        """
        This method checks if a new task is loaded.
        If not, it loads a new task.
        """
        if not self._clippy:
            self._clippy = Clippy()
        pass

    @rx.background
    async def start_new_task(self) -> None:
        """
        This method starts a new task in the background.
        """
        self._clippy.objective = self.objective
        self._clippy.keyexit = False
        async with self:
            logger.info(f"Starting task {self._clippy.objective}")
            await self._clippy.start_capture()
            self.task_id = self._clippy.task.id
            self.objective = self._clippy.task.objective

    async def end_new_task(self) -> None:
        """
        This method ends the clippy browser capture in background from clicking a button or similar
        """

        if self._clippy:
            logger.info(f"Ending task {self._clippy.objective}")
            await self._clippy.end_capture()
