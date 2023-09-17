import json
import os
from pathlib import Path
from typing import Dict, List

import reflex as rx
from loguru import logger

from trajlab.constants import len_long, len_short, tasks_dir, image_type, image_assets

# tasks = [{"name": f.name, "short_name": f.name[:8]} for f in Path(tasks_dir).iterdir() if f.is_dir()]


class State(rx.State):
    """base state."""

    tasks: List[List[str]]

    @rx.var
    def get_tasks(self) -> List[List[str]]:
        MenuState.show_task_extra = False
        self.tasks = [[f.name, f.name[:len_short]] for f in Path(tasks_dir).iterdir() if f.is_dir()]
        logger.info(f"loaded {len(self.tasks)} tasks")
        return self.tasks


class MenuState(State):
    show_right: bool = False

    show_task_extra: bool = False

    def right(self):
        self.show_right = not (self.show_right)

    def close_drawer(self):
        self.show_right = False


class Step(State):
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
        # abs_image_path = (Path(tasks_dir) / task_id / step["id"]).with_suffix(f".{image_type}")
        # sym_image_path = Path(f"trajlab/{image_assets}/{str(abs_image_path.name)}").resolve()

        # if not sym_image_path.exists():
        #     os.symlink(str(abs_image_path.resolve()), sym_image_path)

        inst = cls(
            step_id=step["id"],
            url=step["url"],
            image_path=image_path,
            short_url=short_url,
            short_id=short_id,
        )
        return inst


class Task(State):
    task_id: str = None
    task_id_short: str = None
    objective: str = None
    timestamp: str = None
    _steps: List[Dict[str, str]] = []
    # steps: List[Step] = None

    def load_task(self, task_id: str):
        logger.info(f"loading task {task_id}...")
        task_filepath = Path(tasks_dir) / task_id / "task.json"
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
    def steps(self) -> List[Step]:
        logger.info(f"parsing {len(self._steps)} steps for task {self.task_id}")
        if self._steps != []:
            return [Step.parse_step(s, task_id=self.task_id) for s in self._steps]
        return []
