import reflex as rx

from trajlab.state import State, TaskState, TaskValuesDict


def task_button_datetime(time_str: str) -> rx.Component:
    """Creates a button with the task's datetime."""
    return rx.container(rx.spacer(), rx.text(f"[{time_str}]"))


def task_button_approval_status(approval_status: str) -> rx.Component:
    """Creates a button with the task's approval status."""
    return rx.container(rx.text(f"{approval_status}"))


def task_button(task_values: TaskValuesDict) -> rx.Component:
    """Creates a button for a task with optional datetime and approval status."""
    return rx.box(
        rx.button(
            rx.text(task_values["short_id"]),
            rx.cond(
                State.show_task_values["approval_status"] & task_values["clean_status"],
                task_button_approval_status(task_values["clean_status"]),
                None,
            ),
            rx.cond(State.show_task_values["datetime"], task_button_datetime(task_values["datetime"]), None),
            on_click=lambda: TaskState.goto_task(task_values["id"]),
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


def header_rows(name: str, value: str, **kwargs) -> rx.Component:
    """Creates a row with a name and a value."""
    return rx.hstack(
        rx.text(name),
        rx.spacer(),
        rx.text(value, **kwargs),
    )
