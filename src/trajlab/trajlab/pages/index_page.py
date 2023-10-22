import reflex as rx

from trajlab.components.common import task_button
from trajlab.components.sidebar import sidebar
from trajlab.constants import sort_options, default_sort_by
from trajlab.state import State, TaskState, TaskValuesDict


def index_extra_show_task_options() -> rx.Component:
    """
    This function creates a component that allows the user to toggle the visibility of task details.
    """
    return rx.vstack(
        rx.container(
            rx.hstack(
                rx.heading("Show Details", size="sm"),
                rx.checkbox(
                    "Datetime",
                    is_checked=State.show_task_values["datetime"],
                    on_change=lambda value: State.toggle_show_task_value("datetime", value),
                ),
                rx.checkbox(
                    "Approval Status",
                    is_checked=State.show_task_values["approval_status"],
                    on_change=lambda value: State.toggle_show_task_value("approval_status", value),
                ),
            )
        )
    )


def index_extra_sidebar() -> rx.Component:
    """
    This function creates a sidebar component that includes sorting options and task detail visibility toggles.
    """
    return rx.vstack(
        rx.container(
            rx.hstack(
                rx.heading("Sort By", size="sm"),
                rx.select(sort_options, default_value=default_sort_by, on_change=State.set_sort_by),
                rx.select(
                    ["ascending", "descending"],
                    default_value="Ascending",
                    on_change=lambda sort_direction: State.set_sort_direction(sort_direction),
                ),
            )
        ),
        index_extra_show_task_options(),
    )


def index() -> rx.Component:
    """
    This function creates the main component of the index page. It includes a button to create a new task,
    a list of existing tasks, and a sidebar with additional options.
    """
    return rx.box(
        rx.flex(
            rx.spacer(),
            rx.vstack(
                rx.button("New Task (random)", on_click=TaskState.initiate_new_random_task),
                rx.divider(border_color="black"),
                rx.foreach(
                    State.tasks,
                    task_button,
                ),
            ),
            rx.spacer(),
            sidebar(index_extra_sidebar()),
        )
    )