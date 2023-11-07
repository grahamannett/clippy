import reflex as rx

from trajlab.trajlab_state import TrajState, TaskDirInfo


def task_button_datetime(time_str: str) -> rx.Component:
    """Creates a button with the task's datetime."""
    return rx.container(rx.spacer(), rx.text(f"[{time_str}]"))


def task_button_approval_status(approval_status: str) -> rx.Component:
    """Creates a button with the task's approval status."""
    return rx.container(rx.text(f"{approval_status}"))


def task_button(task_dir_info: TaskDirInfo) -> rx.Component:
    """Creates a button for a task with optional datetime and approval status."""
    return rx.box(
        rx.button(
            rx.text(task_dir_info.short_id),
            rx.cond(
                TrajState.show_task_values["approval_status"],
                task_button_approval_status(task_dir_info.status_emoji),
                None,
            ),
            rx.cond(TrajState.show_task_values["datetime"], task_button_datetime(task_dir_info.timestamp), None),
            on_click=lambda: TrajState.goto_task(task_dir_info.id),
        )
    )


# general


def container(*children, **props):
    """A fixed container based on a 960px grid."""
    # Enable override of default props.
    props = (
        dict(
            width="100%",
            max_width="960px",
            bg="white",
            h="100%",
            px=[4, 12],
            margin="0 auto",
            position="relative",
        )
        | props
    )
    return rx.box(*children, **props)


# COMMON --
