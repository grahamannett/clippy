from typing import Optional

import reflex as rx
from clippy.states.states import Task, Step


class Task(Task, rx.Model, table=True):
    id: str