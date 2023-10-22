import reflex as rx

from trajlab.state import MenuState, State, StepState, TaskState
from trajlab.pages import index, new_task, task_page

# from trajlab.models import Task


# Add state and page to the app.
app = rx.App()
app.add_page(index, title="TrajectoryLabeler")
app.add_page(
    task_page,
    route=f"task/[task_id]",
    on_load=[TaskState.is_task_loaded, MenuState.set_show_task_extra(False)],
)
app.add_page(new_task, route="newtask", on_load=TaskState.new_task_on_load)
app.compile()
