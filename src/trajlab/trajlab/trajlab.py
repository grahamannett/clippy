import random
import json
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

import reflex as rx

# from trajlab.models import Task

from trajlab.state import State, MenuState, Task, Step


def header_rows(name: str, value: str) -> rx.Component:
    return rx.hstack(
        rx.text(name),
        rx.spacer(),
        rx.text(value),
    )


def task_header_card() -> rx.Component:
    return rx.card(
        rx.box(
            header_rows("ID:", Task.task_id),
            header_rows("Time Started:", Task.timestamp),
            rx.text(Task.objective),
        ),
        # header=rx.heading("Task", size="lg"),
        footer=rx.heading("Notes", size="sm"),
        # width="800px",
    )


def task_step(step: Step) -> rx.Component:
    return rx.box(
        rx.text("url: ", step.url),
        rx.spacer(),
        rx.text("id: ", step.id),
        rx.markdown("---"),
    )


def task_page() -> rx.Component:
    # return rx.box(
    return rx.flex(
        rx.container(
            task_header_card(),
            rx.responsive_grid(rx.foreach(Task.steps, task_step)),
        ),
        sidebar(show_extra=True),
    )


def task_button(task_name: List) -> rx.Component:
    return rx.box(rx.button(task_name[1], on_click=lambda: Task.goto_task(task_name[0])))


def sidebar(show_extra: bool = False) -> rx.Component:
    return rx.box(
        rx.button("sidebar", on_click=MenuState.right),
        rx.drawer(
            rx.drawer_overlay(
                rx.drawer_content(
                    rx.drawer_header("sidebar options"),
                    rx.drawer_body(
                        rx.accordion(
                            rx.accordion_item(
                                rx.accordion_button(
                                    rx.heading("Tasks"),
                                    rx.accordion_icon(),
                                ),
                                rx.accordion_panel(
                                    rx.foreach(State.tasks, task_button),
                                ),
                            ),
                            allow_toggle=True,
                            width="100%",
                        ),
                        rx.cond(show_extra, rx.text("extra task info"), rx.text("no extra task info")),
                    ),
                    rx.drawer_footer(
                        rx.button(rx.breadcrumb(rx.breadcrumb_item(rx.breadcrumb_link("Home", href="/")))),
                        rx.spacer(),
                        rx.button("Close", on_click=MenuState.right),
                    ),
                    # bg="rgba(0, 0, 0, 0.3)",
                ),
            ),
            on_esc=MenuState.close_drawer,
            is_open=MenuState.show_right,
        ),
    )


def index() -> rx.Component:
    return rx.box(
        # rx.responsive_grid(
        rx.flex(
            rx.spacer(),
            rx.vstack(
                rx.foreach(
                    State.tasks,
                    task_button,
                )
            ),
            rx.spacer(),
            sidebar(),
        )
        # )
    )


# Add state and page to the app.
app = rx.App()
app.add_page(index, title="TrajectoryLabeler")
app.add_page(task_page, route=f"task/[task_id]", on_load=Task.is_task_loaded)  # , on_load=Task.load_task)
app.compile()
