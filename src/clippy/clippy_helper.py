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
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser, Locators
from clippy.dm.data_manager import DataManager
from clippy.states import Task
from clippy.instructor import Instructor, NextAction


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

    async_tasks = {}

    def __init__(
        self,
        objective: str = constants.default_objective,
        start_page: str = constants.default_start_page,
        headless: bool = False,
        key_exit: bool = True,
        pause_start: bool = True,
        clear_step_states: bool = False,
        data_dir: str = "data/tasks",
    ):
        # gui related settings

        self.headless = headless
        self.key_exit = key_exit
        self.pause_start = pause_start
        self.keep_device_ratio = _device_ratio_check()

        self.start_page = start_page
        self.objective = objective

        self.clear_step_states = clear_step_states
        self.data_manager = DataManager(data_dir=data_dir)  # data manager handles tasks/steps/dataclasses

        self.DEBUG = strtobool(environ.get("DEBUG", False))

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

    async def start_capture(self, goto_start_page: bool = True):
        self.capture = CaptureAsync(objective=self.objective, data_manager=self.data_manager, clippy=self)
        self.crawler = Crawler(headless=self.headless, clippy=self)
        self.task = self.capture.task
        page = await self.capture.start(self.crawler, start_page=False)

        if self.pause_start:
            self.async_tasks["pause_start"] = self.crawler.pause_task

        if self.key_exit:
            self.async_tasks["key_exit"] = self.crawler.add_background_task(self.crawler.allow_end_early())

        if goto_start_page:
            await page.goto(self.start_page)
        return page

    async def end_capture(self):
        await self.crawler.end()
        self.capture.end_capture()

    async def run_capture(self, use_pause: bool = True, **kwargs):
        self.page = await self.start_capture()

        # if we are doing run capture we dont want to close browser so this is what you do
        await self.async_tasks["pause_start"]
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

    async def use_action(self, action: NextAction):
        breakpoint()
        self.task.curr_step.actions.append(action)
        await self.crawler.execute_action(action)

    async def suggest_action(self, num_elems: int = 150, previous_commands: List[str] = None) -> NextAction:
        instructor = Instructor(use_async=True)
        self.dom_parser = DOMSnapshotParser(self.crawler)  # need cdp_client and page so makes sense to use crawler

        previous_commands = self._get_previous_commands(previous_commands)

        # get all the links/actions -- TODO: should these be on the instructor?
        await self.dom_parser.parse()

        elements, locators = await self._get_locators_elements(num_elems=num_elems)

        generated_response = await instructor.generate_next_action(
            elements,
            self.objective,
            self.crawler.page.url,
            previous_commands=previous_commands,
            num_generations=1,
            temperature=0.0,
        )
        # just get the first response unless we change num_generations
        generated_response = generated_response[0]

        # transform the generated action to a json type action to a NextAction type
        next_action = await instructor.transform_action(generated_response.text, locators, temperature=0.2)

        if not next_action:
            raise NotImplementedError("need to implement _find_action_from_elems")

        return next_action

    def _get_previous_commands(self, previous_commands: List[str] = []):
        if len(self.task.steps) >= 1:
            for step in self.task.steps:
                for action in step.actions:
                    _last_cmd = f"{action.action} {action.locator_id}"
                    if action.action_args:
                        _last_cmd += f" - {action.action_args}"
                    previous_commands.append(_last_cmd)
        return previous_commands

    async def _get_locators_elements(self, num_elems: int = 150):
        elements, locators = [], {}
        for el, el_id in zip(self.dom_parser.elements_of_interest, self.dom_parser.ids_of_interest):
            if not (loc := await self.dom_parser.get_locator(el, el_id)):
                continue

            # if its out of viewport we can stop looking for elems most likely
            # actually think this will mess up if the elements are to the right of the viewport (i.e. google search filter)
            if isinstance(loc, Locators.ElementOutOfViewport):
                continue

            elements.append(el)
            locators[el_id] = loc

            if len(elements) >= num_elems:
                break
        return elements, locators
