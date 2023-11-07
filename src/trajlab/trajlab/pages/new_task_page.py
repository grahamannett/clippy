import reflex as rx

from trajlab.components.sidebar import sidebar
from trajlab.trajlab_state import TrajState


def running_new_task() -> rx.Component:
    return rx.container(
        rx.cond(
            TrajState.running_url,
            rx.container(
                rx.text("Current URL: " + TrajState.running_url),
                rx.foreach(TrajState.running_actions, rx.text),
            ),
            rx.text("No task running"),
        )
    )


def new_task():
    return rx.grid(
        rx.box(
            rx.vstack(
                rx.spacer(),
                rx.button("Different Task", on_click=TrajState.generate_new_task),
                rx.button("Start Task", on_click=TrajState.toggle_running_new_task),
                rx.button("Start auto", on_click=TrajState.toggle_running_new_task_auto),
                rx.button("End Task", on_click=TrajState.end_new_task),
                rx.divider(border_color="black"),
                # rx.button("Clippy do task", on_click=TaskState.clippy_do_task),
            ),
        ),
        rx.vstack(
            rx.hstack(rx.text("New Task Page:"), rx.text(TrajState.task.objective)), rx.spacer(), running_new_task()
        ),
        rx.box(sidebar(), position="absolute", right="0px"),
        grid_template_columns="1fr 2fr 1fr",
    )
