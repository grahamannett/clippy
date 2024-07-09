import reflex as rx

from trajlab.trajlab_state import MenuState, TrajState
from trajlab.pages import index, new_task, task_page


@rx.page(route="health")
def new_val():
    return rx.text("okay")


app = rx.App()
app.add_page(
    index,
    title="TrajectoryLabeler",
    on_load=TrajState.read_tasks(),
)
app.add_page(
    task_page,
    route="task/[task_id]",
    on_load=[TrajState.on_load_task, MenuState.set_show_task_extra(False)],
)
app.add_page(
    new_task,
    route="newtask",
    on_load=TrajState.on_load_new_task,
)
