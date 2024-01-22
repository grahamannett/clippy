import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import reflex as rx
from PIL import Image
from rxconfig import config

from clippy import logger
from clippy.constants import ROOT_DIR, TASKS_DATA_DIR
from clippy.instructor import NextAction
from clippy.run import Clippy
from clippy.states import Task
from trajlab.approval_status import ApprovalStatus  # ApprovalStatusHelper
from trajlab.db_interface import db_interface
from trajlab.trajlab_constants import IMAGE_ASSETS, IMAGE_EXT, LEN_LONG, LEN_SHORT, TASKS_DIR
from trajlab.utils.file_utils import get_task_file_path, get_tasks, load_task_json_file, truncate_string


def cache_get_tasks(tasks_dir: str = TASKS_DIR) -> list[str]:
    """
    This function uses a cache to store the results of the get_tasks function.
    The cache has a maximum size of 128 entries. If the cache is full, the least recently used entry will be discarded.
    However, we also have the ability to force a redo of the get_tasks function, bypassing the cache.
    """
    return get_tasks(tasks_dir=tasks_dir)


# @lru_cache(maxsize=128)
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


class TaskDirInfo(rx.Base):
    """this is for the buttons on mane page/sidebar"""

    id: str
    short_id: str
    timestamp: str

    status: str
    status_emoji: str = ""

    @classmethod
    def folder_info(cls, folder: Path):
        id = folder.name
        short_id = truncate_string(folder.name, LEN_SHORT, suffix_str="")
        status = ApprovalStatus.get_status(folder.name)
        status_emoji = status.emoji
        # status = ApprovalStatusHelper.get_status(folder.name)
        # status_emoji = ApprovalStatusHelper.get_emoji(status)
        timestamp = datetime.fromtimestamp(folder.stat().st_mtime).strftime("%m-%d %H:%M")
        return cls(id=id, short_id=short_id, status=status, status_emoji=status_emoji, timestamp=timestamp)


class TaskInfo(rx.Base):
    id: str = ""  # = None
    short_id: str = ""  # = None

    timestamp: str = ""  # = None
    timestamp_short: str = ""  # = "None"  # = "None"  # = None

    objective: str = ""
    full_path: str = ""  # None

    # def __init__(self, task_info: dict = None, **kwargs):
    #     super().__init__(**kwargs)

    @classmethod
    def from_json_data(cls, json_data: dict, task_full_path: str = ""):
        return cls(
            id=json_data["id"],
            short_id=json_data["id"][:LEN_SHORT],
            timestamp=json_data["timestamp"],
            timestamp_short=datetime.fromisoformat(json_data["timestamp"]).strftime("%m-%d %H:%M"),
            objective=json_data["objective"],
            full_path=task_full_path,
        )


class StepActionInfo(rx.Base):
    action_idx: int
    action_type: str
    action_value: str

    clean_value: str = None


