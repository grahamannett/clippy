import asyncio
from argparse import Namespace
from distutils.util import strtobool
from os import environ
from typing import List

from loguru import logger
from playwright.async_api import Page

from clippy import constants
from clippy.capture import CaptureAsync, MachineCaptureAsync
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser
from clippy.dm.data_manager import DataManager
from clippy.states import Task
from clippy.instructor import Instructor


def _device_ratio_check():
    return bool(strtobool(environ.get("KEEP_DEVICE_RATIO", "False")))


def _check_exec_type(exec_type: str, task: str):
    if (task == "capture") and (exec_type != "async"):
        print("==>WARNING<==")
        print("---you cannot capture task in sync mode due to needing to handle callbacks")
        print("---manually changing exec_type to async")
        print("==>WARNING END<==")
        exec_type = "async"
    return exec_type


def _get_input(string: str = None) -> str:
    return input(string)


class Clippy:
    # crawler - capture - data_manager
    crawler: Crawler
    capture: CaptureAsync
    data_manager: DataManager

    def __init__(
        self,
        objective: str = constants.default_objective,
        start_page: str = constants.default_start_page,
        headless: bool = False,
        clear_step_states: bool = False,
        data_dir: str = "data/tasks",
    ):
        # gui related settings

        self.headless = headless
        self.keep_device_ratio = _device_ratio_check()

        self.start_page = start_page
        self.objective = objective

        self.clear_step_states = clear_step_states
        self.data_manager = DataManager(data_dir=data_dir)  # data manager handles tasks/steps/dataclasses

    async def start(self, args: Namespace):
        cmd = args.cmd
        no_confirm = args.no_confirm
        use_llm = args.llm

        exec_type = _check_exec_type(args.exec_type, cmd)

        funcs = {
            "sync": {},
            "async": {
                # "assist": self.run_assist,
                "capture": self.run_capture,
                "replay": self.run_replay(class_handler=MachineCaptureAsync),
            },
        }

        func = funcs[exec_type].get(cmd, None)
        if func is None:
            raise Exception(f"\n\n\t==>cmd `{cmd}` not supported in {exec_type} mode\n\n")

        return await func(use_llm=use_llm, no_confirm=no_confirm)

    def check_command(self, cmd: str):
        match cmd:
            case "capture":
                self._check_objective()

    def _check_objective(self):
        if self.objective == constants.default_objective:
            print("no objective set, please enter objective")
            self.objective = self._get_input(self.objective)

    async def wait_until(self, message: str, timeout: float = 0.5, amt: float = 0.1):
        # idk how to ensure that we have started taking screenshot when screenshot is fired on domcontentloaded which might not happen before we get here
        # Ive tried a lot of things besides just sleeping but the order of stuff happening is not consistent
        # there is probably a better way to do this using async but would require knowing exactly what is happening
        await asyncio.sleep(amt)

        if event := self.capture.events.get(message, None):
            logger.debug(f"waiting on {message} with {event}")
            while event.locked():
                await asyncio.sleep(amt)

                if (timeout := timeout - amt) <= 0:
                    logger.debug(f"timeout on {message}")
                    event.notify_all()
                    return

    async def start_capture(self, key_exit: bool = True, goto_start_page: bool = True):
        self.capture = CaptureAsync(objective=self.objective, data_manager=self.data_manager)
        self.crawler = Crawler(headless=self.headless, key_exit=key_exit)
        page = await self.capture.start(self.crawler)
        if goto_start_page:
            await page.goto(self.start_page)
        return page

    async def end_capture(self):
        await self.crawler.end()
        self.capture.end_capture()

    async def run_capture(self, use_pause: bool = True, **kwargs):
        self.page = await self.start_capture()

        if use_pause:
            await self.page.pause()

        await self.end_capture()

    def run_replay(self, class_handler: MachineCaptureAsync):
        def _replay(use_llm: bool, no_confirm: bool, **kwargs):
            task = self.get_task_for_replay(self.data_manager.tasks)
            capture = class_handler(
                objective=self.objective, data_manager=self.data_manager, start_page=self.start_page, use_llm=use_llm
            )
            return capture.execute_task(task=task, no_confirm=no_confirm, **kwargs)

        return _replay

    def get_task_for_replay(self, tasks: List[Task]) -> Task:
        self.data_manager.load()
        tasks: List[Task] = self.data_manager.tasks
        for t_i, task in enumerate(tasks):
            n_steps = task.n_steps
            n_actions = task.n_actions
            tstamp = task.timestamp
            print(
                f"Task-{t_i} is {task.objective} with {n_steps} steps and {n_actions} num_actions @ {tstamp if tstamp else 'unknown'}"
            )

        task_select = _get_input("Select task: ")
        try:
            task_select = int(task_select)
        except ValueError:
            # this is just so i can break into the debugger if i dont enter a number at this step
            breakpoint()
        task = tasks[task_select]
        return task

    async def suggest_action(self):
        self.dom_parser = DOMSnapshotParser(crawler=self.crawler)
        # get all the links/actions
        elems, elems_ids = await self.dom_parser.parse()
        assert len(elems) == len(elems_ids) and len(elems) > 0, "Something wrong with elems/ids"

        # id1 = elems_ids[0]
        # locator1 = await self.dom_parser._get_from_location_async(page_elem_buffer[id1], self.crawler.page)

        locators = await self.dom_parser.get_locators_async()

        elems = elems[:20]
        instructor = Instructor(use_async=True)
        scored_elems = await instructor.compare_all_page_elements(
            self.objective, page_elements=elems, url=self.crawler.page.url
        )

        # await locators[2].first.click()
        breakpoint()
