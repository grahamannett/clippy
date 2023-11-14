from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Coroutine, Dict

from playwright.async_api import Page

from clippy.constants import input_delay
from clippy.crawler.screenshot_matcher import ScreenshotMatcher
from clippy.dm.data_manager import DataManager
from clippy.states import Action, Actions, Step, Task


class Capture:
    input_delay: int = input_delay

    async_tasks: Dict[str, asyncio.Task | asyncio.Event | asyncio.Condition] = {}

    def __init__(
        self,
        start_page: str = None,
        data_manager: DataManager = None,
        use_llm: bool = False,
        print_injection: bool = True,
        use_screenshot_matcher: bool = True,
        clippy: Clippy = None,
    ) -> None:
        self.start_page = start_page

        self.data_manager = data_manager
        self.ss_match = ScreenshotMatcher(self.data_manager) if use_screenshot_matcher else None

        self.use_llm = use_llm
        self.print_injection = print_injection
        self.clippy = clippy

        if self.clippy:
            self.async_tasks = self.clippy.async_tasks

    @property
    def task(self) -> Task:
        return self.data_manager.task

    def _input(self, text: str) -> str:
        # used for mocking input
        return input(text)

    async def end(self):
        pass

    def confirm_input(self, next_type: Action | Step, confirm: bool = True, **kwargs) -> None:
        if not confirm:
            return
        print(f"next {next_type.__class__.__name__} will be:\n{next_type}\n" + "=" * 10)
        resp = input("does this look correct? (y/n)")
        if resp.lower() == "n":
            breakpoint()
        if resp.lower() == "s":
            self._step_through_actions = True
        if resp.lower() == "c":
            self._step_through_actions = False
