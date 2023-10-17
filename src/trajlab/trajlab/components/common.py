import reflex as rx

from trajlab.state import MenuState, State, StepState, TaskState
from trajlab.components.sidebar import sidebar

# TASK --


def task_header_card() -> rx.Component:
    return rx.card(
        rx.box(
            header_rows("ID:", TaskState.task_id),
            header_rows("Time Started:", TaskState.timestamp),
            rx.spacer(),
            rx.text(TaskState.objective),
            rx.text(TaskState.full_path),
        ),
        # header=rx.heading("Task", size="lg"),
        footer=rx.heading("Notes", size="sm"),
        # width="800px",
    )


def task_step(step: Step) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.spacer(),
            rx.hstack(
                rx.text("url: "),
                rx.link(step.short_url, href=step.url),
            ),
            rx.spacer(),
            rx.text("id: ", step.short_id),
            rx.center(
                rx.image(src=step.image_path, width="500px", height="auto"),
            ),
            rx.spacer(),
            rx.link("Goto page", color="darkblue", href=step.url),
            rx.link("Launch Clippy Here", color="darkblue", on_click=lambda: TaskState.launch_from_state(step.step_id)),
            rx.divider(border_color="black"),
            align_items="left",
        ),
    )


def task_page() -> rx.Component:
    return rx.flex(
        rx.container(
            task_header_card(),
            rx.responsive_grid(rx.foreach(TaskState.steps, task_step)),
        ),
        sidebar(show_task_sidebar=True),
    )


def task_sidebar(show_task_sidebar: bool = False) -> rx.Component:
    return (rx.cond(show_task_sidebar, rx.text("extra task info"), rx.text("no extra task info")),)


# COMMON --


def header_rows(name: str, value: str) -> rx.Component:
    return rx.hstack(
        rx.text(name),
        rx.spacer(),
        rx.text(value),
    )
