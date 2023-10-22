import reflex as rx

from trajlab.state import TaskState
from trajlab.components.sidebar import sidebar


def new_task():
    return rx.grid(
        rx.box(
            rx.vstack(
                rx.spacer(),
                rx.button("Different Task", on_click=TaskState.generate_new_task),
                rx.button("Start Task", on_click=TaskState.start_new_task),
                rx.button("End Task", on_click=TaskState.end_new_task),
            ),
        ),
        rx.vstack(
            rx.hstack(rx.text("New Task Page:"), rx.text(TaskState.objective)),
            rx.spacer(),
        ),
        rx.box(sidebar(), position="absolute", right="0px"),
        grid_template_columns="1fr 2fr 1fr",
    )
