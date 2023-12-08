import reflex as rx

from clippy.clippy_base import TaskGenFromTypes


class TrajlabConfig(rx.Config):
    task_gen_from: TaskGenFromTypes = "taskbank"


config = TrajlabConfig(
    app_name="trajlab",
    telemetry_enabled=False,
)
