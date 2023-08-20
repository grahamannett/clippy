from typing import Awaitable

from playwright.async_api import Page

from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser
from clippy.crawler.parser.playwright_strings import _parse_segment
from clippy.crawler.screenshot_matcher import ScreenshotMatcher
from clippy.crawler.states import Action, Click, Enter, Input, Step, Task, Wheel
from clippy.dm.data_manager import DataManager
from clippy.instructor import Instructor


class Capture:
    input_delay = 100

    def __init__(
        self, objective: str, start_page: str = "https://google.com", data_manager: DataManager = None, use_llm: bool = False
    ) -> None:
        self.objective = objective
        self.start_page = start_page

        self.data_manager = data_manager

        self.task: Task = Task(self.objective)
        self.ss_match = ScreenshotMatcher()

        self._allow_end_record = True
        self.use_llm = use_llm

    def _allow_nested_loop(self):
        import nest_asyncio

        nest_asyncio.apply()

    def _input(self, text: str):
        # use this for mocking
        return input(text)

    def end_capture(self):
        self.data_manager.save(task=self.task)

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


class MachineCapture(Capture):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._step_through_actions = True
        self._curr_step = None

    def _exec_python_locator(self, action: Click, page: Page, **kwargs):
        return eval(f"page.{action.python_locator}")
        # return exec(f"page.{action.python_locator}")

    def execute_none(self, *args, **kwargs) -> None:
        pass

    def execute_input(self, action: Input, page: Page, **kwargs) -> Awaitable[None] | None:
        return page.keyboard.type(text=action.value, delay=self.input_delay)

    def execute_wheel(self, action: Wheel, page: Page, increments: int = 250, **kwargs) -> Awaitable[None] | None:
        # TODO: I dont think this works if there is peripheral scrolling.  NEED TO TEST
        page_x, page_y = page.viewport_size["width"], page.viewport_size["height"]
        final_X = action.deltaX
        final_Y = action.deltaY

        num_scrolls, remainder = divmod(final_Y, increments)
        if num_scrolls < 0:
            scroll_dir = -1
        else:
            scroll_dir = 1

        delta_y = remainder
        for _ in range(abs(num_scrolls)):
            delta_y += increments * scroll_dir
        return page.mouse.wheel(delta_x=final_X, delta_y=delta_y)

        _wheels = []
        # _wheels.append(w)
        # for _ in range(abs(num_scrolls)):
        #     w = page.mouse.wheel(delta_x=0, delta_y=increments * scroll_dir)
        #     _wheels.append(w)

        # w = page.mouse.wheel(delta_x=final_X, delta_y=remainder)
        # _wheels.append(w)
        # return _wheels

    def execute_press(self, action: Action, page: Page, **kwargs) -> Awaitable[None] | None:
        return page.keyboard.press(action.value, delay=self.input_delay)

    def execute_click_with_screenshot(self, action: Action, page: Page, is_last_action: bool = False, **kwargs):
        if not is_last_action:
            return page.mouse.click(*action.position)

        # screenshot_path = f"{self.data_manager.data_dir}/{self.task.id}/{self._curr_step.id}.png"
        ss_path = self.ss_match.get_latest_screenshot_path(
            data_dir=self.data_manager.data_dir, task_id=self.task.id, step_id=self._curr_step.id
        )
        action_template_out_file = self.ss_match.get_action_template(action=action, screenshot_path=ss_path)
        middle_point = self.ss_match.get_point_from_template(page=page)

        scroll_amt = page.viewport_size["height"] // 2
        x_value, y_value = middle_point[0], middle_point[1]

        while y_value > page.viewport_size["height"]:
            page.mouse.wheel(0, scroll_amt)
            y_value -= scroll_amt

        return page.mouse.click(x_value, y_value)

    def setup_task(
        self,
        task: Task,
        use_async: bool,
        no_confirm: bool = False,
    ):
        self.task = task
        self.dom_parser = DOMSnapshotParser()
        self.instructor = Instructor(use_async=use_async)

        if no_confirm:
            self._step_through_actions = False
