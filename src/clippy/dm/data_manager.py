import json
import os
import shutil
from asyncio import iscoroutine
from pathlib import Path

from loguru import logger

from clippy.dm.db_utils import Database
from clippy.states import Task
from clippy.utils._input import _get_input


def confirm_override(func):
    def wrapper(*args, **kwargs):
        if kwargs.get("override", False):
            logger.info("override set, skipping confirm")
            return func(*args, **kwargs)

        confirm_input = _get_input(f"confirm action for {func.__name__}. Press c/y to confirm or n to skip: ")

        if confirm_input.lower() in ["n", "no"]:
            logger.info(f"skipping... {func.__name__}")
            return
        elif confirm_input.lower() not in ["c", "y"]:
            # allow breakpoint for debugger to inspect
            breakpoint()
        return func(*args, **kwargs)

    return wrapper


class DataManager:
    """this is for managing all the trajectories as eventually they need to be sql type to work with pynecone"""

    _task: Task
    tasks: list[Task] = []

    db: Database

    def __init__(self, task_data_dir: Path | str, database_path: Path | str | None = None):
        self.task_data_dir: Path = Path(task_data_dir)
        self._clear_on_start = True

        if database_path is not None:
            self.database_path: Path = Path(database_path)
            self.db = Database(database_path)

    @staticmethod
    def create_task(**kwargs) -> Task:
        return Task(**kwargs)

    """RUN COMMANDS:
    --- TASKS FOLDER
    - migrate: move all data to migrate folder

    --- DB JSON
    - drop_table: drops table from db
    - drop_last: drops last from table from db
    """

    async def run(self, subcmd: str, **kwargs) -> None:
        func = {
            "migrate": self.migrate_data,
            # db related
            "drop_last": self.drop_last,
            "drop_table": self.drop_table,
        }.get(subcmd, None)

        if func is None:
            raise Exception(f"`{subcmd}` not supported in {self.__class__.__name__}")

        if iscoroutine(output := func(**kwargs)):
            await output

        return output

    @property
    def task(self) -> Task:
        return self.tasks[-1]

    @property
    def curr_task_output(self) -> str:
        return f"{self.task_data_dir}/current"

    def capture_task(self, task: Task) -> None:
        self.tasks.append(task)
        self._task = task

    def capture_start(self):
        if self._clear_on_start:
            self.clear_current()

    def clear_current(self):
        if os.path.exists(self.curr_task_output):
            shutil.rmtree(self.curr_task_output)
        os.makedirs(self.curr_task_output, exist_ok=True)

    def page_path(self, str):
        pass

    def migrate_data(self, move_current: bool = False, override: bool = False, **kwargs) -> None:
        migration_dir = f"data/migrate"
        for folder in os.listdir(self.task_data_dir):
            # by default dont move current
            if "current" in folder and not move_current:
                logger.info("skipping current folder...")
                continue

            if os.path.exists(f"{migration_dir}/{folder}"):
                logger.info(f"overwrriting `{folder}` in `{migration_dir}` file")
                if not override:
                    confirm_override = input("press c/y: ")
                    if confirm_override.lower() not in ["c", "y"]:
                        breakpoint()

                shutil.rmtree(f"{migration_dir}/{folder}")

            logger.info(f"moving `{self.task_data_dir}/{folder}` to `{migration_dir}`")
            shutil.move(
                f"{self.task_data_dir}/{folder}",
                migration_dir,
            )

    def load(self):
        for folder in os.listdir(self.task_data_dir):
            try:
                task = self.read_folder(folder)
                # check task somehow
                if self.check_task(task):
                    self.tasks.append(task)
            except FileNotFoundError:
                print(
                    f"somethingwrong with folder:{folder}... not adding to tasks",
                )

    def read_folder(self, folder: str) -> Task:
        task_file = f"{self.task_data_dir}/{folder}/task.json"
        with open(task_file, "r") as f:
            task = json.load(f)

        task = Task.from_dict(task)
        return task

    def check_task(self, task: Task, skip_empty: bool = False) -> bool:
        if task.objective is None:
            return False
        if (len(task.steps) == 0) and skip_empty:
            return False

        return True

    def dump_task(self, task: Task) -> None:
        task_file = f"{self.curr_task_output}/task.json"
        json_data = task.dump()
        with open(task_file, "w") as f:
            json.dump(json_data, f, indent=4)

    def save(self, task: Task | None = None) -> None:
        task = task or self.task

        # dump task to current/task.json - this is the
        self.dump_task(task)
        folder = self.get_folder(task)
        shutil.copytree(self.curr_task_output, folder)

        if isinstance(self.db, Database):
            self.db.save_dataclass(task)

    def get_folder(self, task: Task):
        """need some generic way to get the folder so make it a func for now
        possible i want to save tasks in a different way later maybe shorter uuid
        """

        return self.task_data_dir / task.id

    @confirm_override
    def drop_last(self, table: str, **kwargs) -> None:
        doc_ids = [item.doc_id for item in self.db.table(table).all()]
        dropped_element = self.db.table(table).remove(doc_ids=doc_ids)
        logger.info(f"dropped doc: {dropped_element}")

    @confirm_override
    def drop_table(self, table: str, droplast: bool = False, **kwargs) -> None:
        self.db.drop(table)


class TaskRetriever:
    """use this for retrieving similar trajectories"""

    def __init__(self, dm: DataManager):
        self.dm = dm
