import asyncio
from distutils.util import strtobool
from os import environ
from typing import List

from clippy.crawler.capture import HumanCaptureAsync, MachineCaptureAsync, MachineCaptureSync
from clippy.crawler.executor import Executor
from clippy.crawler.states.states import Task
from clippy.data_states import ClippyDefaults, ClippyState, PageState
from clippy.dm.data_manager import DataManager
from clippy.instructor import Instructor

import argparse


def check_startup():
    api_key = environ.get("COHERE_KEY")
    if api_key is None:
        raise Exception("COHERE_KEY not set in environment")
    # TODO: check for device ratio issue.


def use_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--objective", type=str, default=None)
    parser.add_argument("-t", "--task", type=str, choices=["capture", "replay", "assist"], default="assist")
    parser.add_argument("-nc", "--no-confirm", action="store_true", default=False)
    parser.add_argument("-sp", "--start_page", type=str, default="https://www.google.com")
    parser.add_argument("-et", "--exec-type", type=str, choices=["sync", "async"], default="sync")
    parser.add_argument("-l", "--llm", default=False, action="store_true")

    args = parser.parse_args()
    return args


clippy_defaults = ClippyDefaults()


class Clippy:
    state: ClippyState
    defaults: ClippyDefaults

    def __init__(self, objective: str = None, headless: bool = False, clear_step_states: bool = False, start_page: str = None):
        # gui related settings

        self.headless = headless
        self.keep_device_ratio = bool(strtobool(environ.get("KEEP_DEVICE_RATIO", "False")))

        self.start_page = start_page if start_page else clippy_defaults.start_page
        self.objective = objective if objective else clippy_defaults.objective

        self.state: ClippyState = None
        self.page_state: PageState = None
        self.clear_step_states = clear_step_states
        self.data_manager = DataManager()

    def start(self, args: argparse.Namespace):
        task = args.task
        no_confirm = args.no_confirm
        use_llm = args.llm

        exec_type = args.exec_type
        if task == "capture" and exec_type != "async":
            print("==>WARNING<==")
            print("---you cannot capture task in sync mode due to needing to handle callbacks")
            print("---manually changing exec_type to async")
            print("==>WARNING END<==")
            exec_type = "async"

        funcs = {
            "sync": {
                "replay": self.run_replay(class_handler=MachineCaptureSync),
            },
            "async": {
                "assist": self.run_assist,
                "capture": self.run_capture,
                "replay": self.run_replay(class_handler=MachineCaptureAsync),
            },
        }

        func = funcs[exec_type].get(task, None)
        if func is None:
            raise Exception(f"\n\n\t==>Task `{task}` not supported in {exec_type} mode\n\n")

        if exec_type == "async":
            asyncio.run(func(use_llm=use_llm, no_confirm=no_confirm))
        else:
            func(no_confirm=no_confirm, use_llm=use_llm)

    async def run_capture(self, use_llm: bool = False, **kwargs):
        capture = HumanCaptureAsync(objective=self.objective, data_manager=self.data_manager, use_llm=use_llm)
        await capture.human_start()
        capture.end_capture()

    def run_replay(self, class_handler: MachineCaptureAsync | MachineCaptureSync):
        def _replay(use_llm: bool, no_confirm: bool, **kwargs):
            task = self.get_task_for_replay(self.data_manager.tasks)
            capture = class_handler(objective=self.objective, data_manager=self.data_manager, start_page=self.start_page, use_llm=use_llm)
            return capture.execute_task(task=task, no_confirm=no_confirm, **kwargs)

        return _replay

    async def run_assist(self, **kwargs):
        self.start_agent()
        while True:
            self.run()

    def get_task_for_replay(self, tasks: List[Task]) -> Task:
        self.data_manager.load()
        tasks: List[Task] = self.data_manager.tasks
        for t_i, task in enumerate(tasks):
            n_steps = task.n_steps
            n_actions = task.n_actions
            tstamp = task.timestamp
            print(f"Task-{t_i} is {task.objective} with {n_steps} steps and {n_actions} num_actions @ {tstamp if tstamp else 'unknown'}")

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

    def reset(self) -> ClippyState:
        executor = Executor(keep_device_ratio=self.keep_device_ratio, headless=self.headless)
        self.state = ClippyState(executor=executor)
        return self.state

    def start_agent(self):
        state = self.reset()
        defaults = ClippyDefaults()
        state.executor.go_to_page(defaults.start_page)

        if self.objective is None:
            objective = self._get_input(defaults.objective)
        else:
            print(f"starting with objective: {self.objective}")
            objective = self.objective

        state.objective = objective
        self.instructor = Instructor(objective)

        # set initial loop states
        state.pre_step = self.get_page_state
        state.next_step = self.instructor.step_handler.first_step
        state.post_step = self.instructor.step_handler.post_state

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


if __name__ == "__main__":
    check_startup()
    args = use_args()

    clippy = Clippy(objective=args.objective, headless=args.headless, start_page=args.start_page)
    clippy.start(args)

    # while True:
    #     clippy.run()
