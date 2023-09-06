import asyncio
from argparse import Namespace
from distutils.util import strtobool
from os import environ
from typing import Awaitable, Dict, List

from loguru import logger
from playwright.async_api import Page

from clippy import constants
from clippy.capture import CaptureAsync, MachineCaptureAsync
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser, Locators
from clippy.dm.data_manager import DataManager
from clippy.states import Task
from clippy.instructor import Instructor, NextAction
from clippy.utils._input import _get_input


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


class Clippy:
    # crawler - capture - data_manager
    crawler: Crawler
    capture: CaptureAsync
    data_manager: DataManager
    task: Task

    # async_tasks means background processes, not a clippy `Task`
    async_tasks: Dict[str, asyncio.Task | asyncio.Event | asyncio.Condition] = {}

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

        self.DEBUG = strtobool(environ.get("DEBUG", "False"))

    @property
    def page(self):
        return getattr(self.crawler, "page", None)

    @property
    def url(self):
        return getattr(self.crawler, "url", None)

    @property
    def task(self):
        if self.data_manager:
            return self.data_manager.task

        return None

    async def start(self, args: Namespace):
        cmd = args.cmd
        no_confirm = args.no_confirm
        use_llm = args.llm

        exec_type = _check_exec_type(args.exec_type, cmd)

        _go = {
            "sync": {},
            "async": {
                "capture": self.run_capture,
                "replay": self.run_replay(class_handler=MachineCaptureAsync),
            },
        }

        func = _go[exec_type].get(cmd, None)
        if func is None:
            raise Exception(f"`{cmd}` not supported in {exec_type} mode")

        return await func(use_llm=use_llm, no_confirm=no_confirm)

    def check_command(self, cmd: str):
        match cmd:
            case "capture":
                self._check_objective()

    def _check_objective(self):
        if self.objective == constants.default_objective:
            print("no objective set, please enter objective")
            self.objective = self._get_input(self.objective)

    async def wait_until(self, message: str = None, timeout: float = 0.5, **kwargs) -> None:
        # Ive tried a lot of things besides just sleeping but the order of stuff happening is not consistent
        # there is probably a better way to do this using async but would require knowing exactly what is happening
        if event := self.async_tasks.get(message, None):
            if event.is_set():
                event.clear()

            logger.debug(f"waiting on {message} with {event}")
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"timeout on {message}")

    async def start_capture(self, goto_start_page: bool = True):
        self.data_manager.capture_task(Task(self.objective))
        self.capture = CaptureAsync(data_manager=self.data_manager, clippy=self)
        self.crawler = Crawler(headless=self.headless, clippy=self)

        page = await self.capture.start(self.crawler, start_page=False)

        if self.pause_start:
            self.async_tasks["crawler_pause"] = self.crawler.pause_task

        if self.key_exit:
            task = self.crawler.add_background_task(self.crawler.allow_end_early(), "key_exit")

            # # TODO make clearer
            # if ("key_exit" in self.async_tasks) and (self.async_tasks["key_exit"] != task):
            #     breakpoint()

            self.async_tasks["key_exit"] = task

        if goto_start_page:
            await page.goto(self.start_page)
        return page

    async def end_capture(self):
        await self.crawler.end()
        self.data_manager.save(task=self.task)

    async def run_assist(self, **kwargs):
        raise NotImplementedError

    async def run_capture(self, **kwargs):
        self.page = await self.start_capture()

        # if we capture we dont want to close browser so we will await on pause_start
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
        for i, task in enumerate(tasks):
            logger.info(
                f"Task-{i} is {task.objective} with {task.n_steps} steps and {task.n_actions} num_actions @ {task.timestamp or 'unknown'}"
            )

        task_select = _get_input("Select task: ")
        try:
            task_select = int(task_select)
        except ValueError:
            # so i can break into the debugger if i dont enter a number at this step
            breakpoint()

        return tasks[task_select]

    async def use_action(self, action: NextAction):
        """
        This asynchronous method takes a NextAction object as an argument and performs the action.

        Args:
            action (NextAction): The action to be performed.

        Returns:
            None
        """
        logger.info("in use_action")
        self.async_tasks["screenshot_event"].clear()

        logger.info("check loc")
        if hasattr(action, "locator"):
            await action.locator.first.scroll_into_view_if_needed()

        logger.info("execute action")
        await self.crawler.execute_action(action)

    async def get_elements(self, filter_elements: bool = True):
        self.dom_parser = DOMSnapshotParser(self.crawler)
        await self.dom_parser.parse()

        elements = self.dom_parser.elements_of_interest

        if filter_elements:
            elements = list(filter(self.dom_parser.element_allowed, elements))

        return elements

    async def suggest_action(self, num_elems: int = 100, previous_commands: List[str] = None) -> NextAction:
        instructor = Instructor(use_async=True)
        self.dom_parser = DOMSnapshotParser(self.crawler)  # need cdp_client and page so makes sense to use crawler

        previous_commands = self._get_previous_commands(previous_commands)

        # get all the links/actions -- TODO: should these be on the instructor?
        # filter out text/images that are not actionable
        elements = await self.get_elements(filter_elements=True)
        elements = elements[:num_elems]

        title = await self.crawler.title
        logger.info(f"for `{title[:20]}` filtering {len(elements)} elements...")
        filtered_elements = await instructor.filter_actions(
            elements,
            self.objective,
            title,
            self.crawler.url,
            previous_commands=previous_commands,
            max_elements=10,
            temperature=0.0,
        )

        logger.info(f"generating response with {len(filtered_elements)} elements...")
        generated_response = await instructor.generate_next_action(
            filtered_elements,
            self.objective,
            title,
            self.crawler.url,
            previous_commands=previous_commands,
            num_generations=1,
            temperature=0.0,
        )
        # just get the first response unless we change num_generations
        generated_response = generated_response[0]

        # transform the generated action to a json type action to a NextAction type
        logger.info(f"transforming response...{generated_response.text}")
        next_action = await instructor.transform_action(generated_response.text, temperature=0.3)
        next_action.locator = self._get_locator_for_action(next_action)
        logger.info(f"transformed {generated_response.text} to {next_action}")
        return next_action

    def _get_locator_for_action(self, action: NextAction):
        element_buffer = self.dom_parser.page_element_buffer[action.element_id]
        loc = self.dom_parser.get_loc_helper(element_buffer)
        return loc

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
