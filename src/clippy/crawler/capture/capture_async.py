import asyncio
import time
from typing import Coroutine

from playwright.async_api import ConsoleMessage, Frame, Page

from clippy.crawler.capture.base import Capture, MachineCapture
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser
from clippy.crawler.parser.playwright_strings import _parse_segment
from clippy.crawler.states import Action, Click, Enter, Input, Step, Task, Wheel
from clippy.crawler.tools_capture import _print_console
from clippy.instructor import Instructor
from clippy.utils.async_tools import timer


def _otherloaded(name: str):
    """helper func for attaching to page events"""

    async def _fn(*args, **kwargs):
        print(f"{name} event")

    return _fn


async def catch_console_injections(msg: ConsoleMessage) -> Action:
    if msg.text.startswith("CATCH"):
        values = []
        for arg in msg.args:
            values.append(await arg.json_value())

        # values = [await a.json_value() for a in msg.args]

        _print_console(*values)
        if values[1].lower() == "debug":
            print("debugging...", *values)
            return

        _, class_name, *data = values  # data is list of [CATCH, class_name, *data]

        action = Action[class_name](*data)
        return action


class CaptureAsync(Capture):
    async_tasks = {}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _setup_coroutine(self, co: Coroutine):
        self.async_tasks[co.__name__] = co

    def setup_llm_suggest(self):
        self.instructor = Instructor()
        self.dom_parser = DOMSnapshotParser(keep_device_ratio=False)

    async def domcontentloaded_hook(self, page: Page):
        print("\n==>PAGE-CHANGED...wait for screenshot", end="")
        # let task know its changed
        await self.task.page_change_async(page)

        # TODO move capture_screenshots into its own hook, but has to be able to get step name prior to screenshot
        # then we need to capture screenshot, since we use the task id for the name
        await self._capture_screenshots()
        print(">=>PAGE CHANGE COMPLETE")

    async def _capture_screenshots(self, path: str = None):
        if path is None:
            assert hasattr(self.task.curr_step, "id"), "task must have id"
            path = f"{self.data_manager._curr_task_output}/{self.task.curr_step.id}.png"
        self.task.curr_step.screenshot_path = path
        await self.page.screenshot(path=path, full_page=True)

    async def console_hook(self, msg: ConsoleMessage):
        action = await catch_console_injections(msg)
        if action:
            self.task(action)

    async def _get_elements_of_interest(self, cdp_client, page: Page, timeout=2):
        start_time = time.time()
        elements_of_interest = []
        print("parsing tree...", end="")

        while ((time.time() - start_time) < timeout) and (len(elements_of_interest) == 0):
            tree = await self.crawler.get_tree(self.dom_parser.cdp_snapshot_kwargs)
            elements_of_interest = await self.dom_parser.crawl_async(tree=tree, page=page)
        return elements_of_interest

    # @timer
    async def llm_assist_hook(self, page: Page):
        if not self.use_llm:
            return

        if (elements_of_interest := await self._get_elements_of_interest(self.cdp_client, page)) == []:
            print("tried to crawl but didnt work...")
            return

        # elements_of_interest = await self.dom_parser.crawl_async(self.cdp_client, page)
        element_buffer = self.dom_parser.page_element_buffer
        ids_of_interest = self.dom_parser.ids_of_interest

        if not ids_of_interest:
            print("no elements of interest, skipping...")
            return

        locators = await asyncio.gather(
            *[self.dom_parser._get_from_location_async(element_buffer[i], page) for idx, i in enumerate(ids_of_interest)]
        )

        # TODO: shorten it for time being
        elements_of_interest = elements_of_interest[:50]
        scored_elements = await self.instructor.compare_all_page_elements_async(
            self.objective, page_elements=elements_of_interest, url=page.url
        )

        if not scored_elements:
            breakpoint()

        return await self.instructor.highlight_from_scored_async(scored_elements, locators=locators, page=page)


class HumanCaptureAsync(CaptureAsync):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.action_idx = 0

    async def human_start(self):
        self.data_manager.capture_start()
        self.setup_llm_suggest()
        crawler = Crawler()
        self.crawler = crawler
        page = await crawler.start()

        self._setup_page_hooks(page=page)
        self.page = page
        self.cdp_client = await self.crawler.cdp_client
        await self.page.goto(self.start_page)

        # this is where a human starts doing things
        await self.page.pause()
        await crawler.end()

    def _setup_page_hooks(self, page: Page):
        # watch for console injections + page changes
        page.on("console", self.console_hook)
        page.on("domcontentloaded", self.domcontentloaded_hook)

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
