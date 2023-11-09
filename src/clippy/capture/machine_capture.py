from typing import Awaitable

from playwright.async_api import Page

from clippy.capture.capture import Capture
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.playwright_strings import _parse_segment
from clippy.states import Action, Actions, Click, Enter, Input, Step, Task, Wheel


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

    async def execute_task(self, task: Task, confirm: bool = True, use_async_instructor: bool = True) -> None:
        print("got all elements of interest, now scoring...")

        crawler = Crawler()
        page = await crawler.start(start_page=self.start_page, key_exit=False)

        self.crawler = crawler
        self.page = page
        self.cdp_client = await crawler.get_cdp_client_async()

        for step in task.steps:
            if step.actions == []:
                print("no actions in step...")
                continue

            await self.execute_step(step, page=crawler.page, confirm=confirm)
        await crawler.end()
