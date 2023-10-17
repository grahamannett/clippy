import json
import os
from pathlib import Path
from typing import Dict, List

import reflex as rx
from loguru import logger

# from tinydb import TinyDb
from clippy.dm.db_utils import Database as Database
from clippy.run import Clippy
from trajlab.constants import len_long, len_short, tasks_dir, image_type, image_assets

# tasks = [{"name": f.name, "short_name": f.name[:8]} for f in Path(tasks_dir).iterdir() if f.is_dir()]


class State(rx.State):
    """base state."""

    tasks: List[List[str]]
    _db: Database = None

    def load_tasks(self) -> None:
        self.tasks = [[f.name, f.name[:len_short]] for f in Path(tasks_dir).iterdir() if f.is_dir()]
        MenuState.show_task_extra = False
        logger.info(f"loaded {len(self.tasks)} tasks")


class DatabaseInterface(State):
    """
    since DB eventually will move to SQL thing and not TinyDB, this is just so I can keep a database in
    """

    _db: Database = None

    @rx.var
    def do_this(self):
        logger.info("doing this")

    def check_db(self) -> None:
        logger.info(f"checking db... with current task {TaskState.task_id}")
        database_path = "../../data/db/db.json"

        db = Database(database_path)
        breakpoint()

    def approve_task(self, task_id: str) -> None:
        logger.info(f"approving task {task_id}")
        self._db.approve_task(task_id)
        self.load_tasks()
        return rx.redirect("/")


class MenuState(State):
    show_right: bool = False

    show_task_extra: bool = False

    def right(self):
        self.show_right = not (self.show_right)

    def close_drawer(self):
        self.show_right = False


class StepState(State):
    step_id: str = None
    url: str = None
    image_path: str = None

    short_url: str = None
    short_id: str = None

    @classmethod
    def parse_step(cls, step: Dict[str, str], task_id: str):
        short_url = step["url"][:len_long] + "..." if len(step["url"]) > len_long else step["url"]
        short_id = step["id"][:len_long] + "..." if len(step["id"]) > len_long else step["id"]
        image_path = f"{image_assets}/{task_id}/{step['id']}.{image_type}"

        inst = cls(
            step_id=step["id"],
            url=step["url"],
            image_path=image_path,
            short_url=short_url,
            short_id=short_id,
        )
        return inst


class TaskState(State):
    task_id: str = None
    task_id_short: str = None
    objective: str = None
    timestamp: str = None
    _steps: List[Dict[str, str]] = []
    _clippy = None

    full_path: str = None
    # steps: List[Step] = None

    def load_task(self, task_id: str):
        logger.info(f"loading task {task_id}...")
        task_filepath = Path(tasks_dir) / task_id / "task.json"
        self.full_path = str(task_filepath.resolve())
        with open(task_filepath) as f:
            data = json.load(f)
        self.task_id = data["id"]
        self.task_id_short = self.task_id[:len_short]
        self.objective = data["objective"]
        self.timestamp = data["timestamp"]
        self._steps = data["steps"]

    def goto_task(self, task_id: str):
        self.load_task(task_id)
        return rx.redirect(f"/task/{task_id}")

    def is_task_loaded(self):
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
    def len_steps(self) -> int:
        return len(self._steps)

    @rx.var
    def steps(self) -> List[StepState]:
        logger.info(f"parsing {len(self._steps)} steps for task {self.task_id}")
        if self._steps != []:
            return [StepState.parse_step(s, task_id=self.task_id) for s in self._steps]
        return []

    def new_random_task(self) -> None:
        self._clippy = Clippy()
        task = self._clippy._get_random_task()

    def launch_from_state(self, step_id: str):
        logger.info(f"should launch from this state {step_id}")
        # from clippy.run import check_startup, get_args, Clippy, ClippyState

        # check_startup()

        # args = get_args()
        # kwargs = vars(args)
        # clippy = Clippy(**kwargs)
