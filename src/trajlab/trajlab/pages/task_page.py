import reflex as rx

from trajlab.approval_status import ApprovalStatus
from trajlab.components.sidebar import sidebar
from trajlab.trajlab_state import TrajState, TaskStepInfo, TaskState


# TASK --
# def sidebar_extra_task_info() -> rx.Component:
def task_sidebar_extra() -> rx.Component:
    return rx.vstack(
        rx.cond(
            TrajState.task_status != "pending",
            rx.button(
                "Remove Task Status",
                # on_click=TaskState.remove_id(TaskState.task_id),
            ),
            None,
        ),
        rx.spacer(),
    )


def task_header_rows(name: str, value: str, **kwargs) -> rx.Component:
    """Creates a row with a name and a value."""
    return rx.hstack(
        rx.text(name),
        rx.spacer(),
        rx.text(value, **kwargs),
    )


def delete_task_button() -> rx.Component:
    return rx.box(
        rx.button("Delete", on_click=TaskState.change, color="darkorange"),
        rx.alert_dialog(
            rx.alert_dialog_overlay(
                rx.alert_dialog_content(
                    rx.alert_dialog_header("Confirm"),
                    rx.alert_dialog_body("you sure you would like to delete task?"),
                    rx.alert_dialog_footer(
                        rx.button(
                            "Delete",
                            on_click=TaskState.delete_task(TrajState.task.id),
                            color="red",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Cancel",
                            on_click=TaskState.change,
                        ),
                    ),
                )
            ),
            is_open=TaskState.show_delete,
        ),
    )


def task_header_card() -> rx.Component:
    return rx.card(
        rx.box(
            rx.accordion(
                rx.accordion_item(
                    rx.accordion_button(
                        rx.heading(
                            TrajState.task_status, TrajState.task_status_emoji, color=TrajState.task_status_color
                        ),
                        rx.accordion_icon(),
                    ),
                    rx.accordion_panel(
                        task_header_rows("ID:", TrajState.task.id, as_="b"),
                        task_header_rows("Time Started:", "🕰️ " + TrajState.task.timestamp_short, as_="b"),
                        rx.text(TrajState.task.full_path, as_="sm"),
                    ),
                ),
                allow_toggle=True,
            ),
            rx.spacer(),
            rx.divider(border_color="black"),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.heading("Approve", size="lg", color="green"),
                    on_click=lambda: TrajState.update_id_status(TrajState.task.id, ApprovalStatus.APPROVED.value),
                ),
                rx.button(
                    rx.heading("Reject", size="lg", color="red"),
                    on_click=lambda: TrajState.update_id_status(TrajState.task.id, ApprovalStatus.REJECTED.value),
                ),
                rx.spacer(),
                rx.button(
                    rx.heading("Download", size="sm", color="blue"),
                    on_click=lambda: TrajState.download_task(TrajState.task.id),
                ),
                rx.divider(orientation="vertical", border_color="black"),
                rx.spacer(),
                rx.button(
                    rx.heading("Reset Status", size="sm", color="orange"),
                    on_click=lambda: TrajState.remove_id_status(TrajState.task.id),
                ),
                delete_task_button(),
            ),
        ),
        header=rx.heading(TrajState.task.objective),
        width="130%",
    )


def task_step(step: TaskStepInfo) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                # rx.spacer(),
                rx.heading(f"step: {step.step_idx + 1}"),
                rx.hstack(
                    rx.text("url: "),
                    rx.link(step.short_url, href=step.url),
                ),
                rx.spacer(),
                rx.text("id: ", step.short_id),
                rx.hstack(
                    rx.button(
                        rx.heading("Approve", size="sm", color="green"),
                        # on_click=lambda: TaskState.approve_id(step.step_id),
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.heading("Reject", size="sm", color="red"),
                        # on_click=lambda: TaskState.reject_id(step.step_id),
                    ),
                    # rx.spacer(),
                    rx.divider(orientation="vertical", border_color="black"),
                    # rx.spacer(),
                    rx.button(
                        rx.heading("Remove Status", size="sm", color="orange"),
                        # on_click=lambda: TaskState.remove_id(step.step_id),
                    ),
                ),
                rx.center(
                    # either of these:
                    # - rx.image(src=step.image_path_web, width="500px", height="auto"),
                    rx.image(src=TrajState.task_step_images[step.step_idx], width="800px", height="auto")
                ),
                rx.spacer(),
                rx.vstack(
                    rx.foreach(
                        step.actions,
                        lambda action: rx.box(
                            rx.hstack(
                                rx.text(f"action-{action.action_idx}"),
                                # rx.spacer(),
                                rx.text(action.action_type),
                                rx.text(action.action_value),
                            ),
                            sz="sm",
                        ),
                    ),
                    align_items="left",
                    # width="30%",
                ),
                rx.link("Goto page", color="darkblue", href=step.url),
                rx.link(
                    "Launch Clippy Here",
                    color="darkblue",
                    # on_click=lambda: TaskState.launch_from_step(step.step_id),
                    is_disabled=True,
                ),
                rx.divider(border_color="black"),
                align_items="left",
            ),
        )
    )


def task_page() -> rx.Component:
    return rx.cond(
        TrajState.task,
        rx.box(
            sidebar(task_sidebar_extra()),
            rx.center(
                rx.vstack(
                    task_header_card(),
                    rx.container(
                        rx.responsive_grid(
                            rx.foreach(
                                TrajState.task_steps,
                                task_step,
                            )
                        )
                    ),
                ),
            )
            # justify="space-between",
        ),
        None,
    )
