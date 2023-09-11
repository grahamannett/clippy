import reflex as rx

from trajlab.models import Trajectory, Step
from ..state import State


def show_trajectory_menu_item(trajectory: Trajectory):
    return rx.cond(
        trajectory.uuid,
        rx.hstack(rx.box(trajectory.uuid), rx.button("Load", on_click=lambda: State.get_trajectory(trajectory.uuid))),
        rx.text("None"),
    )


def trajectory_page() -> rx.Component:
    return rx.vstack(
        rx.cond(
            State.trajectory,
            rx.text("FFF" + State.trajectory_id),
            rx.text("No trajectory loaded"),
        )
    )
