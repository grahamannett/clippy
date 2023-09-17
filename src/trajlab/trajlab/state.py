from typing import Dict, List
from pathlib import Path
import json

import reflex as rx

from trajlab.constants import tasks_dir, len_short

# tasks = [{"name": f.name, "short_name": f.name[:8]} for f in Path(tasks_dir).iterdir() if f.is_dir()]


class State(rx.State):
    """base state."""

    # tasks: List[List[str]] = [[f.name, f.name[:len_short]] for f in Path(tasks_dir).iterdir() if f.is_dir()]
    tasks: List[List[str]]

    @rx.var
    def get_tasks(self) -> List[List[str]]:
        MenuState.show_task_extra = False
        self.tasks = [[f.name, f.name[:len_short]] for f in Path(tasks_dir).iterdir() if f.is_dir()]
        return self.tasks


class MenuState(State):
    show_right: bool = False

    show_task_extra: bool = False

    def right(self):
        self.show_right = not (self.show_right)

    def close_drawer(self):
        self.show_right = False


class Step(State):
    url: str = None
    id: str = None


class Task(State):
    task_id: str = None
    task_id_short: str = None
    objective: str = None
    timestamp: str = None
    _steps: List[Dict[str, str]] = None
    # steps: List[Step] = None

    def load_task(self, task_id: str):
        task_filepath = Path(tasks_dir) / task_id / "task.json"
        with open(task_filepath) as f:
            data = json.load(f)
        self.task_id = data["id"]
        self.task_id_short = self.task_id[:len_short]
        self.objective = data["objective"]
        self.timestamp = data["timestamp"]
        self._steps = data["steps"]
        # self.steps = [Step(url=s["url"], id=s["id"]) for s in data["steps"]]

    def goto_task(self, task_id: str):
        self.load_task(task_id)
        return rx.redirect(f"/task/{task_id}")

    def is_task_loaded(self):
        MenuState.show_task_extra = True
        task_id = self.get_query_params().get("task_id", "no task id")

        # im not sure exactly when either of these happen, i.e. when is self.task_id set but query params not and vice versa
        if self.task_id and (self.objective is None):
            print("task_id is set but no objective")
            self.load_task(self.task_id)
        elif task_id != "no task id":
            self.load_task(task_id)

    @rx.var
    def steps(self) -> List[Step]:
        if self._steps:
            return [Step(url=s["url"], id=s["id"]) for s in self._steps]
        return []
