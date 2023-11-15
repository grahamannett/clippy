from __future__ import annotations

import asyncio
from typing import Dict

from clippy import logger
from clippy.clippy_base import ClippyBase
from clippy.constants import input_delay
from clippy.crawler.screenshot_matcher import ScreenshotMatcher
from clippy.dm.data_manager import DataManager
from clippy.states import Action, Step, Task
from clippy.utils import _get_input


class Capture:
    input_delay: int = input_delay
    async_tasks: Dict[str, asyncio.Task | asyncio.Event | asyncio.Condition] = {}

    def __init__(
        self,
        start_page: str = None,
        data_manager: DataManager = None,
        print_injection: bool = True,
        use_screenshot_matcher: bool = True,
        clippy: ClippyBase = None,
    ) -> None:
        self.start_page = start_page
        self.print_injection = print_injection

        self.data_manager = data_manager
        self.ss_match = ScreenshotMatcher(self.data_manager) if use_screenshot_matcher else None

        self.clippy = clippy

        if self.clippy:
            self.async_tasks = self.clippy.async_tasks

    @property
    def task(self) -> Task:
        return self.data_manager.task

    async def end(self):
        pass

    def confirm_input(self, next_type: Action | Step, confirm: bool = True, **kwargs) -> None:
        if not confirm:
            return
        logger.debug(f"next {next_type.__class__.__name__} will be:\n{next_type}\n" + "=" * 10)
        resp = _get_input("does this look correct? (y/n)")

        match resp.lower():
            case "n":
                breakpoint()
            case "s":
                self._step_through_actions = True
            case "c":
                self._step_through_actions = False
