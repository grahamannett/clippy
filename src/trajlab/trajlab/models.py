from typing import Optional

import reflex as rx

# from clippy.states.states import Task, Step


# class Task(Task, rx.Model, table=True):
class TrackedTask(rx.Model, table=True):
    name: str
