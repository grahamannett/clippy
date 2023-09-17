from typing import List

import reflex as rx

from trajlab.state import MenuState, State, Step, Task

# TASK --


def task_header_card() -> rx.Component:
    return rx.card(
        rx.box(
            header_rows("ID:", Task.task_id),
            header_rows("Time Started:", Task.timestamp),
            rx.spacer(),
            rx.text(Task.objective),
        ),
        # header=rx.heading("Task", size="lg"),
        footer=rx.heading("Notes", size="sm"),
        # width="800px",
    )


def task_step(step: Step) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.spacer(),
            rx.hstack(
                rx.text("url: "),
                rx.link(step.short_url, href=step.url),
            ),
            rx.spacer(),
            rx.text("id: ", step.short_id),
            rx.image(src=step.image_path, width="auto", height="500px"),
            rx.spacer(),
            rx.link("Start from here", href="/"),
            # rx.spacer(),
            rx.divider(border_color="black"),
            align_items="left",
        ),
    )


def task_page() -> rx.Component:
    return rx.flex(
        rx.container(
            task_header_card(),
            rx.responsive_grid(rx.foreach(Task.steps, task_step)),
        ),
        sidebar(show_task_sidebar=True),
    )


def task_button(task_name: List) -> rx.Component:
    return rx.box(rx.button(task_name[1], on_click=lambda: Task.goto_task(task_name[0])))


def task_sidebar(show_task_sidebar: bool = False) -> rx.Component:
    return (rx.cond(show_task_sidebar, rx.text("extra task info"), rx.text("no extra task info")),)


# COMMON --


def header_rows(name: str, value: str) -> rx.Component:
    return rx.hstack(
        rx.text(name),
        rx.spacer(),
        rx.text(value),
    )


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
                        rx.button(rx.breadcrumb(rx.breadcrumb_item(rx.breadcrumb_link("Home", href="/")))),
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
