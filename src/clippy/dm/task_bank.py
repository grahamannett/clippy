import random
from pathlib import Path

from clippy.crawler.states.states import Task

task_bank_dir = "clippy/taskgen/"


def _process_word_bank(word_bank: str):
    pass

class WordBank:
    def __init__(self, template_var: str):
        self.template_var = template_var




class WordBanks:
    def __init__(self) -> None:
        pass

class TaskTemplate:
    def __init__(self, objective: str, word_bank: WordBank):
        objective = self.clean_objective(objective)
        self.objective = objective

        self.process_objective()

    def clean_objective(self, objective: str) -> str:
        objective = objective.lstrip("- ")
        return objective

    def process_objective(self):
        # find all
        pattern =

    def sample(self):
        pass


class TaskBankManager:
    task_base_format = "-base"
    word_bank_format = "-bank"

    def __init__(self, task_bank_dir: str = task_bank_dir):
        self.task_bank_dir = task_bank_dir
        self.tasks = []

    def process_task_bank(self):
        with open(f"{self.task_bank_dir}/task{self.task_base_format}") as f:
            tasks_raw = f.read().splitlines()

        # task_templates = []

        # for task in tasks:
        #     task = task.lstrip("- ")
        #     task = TaskTemplate(objective=task)
        #     # task = Task(objective=task)
        #     task_templates.append(task)

        task_templates = [TaskTemplate(task, wb) for task in tasks_raw]

        self.tasks = task_templates

    def _get_word_banks(self):
        for file in Path(self.task_bank_dir).iterdir():
            if file.name.endswith("-bank") and file.name != "task-bank":
                yield _process_word_bank(file)

    def __len__(self):
        return len(self.tasks)

    def sample_task(self):
        return random.choice(self.tasks)
