from __future__ import annotations

import random
from collections import UserDict, UserList
from pathlib import Path
from typing import Any

from jinja2 import Environment

from clippy.constants import TASK_BANK_DIR

task_base_format = "_base"
word_bank_format = "_bank"


def _process_word_bank(word_bank: str) -> list[str]:
    with open(word_bank) as f:
        words_raw = f.read().splitlines()
    return words_raw


class Words(UserList):
    def __init__(self, words: list[str] = [], word_var: str = None) -> None:
        super().__init__(words)
        self.word_var = word_var

    @classmethod
    def from_file(cls, file: str | Path):
        if isinstance(file, str):
            file = Path(file)

        word_var = file.name.split(word_bank_format)[0]
        return cls(_process_word_bank(file), word_var=word_var)

    def sample(self, seed: int | None = None) -> Any:
        if seed != None:
            return self[seed % len(self)]
        return random.choice(self)


class WordBank(UserDict):
    def __init__(self, _seed: int | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._seed = _seed

    def __getattr__(self, key):
        return self[key].sample(self._seed)


class TaskBankManager:
    def __init__(self, task_bank_dir: str = TASK_BANK_DIR, seed: int | None = None) -> None:
        self.task_bank_dir = task_bank_dir
        self.tasks = []
        self._seed = seed
        self.wordbank = WordBank(self._seed)

    def __len__(self):
        return len(self.tasks)

    def __iter__(self) -> TaskBankManager:
        self._task_iter = iter(self.tasks)
        return self

    def __next__(self):
        task = next(self._task_iter)
        return task.render(wordbank=self.wordbank)

    def process_task_bank(self):
        self._process_word_banks()

        self.task_templates_file = f"{self.task_bank_dir}/task{task_base_format}"
        with open(self.task_templates_file) as f:
            self.tasks_raw = f.read().splitlines()

        self.env = Environment()
        for task in self.tasks_raw:
            template = self.env.from_string(task)
            self.tasks.append(template)

    def _process_word_banks(self) -> None:
        for file in Path(self.task_bank_dir).iterdir():
            if file.name.endswith(word_bank_format):
                words = Words.from_file(file)
                self.wordbank[words.word_var] = words

    def sample(self, idx: int | None = None) -> str:
        if idx is None:
            idx = random.randint(0, len(self.tasks) - 1)

        return self.tasks[idx].render(wordbank=self.wordbank)
