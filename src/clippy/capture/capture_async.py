import asyncio
import time
import sys
from typing import Coroutine

from loguru import logger
from playwright.async_api import ConsoleMessage, Frame, Page

from clippy.capture.capture import Capture, MachineCapture
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser
from clippy.crawler.parser.playwright_strings import _parse_segment
from clippy.crawler.states import Action, Click, Enter, Input, Step, Task, Wheel
from clippy.crawler.tools_capture import _print_console
from clippy.dm.data_manager import DataManager
from clippy.instructor import Instructor
from clippy.crawler.helpers import end_record, ainput
import threading


def _otherloaded(name: str):
    """helper func for attaching to page events"""

    async def _fn(*args, **kwargs):
        logger.info(f"{name} event")

    return _fn


async def catch_console_injections(msg: ConsoleMessage) -> Action:
    if not msg.text.startswith("CATCH"):
        return

    # if msg.text.startswith("CATCH"):
    values = []
    for arg in msg.args:
        values.append(await arg.json_value())

    _print_console(*values, print_fn=logger.debug)
    if values[1].lower() == "debug":
        logger.debug("debugging...", *values)
        return

    _, class_name, *data = values  # data is list of [CATCH, class_name, *data]

    action = Action[class_name](*data)
    return action


class CaptureAsync(Capture):
    async_tasks = {}

    def __init__(
        self,
        objective: str = None,
        start_page: str = None,
        data_manager: DataManager = None,
        use_llm: bool = False,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(
            objective=objective, start_page=start_page, data_manager=data_manager, use_llm=use_llm, *args, **kwargs
        )

        self.condition = asyncio.Condition()

        self.captured_screenshot_ids = []

    def _setup_coroutine(self, co: Coroutine):
        self.async_tasks[co.__name__] = co

    def setup_llm_suggest(self):
        if self.use_llm:
            self.instructor = Instructor()
            self.dom_parser = DOMSnapshotParser(keep_device_ratio=False)

    async def hook_update_task_new_page(self, page: Page):
        logger.info(">=>PAGE-CHANGE")

        async with self.condition:
            await self.task.page_change_async(page=page)
        # then we need to capture screenshot, since we use the task id for the name
        # await self._capture_screenshots()

    async def hook_capture_screenshot(self, page: Page):
        """take screenshot after page has loaded."""
        await self.condition.wait_for(lambda: hasattr(self.task.curr_step, "id"))
        async with self.condition:
            # idk if this has ever happened but make sure we dont screenshot twice

            if self.task.curr_step.id in self.captured_screenshot_ids:
                return

            path = f"{self.data_manager._curr_task_output}/{self.task.curr_step.id}.png"
            self.task.curr_step.screenshot_path = path
            await self.crawler.page.screenshot(path=path, full_page=True)
            self.captured_screenshot_ids.append(self.task.curr_step.id)

    async def hook_console(self, msg: ConsoleMessage):
        # action = await catch_console_injections(msg)
        # if action:
        #     self.task(action)
        if action := await catch_console_injections(msg):
            self.task(action)

    def setup_page_hooks(self, page: Page):
        # this captures actions from injections
        page.on("console", self.hook_console)
        # this one captures the page change
        page.on("domcontentloaded", self.hook_update_task_new_page)
        page.on("domcontentloaded", self.hook_capture_screenshot)

    async def start(self, crawler: Crawler, start_page: str = None, pause: bool = True):
        self.crawler = crawler

        page = await crawler.start(key_exit=True)
        await crawler.add_background_task(crawler.allow_end_early())

        self.setup_page_hooks(page=page)

        await page.goto(start_page)

        if pause:  # you wont pause if its a replay/headless
            await page.pause()
        # breakpoint()


class HumanCaptureAsync(CaptureAsync):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.action_idx = 0

    async def human_start(self):
        raise NotImplementedError("Use CaptureAsync only")

    async def framenavigated_hook(self, frame: Frame):
        pass


class MachineCaptureAsync(MachineCapture):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def execute_click(self, action: Click, page: Page, **kwargs) -> None:
        if action.python_locator:
            segments = _parse_segment(action.python_locator)

        locator = self._exec_python_locator(action=action, page=page)

        locator_count = await locator.count()
        if locator_count == 1:
            print("clicking off of locator")
            return await locator.click(delay=self.input_delay)
        elif locator_count <= 3:
            print("locator has multiple elements but its maybe enough to just try the first one?")
            return await locator.first.click(delay=self.input_delay)

        locator = page
        try:
            print("TRYING TO PARSE LOCATOR BY SEGMENTS, NOT IDEAL")
            for segment in segments:
                # THIS IS PROBLEMATIC AND I CANT REMEMBER WHY
                if len(segment) == 1:
                    locator = getattr(locator, segment[0])
                else:
                    fn_name, arg_list, kw_dict = segment
                    fn = getattr(locator, fn_name)
                    locator = fn(*arg_list, **kw_dict)  # would await this
        except:
            breakpoint()
        return locator.click(delay=self.input_delay)

    async def execute_step(self, step: Step, page: Page, confirm: bool = True):
        types = {
            Click: self.execute_click,
            Input: self.execute_input,
            Wheel: self.execute_wheel,
            Enter: self.execute_press,
        }
        actions_taken = []

        # self._cur_actions_len = len(self.actions)
        self._curr_step = step
        self._curr_actions = step.actions

        await self.llm_assist_hook(page=page)
        self.confirm_input(step, page=page, confirm=confirm)

        for a_i, action in enumerate(step.actions):
            if self._step_through_actions and confirm:
                self.confirm_input(action, page=page, action=action, step=step)

            if type(action) in types:
                is_last_action = a_i == (len(step.actions) - 1)

                out = await types[type(action)](action, page, is_last_action=is_last_action)

                if out is None:
                    out = action
                actions_taken.append(actions_taken)

                if is_last_action:
                    print("=>waiting for new page to load...", end="\r")
                    async with page.expect_event("domcontentloaded") as event_info:
                        print("page should be fully loaded at this point...", event_info)
                        await self.llm_assist_hook(page=page)
            else:
                print("action not found in types")

        if confirm:
            confirm = self._input("does this look correct?")

        return actions_taken

    async def execute_task(self, task: Task, no_confirm: bool = False, use_async_instructor: bool = True):
        print("got all elements of interest, now scoring...")

        self.setup_task(task=task, use_async=use_async_instructor)
        crawler = Crawler()
        page = await crawler.start(start_page=self.start_page, key_exit=False)

        self.crawler = crawler
        self.page = page
        self.cdp_client = await crawler.get_cdp_client_async()

        for step in task.steps:
            if step.actions == []:
                print("no actions in step...")
                continue

            await self.execute_step(step, page=crawler.page, confirm=(not no_confirm))
        await crawler.end()