class TaskStepInfo(rx.Base):
    step_idx: int = 0
    step_id: str = ""
    url: str = ""
    image_path_web: str = ""
    image_path_rel: str = ""
    status: ApprovalStatus = ApprovalStatus.DEFAULT

    actions: list[StepActionInfo] = ""

    short_url: str = ""
    short_id: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class TrajState(rx.State):
    """
    This is the base state class.
    It includes the show_datetime, sort_by, sort_direction, show_task_values, and _tasks attributes.
    It also includes the tasks, task_list_name, toggle_show_task_value, and reload_database methods.
    """

    task: TaskInfo = None  # TaskInfo()

    show_datetime: bool = False
    sort_by: str = "id"
    sort_direction: str = "descending"
    show_task_values: Dict[str, bool] = {
        "approval_status": True,
        "datetime": False,
    }

    _tasks_files: list[Tuple[str, float]] = []  # path/id and mtime
    _clippy: Clippy = None
    clippy_running: bool = False

    task_dirs: list[TaskDirInfo] = []
    current_in_task_dirs: bool = False
    # TASK----
    task_steps: list[TaskStepInfo] = []
    task_step_images: list[Image.Image] = []

    # RUNNING TASK
    running_url: str = "None"
    running_actions: list[str] = []

    # @rx.var
    # def list_task

    @rx.var
    def list_task_dirs(self) -> list[TaskDirInfo]:
        return sorted(
            self.task_dirs, key=lambda v: getattr(v, self.sort_by), reverse=self.sort_direction == "descending"
        )

    @rx.var
    def task_status(self) -> str:
        """
        This method returns the status of the task.
        """
        if self.task:
            return ApprovalStatus.get_status(self.task.id)
        return ApprovalStatus.DEFAULT

    @rx.var
    def task_status_color(self) -> str:
        """
        This method returns the color of the task status.
        """
        # return ApprovalStatusHelper.get_color(self.task_status)
        return self.task_status.color

    @rx.var
    def task_status_emoji(self):
        # return ApprovalStatusHelper.get_emoji(self.task_status)
        return self.task_status.emoji

    @rx.var
    def len_step_images(self) -> int:
        """
        This method returns the number of step images in a task.
        """
        return len(self.task_step_images)

    def goto_page(self, page: str):
        """
        This method redirects to a page.
        """
        return rx.redirect(page)

    def goto_task(self, task_id: str):
        """
        This method loads a task and redirects to the task page.
        """
        # return rx.redirect(f"/task/{task_id}")
        return self.goto_page(f"/task/{task_id}")

    def on_load_task(self) -> None:
        """
        This method checks if a task is loaded.
        If the task is not loaded, it loads the task.
        """
        MenuState.show_task_extra = True
        folder_id = self.get_query_params().get("task_id", "no task id")
        logger.info(f"checking if loaded for task_id: {folder_id}")
        return self.load_task(folder_id=folder_id)

    def reset_task(self):
        self.task = TaskInfo()

    def goto_newtask(self):
        self.reset_task()
        self.on_load_new_task()
        return self.goto_page("/newtask")

    def _make_clippy(self) -> None:
        # HERE IS WHERE WE SHOULD SET ALL THE ARGS FOR CLIPPY FROM THE CONFIG
        # THEY MUST BE SET VIA ENV VARS AS CANNOT PASS ARGS TO reflex
        clippy_kwargs = {
            "task_gen_from": config.task_gen_from,
        }

        logger.info(f"init clippy with kwargs: {clippy_kwargs}")
        self._clippy = Clippy(**clippy_kwargs)

    def check_for_clippy(self) -> None:
        if not self._clippy:
            self._make_clippy()

    def on_load_new_task(self) -> None:
        self.check_for_clippy()

        if not self.task:
            self.task = TaskInfo()

        if not self.task.objective:
            self.generate_new_task()
            logger.info(f"made new task with objective: {self.task.objective}")

    def load_task(self, folder_id: str):
        task_full_path = get_task_file_path(tasks_dir=Path(TASKS_DIR), task_id=folder_id)

        if not Path(task_full_path).exists():
            logger.warning(f"task file does not exist: {task_full_path}")
            yield rx.redirect("/")

        json_data = cache_load_task_json_file(filepath=task_full_path)

        # do this so the actions are cleaned up - NEED TO MOVE AWAY FROM JSON DICT TO USING THIS
        json_data = Task.from_dict(json_data).cleanup().dump()

        self.task = TaskInfo.from_json_data(json_data=json_data, task_full_path=task_full_path)
        # self.task = TaskInfo(
        #     id=json_data["id"],
        #     short_id=json_data["id"][:LEN_SHORT],
        #     timestamp=json_data["timestamp"],
        #     timestamp_short=datetime.fromisoformat(json_data["timestamp"]).strftime("%m-%d %H:%M"),
        #     objective=json_data["objective"],
        #     full_path=task_full_path,
        # )

        self.task_steps = []
        self.task_step_images = []

        for step_idx, step in enumerate(json_data["steps"]):
            step_state = TaskStepInfo(
                step_idx=step_idx,
                step_id=step["id"],
                url=step["url"],
                short_url=truncate_string(step["url"], LEN_LONG),
                short_id=truncate_string(step["id"], LEN_LONG),
                image_path_web=f"{IMAGE_ASSETS}/{self.task.id}/{step['id']}.{IMAGE_EXT}",
                image_path_rel=f"{ROOT_DIR}/data/tasks/{folder_id}/{step['id']}.{IMAGE_EXT}",
                # status=ApprovalStatusHelper.get_status(step["id"]),
                status=ApprovalStatus.get_status(step["id"]),
                actions=[],
            )

            for action_idx, action in enumerate(step["actions"]):
                action_value = "unknown"
                if action_type := action.get("action_type"):
                    if action_type == "click":
                        action_value = f"pos({action['x']},{action['y']})"
                        clean_value = "click @ " + action_value
                    elif action_type in ["type", "enter"]:
                        action_value = action["value"]
                        clean_value = "press enter"
                    elif action_type in ["input"]:
                        action_value = f'"{action["value"]}"'
                        clean_value = "type " + action_value

                    step_state.actions.append(
                        StepActionInfo(
                            action_idx=action_idx,
                            action_type=action_type,
                            action_value=action_value,
                            clean_value=clean_value,
                        )
                    )
                else:
                    logger.debug("DIDNT FIND ACTION_TYPE")

            self.task_steps.append(step_state)
            self.task_step_images.append(Image.open(f"{ROOT_DIR}/data/tasks/{folder_id}/{step['id']}.{IMAGE_EXT}"))

    def read_tasks(self) -> None:
        def filter_task_dir(folder: Path) -> bool:
            if folder.name == "current":
                self.current_in_task_dirs = True
                return False
            return True

        self.task_dirs = [
            TaskDirInfo.folder_info(folder) for folder in get_tasks(tasks_dir=TASKS_DIR) if filter_task_dir(folder)
        ]

        logger.info(f"loaded {len(self.task_dirs)} tasks")

    def toggle_show_task_value(self, property: str) -> None:
        """
        This method toggles the visibility of a task value.
        """
        self.show_task_values[property] = not self.show_task_values[property]

    def reload_database(self) -> None:
        db_interface.reload_database()

    def mock_update_id_status(self, id: str, value: str) -> None:
        logger.info(f"mock update id status: {id} {value}")

    def update_id_status(self, id: str, value: str) -> None:
        db_interface.update_id_status(id, value)

    def remove_id_status(self, id: str) -> None:
        db_interface.remove_obj_id(id)

    def download_task(self, task_id: str) -> rx.event.EventSpec:
        """
        This method creates a tarfile of the data in the task_id folder and downloads it.
        """
        task_dir = f"{TASKS_DATA_DIR}/{task_id}"
        tar_file_name = f"{task_id}.tar.gz"
        rx_file_path = rx.get_asset_path(tar_file_name)

        with tarfile.open(rx_file_path, "w:gz") as tar:
            tar.add(task_dir, arcname=os.path.basename(task_dir))

        logger.info(f"Task data saved to {tar_file_name}")
        yield rx.download(f"/{tar_file_name}", filename=tar_file_name)

    def download_all_tasks(self) -> rx.event.EventSpec:
        """
        This method creates a tarfile of the data in all the directories in TASKS_DATA_DIR except for the dir named 'current' and downloads it.
        """
        tar_file_name = "all_tasks.tar.gz"
        rx_file_path = rx.get_asset_path(tar_file_name)
        with tarfile.open(rx_file_path, "w:gz") as tar:
            for task_dir in os.listdir(TASKS_DATA_DIR):
                if task_dir != "current":
                    tar.add(os.path.join(TASKS_DATA_DIR, task_dir), arcname=task_dir)

        logger.info(f"All tasks data saved to {tar_file_name}")
        yield rx.download(f"/{tar_file_name}", filename=tar_file_name)

    def generate_new_task(self) -> None:
        """
        This method generates a new task.
        """
        self.check_for_clippy()
        self.task.objective = self._clippy._get_random_task()

    def launch_from_step(self, step_id: str):
        """
        This method is a placeholder for launching from a state.
        """
        logger.info(f"should launch from this step {step_id}")

    def toggle_running_new_task(self) -> None:
        self.check_for_clippy()
        yield TrajState.clippy_run_new_task

    def toggle_running_new_task_auto(self) -> None:
        self.check_for_clippy()
        yield TrajState.clippy_run_new_task_auto

        """
        This method starts a new task in the background.
        """

    @rx.background
    async def clippy_run_new_task(self) -> None:
        async def page_change_callback(task: Task, page, **kwargs):
            async with self:
                self.running_url = page.url
                _steps = task.steps[-1]
                _actions = _steps.actions
                logger.info(f"PAGE-CHANGE: {page.url} | PREVIOUS ACTIONS: {_actions}")

        async with self:
            self._clippy.callback_manager.add_callback(callback=page_change_callback, on=Task.page_change_async)
            self._clippy.objective = self.task.objective
            self._clippy.key_exit = False
            await self._clippy.start_capture()
            # self.task.id = self._clippy.task.id

        # wait for the pause event
        await self._clippy.async_tasks["crawler_pause"]

    @rx.background
    async def clippy_run_new_task_auto(self) -> None:
        # start it
        async with self:
            self._clippy.objective = self.task.objective
            self._clippy.key_exit = False
            await self._clippy.start_capture()
            self.task.objective, self.task.id = self._clippy.task.objective, self._clippy.task.id

        # here we are running the clippy auto task
        action: NextAction = await self._clippy.suggest_action()
        logger.info(f"got action: {action}")

        # page = await clippy.start_capture(goto_start_page=True)
        # action = await clippy.suggest_action()

    async def end_new_task(self) -> None:
        """
        This method ends the clippy browser capture in background from clicking a button or similar
        """

        if self._clippy:
            # await self._clippy.crawler.playwright_resume()
            await self._clippy.end_capture()
        logger.info(f"ended task: {self._clippy.objective}")


class TaskState(TrajState):
    show_delete: bool = False
    new_running: bool = False

    objective: str = None

    _running_id: str = None
    _running_url: str = None
    _running_actions: list[str] = []

    @rx.var
    def running_url(self):
        return self._running_url

    @rx.var
    def running_actions(self):
        return self._running_actions

    def delete_task(self, task_id: str):
        """
        This method deletes a task.
        """
        logger.info(f"deleting dir {TASKS_DATA_DIR}/{task_id}")
        shutil.rmtree(f"{TASKS_DATA_DIR}/{task_id}")
        return rx.redirect(f"/")

    def change(self) -> None:
        """
        This method toggles the visibility of the delete button.
        """
        self.show_delete = not (self.show_delete)


class MenuState(TrajState):
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
