import asyncio
from typing import Coroutine

from loguru import logger
from playwright.async_api import ConsoleMessage, Frame, Page, Request

from clippy.capture.capture import Capture, MachineCapture
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser
from clippy.crawler.parser.playwright_strings import _parse_segment
from clippy.states import Action, Click, Enter, Input, Step, Task, Wheel
from clippy.crawler.tools_capture import _print_console
from clippy.dm.data_manager import DataManager
from clippy.instructor import Instructor


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


class ScreenshotHelper:
    def __init__(self, crawler: Crawler):
        self.crawler = crawler
        self.captured_screenshot_ids = []

    async def capture(self, page: Page):
        pass

    async def emit_done(self, page: Page):
        await page.evaluate("console.log('screenshotEventDone')")


class CaptureAsync(Capture):
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
            objective=objective,
            start_page=start_page,
            data_manager=data_manager,
            use_llm=use_llm,
            *args,
            **kwargs,
        )

        self.captured_screenshot_ids = []
        self.captured_screenshot_urls = []

    async def hook_dom_group(self, page: Page):
        logger.info(f">=>PAGE-CHANGE|{page.url}")
        await self.hook_update_task_new_page(page=page)

        async with self.events["screenshot_event"]:
            await self.hook_capture_screenshot(page=page)

    async def hook_update_task_new_page(self, page: Page):
        await self.task.page_change_async(page=page)

    async def hook_capture_screenshot(self, page: Page):
        self.captured_screenshot_urls.append(page.url)

        if self.task.curr_step.id in self.captured_screenshot_ids:
            return

        path = f"{self.data_manager.curr_task_output}/{self.task.curr_step.id}.png"
        self.task.curr_step.screenshot_path = path
        await self.crawler.page.screenshot(path=path, full_page=True)
        self.captured_screenshot_ids.append(self.task.curr_step.id)

    async def hook_console(self, msg: ConsoleMessage):
        if action := await catch_console_injections(msg):
            self.task(action)

    async def hook_request_navigation_response(request: Request):
        if request.is_navigation_request():
            pass

    def setup_page_hooks(self, page: Page):
        # first create events that hooks may need
        self.events["screenshot_event"] = asyncio.Condition()

        # this captures actions from injections
        page.on("console", self.hook_console)
        # this one captures the page change
        page.on("domcontentloaded", self.hook_dom_group)

    async def start(self, crawler: Crawler, start_page: str = None) -> Page:
        self.crawler = crawler

        logger.info("crawler start...")
        page = await crawler.start(key_exit=True)
        logger.info("add background tasks...")
        await crawler.add_background_task(crawler.allow_end_early())

        logger.info("setup page hooks...")
        self.setup_page_hooks(page=page)

        if start_page:
            # think this might fuck up the capture
            logger.info("going to start page")
            await page.goto(start_page)

        return page


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
