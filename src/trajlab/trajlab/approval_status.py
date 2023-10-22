from enum import auto, StrEnum
from typing import Dict

from trajlab.db_interface import db_interface


class ApprovalStatus(StrEnum):
    APPROVED = auto()
    REJECTED = auto()
    PENDING = auto()
    INITIALIZING = auto()


class ApprovalStatusHelper:
    COLORS: Dict[ApprovalStatus, str] = {
        ApprovalStatus.APPROVED: "green",
        ApprovalStatus.REJECTED: "red",
        ApprovalStatus.INITIALIZING: "purple",
        ApprovalStatus.PENDING: "orange",
    }

    EMOJIS: Dict[ApprovalStatus, str] = {
        ApprovalStatus.APPROVED: "✅",
        ApprovalStatus.REJECTED: "❌",
        ApprovalStatus.INITIALIZING: "🟣",
        ApprovalStatus.PENDING: "",
    }

    @staticmethod
    def get_status(task_id: str) -> ApprovalStatus:
        task_state = db_interface.get_approval_status(task_id)
        return {
            True: ApprovalStatus.APPROVED,
            False: ApprovalStatus.REJECTED,
            None: ApprovalStatus.PENDING,
        }[task_state]

    @staticmethod
    def get_color(status: ApprovalStatus) -> str:
        return ApprovalStatusHelper.COLORS[status]

    @staticmethod
    def get_emoji(status: ApprovalStatus) -> str:
        return ApprovalStatusHelper.EMOJIS[status]
