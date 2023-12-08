import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Literal, List, TypeAlias

from playwright.async_api import Page

from clippy import constants, logger
from clippy.states import Action, Task
from clippy.states.actions import NextAction
from clippy.utils import _device_ratio_check, _get_environ_var, _get_input, _random_delay


RANDOM_WORD_MATCH = constants.RANDOM_WORD_MATCH
DEFAULT_OBJECTIVE = constants.default_objective

TaskGenFromTypes: TypeAlias = Literal["llm", "taskbank"]


class ClippyBase:
    """
    Use ClippyBase so I can get around circular imports.
    """

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
        task_gen_from: TaskGenFromTypes = "taskbank",
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
        self.keep_device_ratio = _device_ratio_check()
        self._seed = seed

        # gui related settings
        self.headless = headless
        self.key_exit = key_exit
        self.confirm_actions = confirm_actions
        self.pause_start = pause_start

        self.task_gen_from = task_gen_from

        self.start_page = start_page
        self.objective = objective

        self.clear_step_states = clear_step_states
        self.data_dir = Path(data_dir)
        self.data_manager_path = Path(data_manager_path)  # data manager handles tasks/steps/dataclasses
        self.database_path = Path(database_path)  # database handles json storage

        self.task_generators_avail: dict[str, callable] = {}

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

    @property
    def delay(self) -> int:
        return _random_delay(mean=constants.input_delay)

    def _make_cmd_kwargs(self, run_kwargs: dict) -> tuple[str, dict]:
        cmd = run_kwargs.pop("cmd")
        cmd_kwargs = {
            **run_kwargs,
            **asdict(run_kwargs.pop("command")),
        }

        return cmd, cmd_kwargs

    def _get_random_task(self) -> str:
        """
        Get a random task based on the task generation method.

        Returns:
            str: The generated task.
        """

        task_gen = self.task_generators_avail[self.task_gen_from]
        return task_gen()

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

        if len(self.task.steps) < 1:  #
            return previous_commands

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

    def check_command(self, cmd, **kwargs) -> "ClippyBase":
        match cmd:
            case "capture":
                self._check_objective(kwargs)

        return self

    def _check_objective(self, kwargs: dict) -> None:
        # if we set task in kwargs then fetch it from task bank

        if (task_id := kwargs.get("task_id", None)) in RANDOM_WORD_MATCH:
            if task_id.isdigit():
                raise NotImplementedError("task_id from int not implemented")
            # self.objective = self.tbm.sample(task_id)
            self.objective = self._get_random_task()
            logger.info(f"Sampled TASK from[{self.task_gen_from}]\nTASK: {self.objective} ")

        if self.objective is DEFAULT_OBJECTIVE:
            logger.info("Default objective is used. Need user response.")
            self.objective = _get_input(self.objective)

            # allow user to select a random task
            if self.objective in RANDOM_WORD_MATCH:
                self.objective = self._get_random_task()
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
                logger.warn(f"timeout on {message}")
