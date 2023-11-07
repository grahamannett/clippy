from enum import auto, StrEnum

from trajlab.db_interface import db_interface


class ApprovalStatus(StrEnum):
    APPROVED = auto()
    REJECTED = auto()
    PENDING = auto()
    RUNNING = auto()

    DEFAULT = PENDING

    @property
    def color(self) -> str:
        return {
            ApprovalStatus.APPROVED: "green",
            ApprovalStatus.REJECTED: "red",
            ApprovalStatus.RUNNING: "purple",
            ApprovalStatus.PENDING: "orange",
        }[self]

    @property
    def emoji(self) -> str:
        return {
            ApprovalStatus.APPROVED: "✅",
            ApprovalStatus.REJECTED: "❌",
            ApprovalStatus.RUNNING: "🏃🏻‍♀️",
            ApprovalStatus.PENDING: "👾",
        }[self]

    @classmethod
    def get_status(cls, task_id: str) -> "ApprovalStatus":
        try:
            task_state = db_interface.get_approval_status(task_id)
            return cls(task_state)
        except ValueError:
            return cls.DEFAULT
