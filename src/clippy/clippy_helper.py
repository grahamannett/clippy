import asyncio
from collections import UserDict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Literal

from clippy import logger

from clippy import constants
from clippy.callback import Callback
from clippy.controllers.apis.cohere_controller import CohereController
from clippy.capture import CaptureAsync
from clippy.crawler import Crawler, Page
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser, element_allowed_fn
from clippy.dm import DataManager, TaskBankManager, LLMTaskGenerator
from clippy.instructor import Instructor, NextAction
from clippy.states import Action, Step, Task
from clippy.utils import _device_ratio_check, _get_environ_var, _get_input


class AsyncTasksManager(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Clippy:
    # crawler - capture - data_manager
    crawler: Crawler
    capture: CaptureAsync
    data_manager: DataManager
    callback_manager: Callback = Callback()

    # async_tasks means background processes, not a clippy `Task`
    async_tasks: Dict[str, asyncio.Task | asyncio.Event | asyncio.Condition] = {}
    used_next_actions: List[NextAction] = []

    def __init__(
        self,
        objective: str = constants.default_objective,
        start_page: str = constants.default_start_page,
        headless: bool = False,
        key_exit: bool = True,
        confirm_actions: bool = False,
        pause_start: bool = True,
        clear_step_states: bool = False,
        data_dir: str = f"{constants.ROOT_DIR}/data/",
        data_manager_path: str = f"{constants.ROOT_DIR}/data/tasks",
        database_path: str = f"{constants.ROOT_DIR}/data/db/db.json",
        seed: int | None = None,
        random_task_from: Literal["llm", "bank"] = "bank",
        **kwargs,
    ) -> None:
        """
        Initialize the Clippy class.

        Parameters:
        objective (str): The objective of the task. Default is constants.default_objective.
        start_page (str): The starting page of the task. Default is constants.default_start_page.
        headless (bool): If True, the browser will run in headless mode. Default is False.
        key_exit (bool): If True, the program will exit on key press. Default is True.
        confirm_actions (bool): If True, actions will be confirmed before execution. Default is False.
        pause_start (bool): If True, the program will pause at the start. Default is True.
        clear_step_states (bool): If True, the step states will be cleared. Default is False.
        data_dir (str): The directory where data will be stored. Default is "{constants.ROOT_DIR}/data/".
        data_manager_path (str): The path to the data manager. Default is "{constants.ROOT_DIR}/data/tasks".
        database_path (str): The path to the database. Default is "{constants.ROOT_DIR}/data/db/db.json".
        seed (int | None): The seed for random number generation. Default is None.
        """
        self.DEBUG = _get_environ_var("DEBUG", False)

        # gui related settings
        self.headless = headless
        self.key_exit = key_exit
        self.confirm_actions = confirm_actions
        self.pause_start = pause_start

        self.random_task_from: Literal["llm", "bank"] = random_task_from

        self.keep_device_ratio = _device_ratio_check()

        self.start_page = start_page
        self.objective = objective

        self.clear_step_states = clear_step_states
        self.data_dir = Path(data_dir)
        self.data_manager_path = Path(data_manager_path)  # data manager handles tasks/steps/dataclasses
        self.database_path = Path(database_path)  # database handles json storage
        self.data_manager = DataManager(self.data_manager_path, self.database_path)

        # TODO: make the task bank manager one instance with 2 interfaces/generators
        self.tbm = TaskBankManager(seed=seed).setup()
        self.tbm_llm = LLMTaskGenerator(seed=seed)
        # self.tbm_llm.setup()

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

    def _get_previous_commands_from_generated(self, previous_commands: List[str] = []):
        pass
        # for used_action in self.used_next_actions:
        #     previous_commands.append(used_action.format_)

    def _get_previous_commands(self, previous_commands: List[str] = []):
        next_action_idx = 0

        def _match_cmd_with_used_actions(action):
            if not hasattr(action, "python_locator"):
                return None

            nonlocal next_action_idx
            element_id = self.used_next_actions[next_action_idx].element_id

            # if we use the element_id and it is not the last one, then increment the next_action_idx
            if (next_action_idx + 1) < len(self.used_next_actions):
                next_action_idx += 1

            return element_id

        if len(self.task.steps) >= 1:
            for step in self.task.steps:
                for action in step.actions:
                    if not isinstance(action, Action):
                        raise Exception("action is not an Action")

                    # last_cmd = f"{action.__class__.__name__}"
                    last_cmd = action.format_for_llm(element_id=_match_cmd_with_used_actions(action))

                    # gen_action = self.used_next_actions[next_action_idx]
                    # last_cmd = f"{action.__class__.__name__} {gen_action.element_id}"

                    # if gen_action.action_args:
                    #     last_cmd += f" - {gen_action.action_args}"

                    previous_commands.append(last_cmd)

        return previous_commands

    def _get_random_task(self) -> str:
        # if self.random_task_from == "llm"

        fn = {"llm": self.tbm_llm.sample_sync, "bank": self.tbm.sample}[self.random_task_from]
        return fn()

    def _check_objective(self, kwargs: dict) -> None:
        # if we set task in kwargs then fetch it from task bank
        client = CohereController.get_client(client_type="sync")
        # task_generator = LLMTaskGenerator()
        # client = CohereController()
        # loop = asyncio.new_event_loop()

        # t = loop.run_until_complete(task_generator.sample(client))

        # breakpoint()
        # _task = self.tbm_llm.sample_sync(client=client)
        self.tbm_llm.setup()
        _task = self._get_random_task()
        breakpoint()

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

    async def _generate_objective(self):
        if self.random_task_from == "llm":
            task_generator = LLMTaskGenerator()
            async with CohereController() as client:
                self.objective = await task_generator.sample(client)
        elif self.random_task_from == "bank":
            self.objective = self._get_random_task()

    async def run(self, run_kwargs: dict) -> None:
        try:
            cmd = run_kwargs.pop("cmd")
            func = {
                "capture": self.run_capture,
                "replay": self.run_replay,
                "datamanager": self.data_manager.run,
                "assist": self.run_assist,
            }[cmd]
        except KeyError:
            raise Exception(f"`{cmd}` not supported in {self.__class__.__name__} mode")

        cmd_kwargs = asdict(run_kwargs.pop("command"))
        all_kwargs = {**run_kwargs, **cmd_kwargs}

        return await func(**all_kwargs)

    def check_command(self, cmd, **kwargs) -> "Clippy":
        match cmd:
            case "capture":
                self._check_objective(kwargs)

        return self

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
        await self.crawler.end(task_dir=self.data_manager.curr_task_output)
        self.data_manager.save()

    async def run_capture(self, **kwargs):
        await self.start_capture()
        # if we capture we dont want to close browser so we will await on pause_start
        await self.async_tasks["crawler_pause"]
        await self.end_capture()

    async def run_assist(self, confirm_actions: bool = None, action_delay: int = 0, max_actions: int = 5, **kwargs):
        confirm_actions = confirm_actions or self.confirm_actions
        # disable key exit before start capture
        self.key_exit = False
        page = await self.start_capture()

        num_actions = 0

        while num_actions < max_actions:
            num_actions += 1

            next_action = await self.suggest_action()
            if confirm_actions:
                task_select = _get_input("Confirm action [Q(uit)/B(reakpoint)/C(ontinue)/*): ")
                if task_select.lower() == "q":
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
        logger.info(f"begin use-action: {action}")
        action_type = action.action  # this is a weird name for this attribute
        self.used_next_actions.append(action)
        self.async_tasks["screenshot_event"].clear()

        if action_locator := getattr(action, "locator", None):
            await action_locator.first.scroll_into_view_if_needed(timeout=5000)

        # execute the action
        await self.crawler.actions[action_type](action)

        # use merge on steps as the capture might be multiple (e.g. click input and type)
        self.task.steps[-1].merge()

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
        suffix_map = {"link": "page"}
        previous_commands = self._get_previous_commands(previous_commands)

        def _suffix_fn(el: str) -> str:
            """
            The suffix is determined by the 'suffix_map' dictionary.

            This method is useful in the context of suggesting actions for the Language Learning Model (LLM).
            By adding a suffix to an element, we can provide more context to the LLM, which can help it make better suggestions.
            """
            try:
                # split off the first word and add a suffix if it exists
                _suffix = suffix_map.get(el.split(" ", 1)[0], "")
                return f"{el} {_suffix}"
            except:
                return el

        def _filter_elem_fn(elems):
            if not filter_elements:
                return elems

            return list(filter(element_allowed_fn, elems))

        async with Instructor() as instructor:
            # instructor = Instructor(use_async=True)
            self.dom_parser = DOMSnapshotParser(self.crawler)  # need cdp_client and page so makes sense to use crawler
            await self.dom_parser.parse()
            title = await self.crawler.title

            # get all the links/actions -- TODO: should these be on the instructor?
            # filter out text/images that are not actionable
            # all_elements = await self.get_elements(filter_elements=True)
            all_elements = _filter_elem_fn(self.dom_parser.elements_of_interest)
            elements = list(map(_suffix_fn, all_elements))

            # filter to only the first num_elems
            if num_elems:
                elements = elements[:num_elems]

            # filter with the language model to get the most likely actions, not using likelihoods
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
            raw_action = generated_response[0]

            # transform the generated action to a json type action to a NextAction type
            logger.info(f"transforming response...{raw_action.text}")
            next_action = await instructor.transform_action(raw_action.text, temperature=0.2)
            if not (next_action.is_scroll() or next_action.is_done()):
                next_action.locator = self.dom_parser.get_loc_helper(
                    self.dom_parser.page_element_buffer[next_action.element_id]
                )

            logger.info(f"transformed {raw_action.text} to {next_action}")

        return next_action
