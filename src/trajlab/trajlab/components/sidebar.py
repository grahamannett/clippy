from typing import List

import reflex as rx

from trajlab.components.common import task_button
from trajlab.state import MenuState, State


# def sidebar(children: bool = False) -> rx.Component:
def sidebar(*children: List[rx.Component]) -> rx.Component:
    return rx.box(
        rx.button("sidebar", on_click=MenuState.right),
        rx.drawer(
            rx.drawer_overlay(
                rx.drawer_content(
                    rx.drawer_header("sidebar options"),
                    rx.drawer_body(
                        rx.accordion(
                            # show options for viewing task info
                            # rx.cond(show_task_sidebar, sidebar_extra_task_info(), None),
                            rx.cond(len(children) > 0, rx.container(*children), None),
                            # show list of tasks
                            rx.accordion_item(
                                rx.accordion_button(
                                    rx.heading("Tasks"),
                                    rx.accordion_icon(),
                                ),
                                rx.accordion_panel(
                                    rx.foreach(State.tasks, task_button),
                                ),
                            ),
                            allow_toggle=True,
                            width="100%",
                        ),
                    ),
                    rx.drawer_footer(
                        rx.link(
                            rx.button("Home"),
                            href="/",
                            color="rgb(107,99,246)",
                            button=True,
                            on_click=MenuState.close_drawer,
                        ),
                        # on_click=MenuState.close_drawer,
                        rx.spacer(),
                        rx.button("🔄 DB File", on_click=State.reload_database),
                        rx.spacer(),
                        rx.button("Close", on_click=MenuState.right),
                    ),
                    # bg="rgba(100, 0.7, 0.7, 0.0)",  # bg="rgba(0, 0, 0, 0.3)",
                ),
            ),
            on_esc=MenuState.close_drawer,
            is_open=MenuState.show_right,
            size="sm",
        ),
    )
