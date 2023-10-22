import reflex as rx

from trajlab.components.common import header_rows
from trajlab.components.sidebar import sidebar
from trajlab.state import StepState, TaskState


# TASK --
# def sidebar_extra_task_info() -> rx.Component:
def task_sidebar_extra() -> rx.Component:
    return rx.vstack(
        rx.cond(
            TaskState.status != "pending", rx.button("Remove Task Status", on_click=TaskState.remove_task_status), None
        ),
        rx.spacer(),
    )


def task_header_card() -> rx.Component:
    return rx.card(
        rx.box(
            header_rows("ID:", TaskState.task_id),
            header_rows("Time Started:", TaskState.timestamp),
            header_rows("Status:", TaskState.status, color=TaskState.task_status_color),
            rx.spacer(),
            rx.text(TaskState.objective),
            rx.text(TaskState.full_path),
            rx.spacer(),
            rx.divider(border_color="black"),
            rx.spacer(),
            rx.hstack(
                rx.button(rx.heading("Approve", size="lg", color="green"), on_click=TaskState.approve_task),
                rx.spacer(),
                rx.button(rx.heading("Reject", size="lg", color="red"), on_click=TaskState.reject_task),
            ),
        ),
        footer=rx.heading("Notes", size="sm"),
    )


def task_step(step: StepState) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.spacer(),
            rx.hstack(
                rx.text("url: "),
                rx.link(step.short_url, href=step.url),
            ),
            rx.spacer(),
            rx.text("id: ", step.short_id),
            rx.hstack(
                rx.button(rx.heading("Approve", size="sm", color="green"), on_click=StepState.approve_step),
                rx.spacer(),
                rx.button(rx.heading("Reject", size="sm", color="red"), on_click=StepState.reject_step),
            ),
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
        sidebar(task_sidebar_extra()),
    )
