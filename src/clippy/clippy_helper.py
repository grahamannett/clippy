import asyncio
from distutils.util import strtobool
from os import environ
from typing import List
from argparse import Namespace

from clippy.capture import CaptureAsync, MachineCaptureAsync, MachineCaptureSync
from clippy.crawler.crawler import Crawler
from clippy.crawler.states.states import Task
from clippy.data_states import ClippyDefaults, ClippyState, PageState
from clippy.dm.data_manager import DataManager
from clippy.instructor import Instructor
from clippy import constants


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


class ClippyHelper:
    state: ClippyState

    def __init__(
        self,
        objective: str = constants.default_objective,
        start_page: str = constants.default_start_page,
        headless: bool = False,
        clear_step_states: bool = False,
    ):
        # gui related settings

        self.headless = headless
        self.keep_device_ratio = _device_ratio_check()

        self.start_page = start_page
        self.objective = objective

        self.state: ClippyState = None
        self.page_state: PageState = None
        self.clear_step_states = clear_step_states
        self.data_manager = DataManager()

    async def start(self, args: Namespace):
        cmd = args.cmd
        no_confirm = args.no_confirm
        use_llm = args.llm

        exec_type = _check_exec_type(args.exec_type, cmd)

        funcs = {
            "sync": {
                "replay": self.run_replay(class_handler=MachineCaptureSync),
            },
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

    async def run_capture(self, use_llm: bool = False, **kwargs):
        capture = CaptureAsync(objective=self.objective, data_manager=self.data_manager)
        crawler = Crawler(headless=False)

        await capture.start(crawler, start_page=self.start_page)
        await crawler.end()
        capture.end_capture()

    def run_replay(self, class_handler: MachineCaptureAsync | MachineCaptureSync):
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

        task_select = self._get_input("Select task: ")
        try:
            task_select = int(task_select)
        except ValueError:
            # this is just so i can break into the debugger if i dont enter a number at this step
            breakpoint()
        task = tasks[task_select]
        return task

    def _get_input(self, string: str = None):
        return input(string)

    def get_page_state(self, state: ClippyState) -> ClippyState:
        """
        get the observation (meaning the page elements )
        """

        page_elements = state.crawler.crawl()
        page_state = PageState(url=state.crawler.page.url, page_elements=page_elements)
        state.page_state = page_state
        return state

    def step(self, state: ClippyState) -> ClippyState:
        """
        loop is like this:
        1. get the page state (includes page elements)
        2. get prerequisites for state
        2. process page with instructor (get next command and next command target)
        3. get feedback

        """

        if state.pre_step:
            state = state.pre_step(state)

        state = state.next_step(state)

        if state.post_step:
            state = state.post_step(state)

        if self.clear_step_states:
            state.pre_step = None
            state.post_step = None

        state.pre_step = state.response.next_steps["pre_step"]
        state.next_step = state.response.next_steps["next_step"]
        state.post_step = state.response.next_steps["post_step"]

        return state

    def run(self) -> ClippyState:
        state = self.state
        state = self.step(state)
        return state
