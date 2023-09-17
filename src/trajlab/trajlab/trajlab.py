import reflex as rx

from trajlab.components.common import sidebar, task_button, task_page
from trajlab.state import MenuState, State, Step, Task

# from trajlab.models import Task


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
    )


# Add state and page to the app.
app = rx.App()
app.add_page(index, title="TrajectoryLabeler")
app.add_page(task_page, route=f"task/[task_id]", on_load=Task.is_task_loaded)  # , on_load=Task.load_task)
app.compile()
