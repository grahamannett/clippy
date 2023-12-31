import json
import os
import shutil
from asyncio import iscoroutine
from pathlib import Path

from clippy import logger
from clippy.constants import MIGRATION_DIR
from clippy.dm.data_manager_utils import confirm_override
from clippy.dm.db_utils import Database
from clippy.states import Task


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
        if not self.tasks:
            return None

        return self.tasks[-1]

    @property
    def curr_task_output(self) -> str:
        return f"{self.task_data_dir}/current"

    def get_curr_step_screenshot_path(self) -> str:
        return f"{self.curr_task_output}/{self.task.current.id}.png"

    def capture_task(self, task: Task) -> None:
        self.capture_start()
        self.tasks.append(task)
        self._task = task

    def capture_start(self):
        if self._clear_on_start:
            self.clear_current()

    def clear_current(self):
        logger.info("check if clear current")
        if os.path.exists(self.curr_task_output):
            logger.info("should clear current dir")
            shutil.rmtree(self.curr_task_output)
        os.makedirs(self.curr_task_output, exist_ok=True)

    def page_path(self, str):
        pass

    def migrate_data(self, move_current: bool = False, override: bool = False, **kwargs) -> None:
        for folder in os.listdir(self.task_data_dir):
            # by default dont move current
            if "current" in folder and not move_current:
                logger.info("skipping current folder...")
                continue

            if os.path.exists(f"{MIGRATION_DIR}/{folder}"):
                logger.info(f"overwrriting `{folder}` in `{MIGRATION_DIR}` file")
                if not override:
                    confirm_override = input("press c/y: ")
                    if confirm_override.lower() not in ["c", "y"]:
                        breakpoint()

                shutil.rmtree(f"{MIGRATION_DIR}/{folder}")

            logger.info(f"moving `{self.task_data_dir}/{folder}` to `{MIGRATION_DIR}`")
            shutil.move(
                f"{self.task_data_dir}/{folder}",
                MIGRATION_DIR,
            )

    def load(self):
        """load all tasks from task_data_dir"""
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
        cleaned_task = task.cleanup()
        json_data = cleaned_task.dump()
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

    def get_folder(self, task: Task) -> Path:
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
