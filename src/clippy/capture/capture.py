from __future__ import annotations

import asyncio
from typing import Awaitable, Dict

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
        self.ss_match = ScreenshotMatcher() if use_screenshot_matcher else None

        self.use_llm = use_llm
        self.print_injection = print_injection
        self.clippy = clippy

        if self.clippy:
            self.async_tasks = self.clippy.async_tasks

    @property
    def task(self):
        return self.data_manager.task

    def _input(self, text: str):
        # used for mocking input
        return input(text)

    def confirm_input(self, next_type: Action | Step, confirm: bool = True, **kwargs):
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


# THIS SHOULD BE PART OF CRAWLER
class MachineCapture(Capture):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._step_through_actions = True

    def _exec_python_locator(self, action: Actions.Click, page: Page, **kwargs):
        return eval(f"page.{action.python_locator}")

    def execute_none(self, *args, **kwargs) -> None:
        pass

    def execute_input(self, action: Actions.Input, page: Page, **kwargs) -> Awaitable[None] | None:
        return page.keyboard.type(text=action.value, delay=self.input_delay)

    def execute_wheel(self, action: Actions.Wheel, page: Page, increm: int = 250, **kwargs) -> Awaitable[None] | None:
        # TODO: I dont think this works if there is peripheral scrolling.  NEED TO TEST
        x, y = page.viewport_size["width"], page.viewport_size["height"]
        final_X = action.deltaX
        final_Y = action.deltaY

        num_scrolls, remainder = divmod(final_Y, increm)
        if num_scrolls < 0:
            scroll_dir = -1
        else:
            scroll_dir = 1

        delta_y = remainder
        for _ in range(abs(num_scrolls)):
            delta_y += increm * scroll_dir
        return page.mouse.wheel(delta_x=final_X, delta_y=delta_y)

    def execute_press(self, action: Action, page: Page, **kwargs) -> Awaitable[None] | None:
        return page.keyboard.press(action.value, delay=self.input_delay)

    def execute_click_with_screenshot(self, action: Action, page: Page, is_last_action: bool = False, **kwargs):
        if not is_last_action:
            return page.mouse.click(*action.position)

        ss_path = self.ss_match.get_latest_screenshot_path(
            data_dir=self.data_manager.data_dir, task_id=self.task.id, step_id=self.data_manager.task.id
        )
        action_template_out_file = self.ss_match.get_action_template(action=action, screenshot_path=ss_path)
        middle_point = self.ss_match.get_point_from_template(page=page)

        scroll_amt = page.viewport_size["height"] // 2
        x_value, y_value = middle_point[0], middle_point[1]

        while y_value > page.viewport_size["height"]:
            page.mouse.wheel(0, scroll_amt)
            y_value -= scroll_amt

        return page.mouse.click(x_value, y_value)
