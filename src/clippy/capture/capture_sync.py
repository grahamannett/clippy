import time

from playwright.sync_api import ConsoleMessage, Page

from clippy.capture.capture import MachineCapture
from clippy.crawler.crawler_sync import CrawlerSync
from clippy.crawler.parser.playwright_strings import _parse_segment
from clippy.crawler.states import Action, Click, Enter, Input, Step, Task, Wheel


def catch_console_injections(msg: ConsoleMessage) -> Action:
    if msg.text.startswith("CATCH"):
        values = []
        for arg in msg.args:
            values.append(arg.json_value())

        if values[1].lower() == "debug":
            print("debugging...", *values)
            return

        _, class_name, *data = values

        action = Action[class_name](*data)
        return action


class MachineCaptureSync(MachineCapture):
    # without input delay the actions sometimes dont seem to execute properly

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _get_elements_of_interest(self, cdp_client, page: Page, timeout=2):
        start_time = time.time()
        elements_of_interest = []
        print("parsing tree...", end="")
        while ((time.time() - start_time) < timeout) and (len(elements_of_interest) == 0):
            tree = self.crawler.get_tree(self.dom_parser.cdp_snapshot_kwargs)
            elements_of_interest = self.dom_parser.crawl(tree=tree, page=page)
            print("waiting...")
        print("done with get...\n")
        return elements_of_interest

    def llm_assist_hook(self, page: Page):
        if not self.use_llm:
            return

        if not self.dom_parser.need_crawl(page=page):
            return

        if (elements_of_interest := self._get_elements_of_interest(self.cdp_client, page)) == []:
            print("tried to crawl but didnt work...")
            return

        element_buffer = self.dom_parser.page_element_buffer
        ids_of_interest = self.dom_parser.ids_of_interest

        locators = [
            self.dom_parser._get_from_location(element_buffer[i], page) for idx, i in enumerate(ids_of_interest)
        ]
        elements_of_interest = elements_of_interest[:50]
        scored_els = self.instructor.compare_all_page_elements(
            self.objective, page_elements=elements_of_interest, url=page.url
        )
        if len(scored_els) == 0:
            breakpoint()

        self.instructor.highlight_from_scored(scored_els, locators=locators, page=page)

    def execute_click(self, action: Click, page: Page, **kwargs) -> None:
        if action.python_locator:
            segments = _parse_segment(action.python_locator)

        locator = self._exec_python_locator(action=action, page=page)

        locator_count = locator.count()

        if locator_count == 1:
            print("clicking off of locator")
            return locator.click(delay=self.input_delay)
        elif locator_count <= 3:
            print("locator has multiple elements but its maybe enough to just try the first one?")
            return locator.first.click(delay=self.input_delay)

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

    def execute_step(self, step: Step, page: Page, confirm: bool = True):
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

        # page.wait_for_load_state("domcontentloaded")
        page.expect_event("domcontentloaded", timeout=5 * MS)

        self.llm_assist_hook(page=page)
        self.confirm_input(step, page=page, confirm=confirm)

        for a_i, action in enumerate(step.actions):
            if self._step_through_actions and confirm:
                self.confirm_input(action, page=page, action=action, step=step)

            if type(action) in types:
                is_last_action = a_i == (len(step.actions) - 1)
                out = types[type(action)](action, page, is_last_action=is_last_action)
                if out is None:
                    out = action
                actions_taken.append(actions_taken)

                if is_last_action:
                    print("=>waiting for new page to load...", end="\r")
                    with page.expect_event("domcontentloaded") as event_info:
                        print("page should be fully loaded at this point...", event_info)
                        self.llm_assist_hook(page=page)
            else:
                print("action not found in types")

        if confirm:
            confirm = self._input("does this look correct?")

        return actions_taken

    def execute_task(self, task: Task, no_confirm: bool = False):
        self.setup_task(task=task, use_async=False)
        crawler = CrawlerSync()
        page = crawler.start(start_page=self.start_page)

        self.crawler = crawler
        self.page = page
        self.cdp_client = crawler.get_cdp_client()

        for step in task.steps:
            if step.actions == []:
                print("no actions in step...")
                continue

            self.execute_step(step, page=crawler.page, confirm=(not no_confirm))
        crawler.end()
