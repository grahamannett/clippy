import reflex as rx

from trajlab.components.common import task_page
from trajlab.components.sidebar import sidebar, task_button
from trajlab.state import MenuState, State, StepState, TaskState

# from trajlab.models import Task


def index() -> rx.Component:
    return rx.box(
        # rx.responsive_grid(
        rx.flex(
            rx.spacer(),
            rx.button("New Task (random)", on_click=TaskState.new_random_task),
            rx.vstack(
                rx.foreach(
                    State.tasks,
                    task_button,
                )
            ),
            rx.spacer(),
            sidebar(),
        )
    )


# Add state and page to the app.
app = rx.App()
app.add_page(index, title="TrajectoryLabeler", on_load=State.load_tasks)
app.add_page(task_page, route=f"task/[task_id]", on_load=TaskState.is_task_loaded)  # , on_load=Task.load_task)
app.compile()
