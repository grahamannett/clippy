import asyncio
from argparse import Namespace
from distutils.util import strtobool
from os import environ
from pathlib import Path
from typing import Dict, List

from loguru import logger

from clippy import constants
from clippy.capture import CaptureAsync, MachineCaptureAsync
from clippy.crawler.crawler import Crawler, Page
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser, Locators
from clippy.dm.data_manager import DataManager
from clippy.dm.task_bank import TaskBankManager
from clippy.instructor import Instructor, NextAction
from clippy.states import Action, Task
from clippy.states.states import Step
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

    # async_tasks means background processes, not a clippy `Task`
    async_tasks: Dict[str, asyncio.Task | asyncio.Event | asyncio.Condition] = {}
    used_next_actions: List[NextAction] = []

    def __init__(
        self,
        objective: str = constants.default_objective,
        start_page: str = constants.default_start_page,
        headless: bool = False,
        key_exit: bool = True,
        confirm: bool = False,
        pause_start: bool = True,
        clear_step_states: bool = False,
        data_dir: str = f"{constants.ROOT_DIR}/data/",
        data_manager_path: str = f"{constants.ROOT_DIR}/data/tasks",
        database_path: str = f"{constants.ROOT_DIR}/data/db/db.json",
        seed: int | None = None,
        **kwargs,
    ) -> None:
        # gui related settings
        self.headless = headless
        self.key_exit = key_exit
        self.confirm = confirm
        self.pause_start = pause_start
        self.keep_device_ratio = _device_ratio_check()

        self.start_page = start_page
        self.objective = objective

        self.clear_step_states = clear_step_states
        self.data_dir = Path(data_dir)
        self.data_manager_path = Path(data_manager_path)  # data manager handles tasks/steps/dataclasses
        self.database_path = Path(database_path)  # database handles json storage
        self.data_manager = DataManager(self.data_manager_path, self.database_path)

        self.tbm = TaskBankManager(seed=seed)
        self.tbm.process_task_bank()

        self.DEBUG = strtobool(environ.get("DEBUG", "False"))

    @property
    def page(self) -> Page | None:
        return getattr(self.crawler, "page", None)

    @property
    def url(self) -> str | None:
        return getattr(self.crawler, "url", None)

    @property
    def task(self) -> Task | None:
        if self.data_manager:
            return self.data_manager.task

        return None

    async def run(self, args: Namespace) -> None:
        cmd = args.cmd

        func = {
            "capture": self.run_capture,
            "replay": self.run_replay,
            "datamanager": self.data_manager.run,
        }.get(cmd, None)

        if func is None:
            raise Exception(f"`{cmd}` not supported in {self.__class__.__name__} mode")

        return await func(**vars(args))

    def check_command(self, cmd: str, kwargs: dict):
        match cmd:
            case "capture":
                self._check_objective(kwargs)

    def _get_random_task(self) -> str:
        task = self.tbm.sample()
        return task

    def _check_objective(self, kwargs: dict) -> None:
        # if we set task in kwargs then fetch it from task bank

        if (_task_sample := kwargs.get("task", None)) != None:
            _task_sample = _task_sample if _task_sample >= 0 else None
            self.objective = self.tbm.sample(_task_sample)
            logger.info(f"Sampled task: {self.objective}")

        if self.objective is constants.default_objective:
            logger.info("Default objective is used. So need to ask user.")
            self.objective = _get_input(self.objective)
            if self.objective.startswith(("r", "random")):
                self.objective = self.tbm.sample()
                logger.info(f"Sampled task: {self.objective}")

    async def wait_until(self, message: str = None, timeout: float = 1.0, **kwargs) -> None:
        # Ive tried a lot of things besides just sleeping but the order of stuff happening is not consistent
        # there is probably a better way to do this using async but would require knowing exactly what is happening
        event = self.async_tasks.get(message, None)
        if event is not None:
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
            self.async_tasks["key_exit"] = self.crawler.add_background_task(self.crawler.allow_end_early(), "key_exit")

        if goto_start_page:
            await page.goto(self.start_page)
        return page

    async def end_capture(self):
        await self.crawler.end()
        self.data_manager.save()

    async def run_assist(self, **kwargs):
        raise NotImplementedError

    async def run_capture(self, **kwargs):
        await self.start_capture()
        # if we capture we dont want to close browser so we will await on pause_start
        await self.async_tasks["crawler_pause"]
        await self.end_capture()

    async def run_auto(self, user_confirm: bool = True, **kwargs):
        page = await self.start_capture()

        while True:
            next_action = await self.suggest_action()
            if user_confirm:
                task_select = _get_input("Confirm action (q/b/*): ")
                if task_select == "q":
                    await self.end_capture()
                    exit()
                elif task_select == "b":
                    breakpoint()

            await self.use_action(next_action)

    async def run_replay(self, **kwargs):
        task = self.get_task_for_replay(self.data_manager.tasks)
        self.start_page = task.steps[0].url
        await self.start_capture(goto_start_page=True)

        for step in task.steps:
            await self.execute_step(step)

    async def execute_step(self, step: Step, page: Page | None = None):
        pass

    def get_task_for_replay(self) -> Task:
        self.data_manager.load()
        task: Task
        for i, task in enumerate(self.data_manager.tasks):
            logger.info(
                f"Task-{i} is {task.objective} with {task.n_steps} steps & {task.n_actions} n_actions @ {task.timestamp}"
            )

        try:
            task_select = int(_get_input("Select task: "))
            return self.data_manager.tasks[task_select]
        except ValueError:
            # so i can break into the debugger if i dont enter a number at this step
            breakpoint()

    async def use_action(self, action: NextAction):
        """
        This asynchronous method takes a NextAction object as an argument and performs the action.

        Args:
            action (NextAction): The action to be performed.

        Returns:
            None
        """
        self.used_next_actions.append(action)
        self.async_tasks["screenshot_event"].clear()

        if hasattr(action, "locator"):
            await action.locator.first.scroll_into_view_if_needed()

        await self.crawler.execute_action(action)

    async def get_elements(self, filter_elements: bool = True):
        self.dom_parser = DOMSnapshotParser(self.crawler)
        await self.dom_parser.parse()

        elements = self.dom_parser.elements_of_interest

        if filter_elements:
            elements = list(filter(self.dom_parser.element_allowed, elements))

        return elements

    async def suggest_action(
        self, num_elems: int = 100, previous_commands: List[str] = [], filter_elements: bool = True
    ) -> NextAction:
        instructor = Instructor(use_async=True)
        self.dom_parser = DOMSnapshotParser(self.crawler)  # need cdp_client and page so makes sense to use crawler
        title = await self.crawler.title

        previous_commands = self._get_previous_commands(previous_commands)

        # get all the links/actions -- TODO: should these be on the instructor?
        # filter out text/images that are not actionable
        elements = await self.get_elements(filter_elements=True)

        if num_elems:
            elements = elements[:num_elems]

        if filter_elements:
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

            elements = filtered_elements

        logger.info(f"generating response with {len(elements)} elements...")
        generated_response = await instructor.generate_next_action(
            elements,
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
        next_action_idx = 0
        if len(self.task.steps) >= 1:
            for step in self.task.steps:
                for action in step.actions:
                    if not isinstance(action, Action):
                        breakpoint()
                        raise Exception("action is not an Action")

                    gen_action = self.used_next_actions[next_action_idx]
                    last_cmd = f"{action.__class__.__name__} {gen_action.element_id}"

                    if gen_action.action_args:
                        last_cmd += f" - {gen_action.action_args}"

                    next_action_idx += 1
                    previous_commands.append(last_cmd)

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
