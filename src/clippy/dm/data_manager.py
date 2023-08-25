import json
import os
import shutil

from clippy.states import Task


class DataManager:
    """this is for managing all the trajectories as eventually they need to be sql type to work with pynecone"""

    def __init__(self, data_dir: str = "data/tasks"):
        self.data_dir = data_dir
        self.tasks = []

        # self.curr_task_output = f"{self.data_dir}/current"
        self._clear_on_start = True

    @property
    def curr_task_output(self):
        return f"{self.data_dir}/current"

    def capture_start(self):
        if self._clear_on_start:
            self.clear_current()

    def clear_current(self):
        if os.path.exists(self.curr_task_output):
            shutil.rmtree(self.curr_task_output)
        os.makedirs(self.curr_task_output, exist_ok=True)

    def page_path(self, str):
        pass

    def migrate_data(self, move_current: bool = False, override: bool = False):
        migration_dir = f"data/migrate"
        for folder in os.listdir(self.data_dir):
            # by default dont move current
            if "current" in folder and not move_current:
                continue

            if os.path.exists(f"{migration_dir}/{folder}"):
                print(f"overwrriting `{folder}` in `{migration_dir}` file")
                if not override:
                    confirm_override = input("press c/y: ")
                    if confirm_override.lower() not in ["c", "y"]:
                        breakpoint()

                shutil.rmtree(f"{migration_dir}/{folder}")

            shutil.move(
                f"{self.data_dir}/{folder}",
                migration_dir,
            )

    def load(self):
        for folder in os.listdir(self.data_dir):
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
        task_file = f"{self.data_dir}/{folder}/task.json"
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

    def dump_task(self, task: Task):
        task_file = f"{self.curr_task_output}/task.json"
        json_data = task.dump()
        with open(task_file, "w") as f:
            json.dump(json_data, f, indent=4)

    def save(self, task: Task):
        # dump task to current/task.json
        self.dump_task(task)
        folder = self.get_folder(task)

        shutil.copytree(self.curr_task_output, folder)
        print("saved data manager... ")

    def get_folder(self, task: Task):
        """need some generic way to get the folder so make it a func for now
        possible i want to save tasks in a different way later maybe shorter uuid
        """
        folder = task.id

        return f"{self.data_dir}/{folder}"


class TaskRetriever:
    """use this for retrieving similar trajectories"""

    def __init__(self, dm: DataManager):
        self.dm = dm

    # def make_embedding(self, task: Task, stub: StubTemplates):
    #     text = StubTemplates.
