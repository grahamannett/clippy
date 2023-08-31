import random
from pathlib import Path
from itertools import cycle

from jinja2 import Environment

from collections import UserDict, UserList

task_bank_dir = "src/taskgen/wordbank"
task_base_format = "_base"
word_bank_format = "_bank"


def _process_word_bank(word_bank: str) -> list[str]:
    with open(word_bank) as f:
        words_raw = f.read().splitlines()
    return words_raw


class Words(UserList):
    def __init__(self, words: list[str] = [], word_var: str = None):
        super().__init__(words)
        self.word_var = word_var

    def sample(self):
        return random.choice(self)

    @classmethod
    def from_file(cls, file: Path):
        if isinstance(file, str):
            file = Path(file)

        word_var = file.name.split(word_bank_format)[0]
        return cls(_process_word_bank(file), word_var)


class WordBank(UserDict):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def __getattr__(self, key):
        return self[key].sample()


class TaskBankManager:
    def __init__(self, task_bank_dir: str = task_bank_dir):
        self.task_bank_dir = task_bank_dir
        self.tasks = []
        self.wordbank = WordBank()

    def __len__(self):
        return len(self.tasks)

    def __iter__(self):
        self._task_iter = cycle(self.tasks)
        return self

    def __next__(self):
        task = next(self._task_iter)
        return task.render(wordbank=self.wordbank)

    def process_task_bank(self):
        self._process_word_banks()

        self.task_templates_file = f"{self.task_bank_dir}/task{task_base_format}"
        with open(self.task_templates_file) as f:
            tasks_raw = f.read().splitlines()

        self.tasks_raw = tasks_raw

        for task in self.tasks_raw:
            template = Environment().from_string(task)
            self.tasks.append(template)

    def _process_word_banks(self):
        for file in Path(self.task_bank_dir).iterdir():
            if file.name.endswith(word_bank_format):
                words = Words.from_file(file)
                self.wordbank[words.word_var] = words

    def sample(self):
        return random.choice(self.tasks).render(wordbank=self.wordbank)
