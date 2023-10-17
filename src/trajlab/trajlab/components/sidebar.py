from typing import List

import reflex as rx

from trajlab.state import DatabaseInterface, MenuState, State, TaskState


def task_button(task_name: List) -> rx.Component:
    return rx.box(rx.button(task_name[1], on_click=lambda: TaskState.goto_task(task_name[0])))


def sidebar(show_task_sidebar: bool = False) -> rx.Component:
    return rx.box(
        rx.button("sidebar", on_click=MenuState.right),
        rx.drawer(
            rx.drawer_overlay(
                rx.drawer_content(
                    rx.drawer_header("sidebar options"),
                    rx.drawer_body(
                        rx.accordion(
                            # show options for viewing task info
                            rx.cond(show_task_sidebar, rx.text("extra task info"), None),
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
                        # rx.button(rx.breadcrumb(rx.breadcrumb_item(rx.breadcrumb_link("Home", href="/")))),
                        rx.link(
                            rx.button("Home"),
                            href="/",
                            color="rgb(107,99,246)",
                            button=True,
                            on_click=MenuState.close_drawer,
                        ),
                        # rx.breadcrumb(rx.breadcrumb_item(rx.breadcrumb_link("Home", href="/"))),
                        # on_click=MenuState.close_drawer,
                        rx.spacer(),
                        rx.button("DB", on_click=DatabaseInterface.check_db),
                        rx.spacer(),
                        rx.button("Close", on_click=MenuState.right),
                    ),
                    # bg="rgba(100, 0.7, 0.7, 0.0)",  # bg="rgba(0, 0, 0, 0.3)",
                ),
            ),
            on_esc=MenuState.close_drawer,
            is_open=MenuState.show_right,
        ),
    )
