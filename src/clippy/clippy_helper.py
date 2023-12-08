from collections import UserDict

from clippy import constants, logger
from clippy.callback import Callback
from clippy.capture import CaptureAsync
from clippy.clippy_base import ClippyBase, TaskGenFromTypes
from clippy.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser, element_allowed_fn
from clippy.dm import DataManager, LLMTaskGenerator, TaskBankManager
from clippy.instructor import Instructor, NextAction
from clippy.states import Action, Task
from clippy.utils import _get_input


class AsyncTasksManager(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Clippy(ClippyBase):
    # crawler - capture - data_manager
    crawler: Crawler
    capture: CaptureAsync
    data_manager: DataManager
    callback_manager: Callback = Callback()

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
        seed: int = None,
        task_gen_from: TaskGenFromTypes = "taskbank",
        **kwargs,
    ) -> None:
        super().__init__(
            objective=objective,
            start_page=start_page,
            headless=headless,
            key_exit=key_exit,
            confirm_actions=confirm_actions,
            pause_start=pause_start,
            clear_step_states=clear_step_states,
            data_dir=data_dir,
            data_manager_path=data_manager_path,
            database_path=database_path,
            seed=seed,
            task_gen_from=task_gen_from,
            **kwargs,
        )

        self.data_manager = DataManager(self.data_manager_path, self.database_path)

        # TODO: make the task bank manager one instance with 2 interfaces/generators
        self.tbm = TaskBankManager(seed=self._seed).setup()
        self.tbm_llm = LLMTaskGenerator(seed=self._seed)

        if self.task_gen_from == "llm":
            self.tbm_llm.setup()

        self.task_generators_avail["llm"] = self.tbm_llm.sample_sync
        self.task_generators_avail["taskbank"] = self.tbm.sample

    async def run(self, run_kwargs: dict) -> None:
        funcs = {
            "capture": self.run_capture,
            "replay": self.run_replay,
            "datamanager": self.data_manager.run,
            "assist": self.run_assist,
        }

        cmd, cmd_kwargs = self._make_cmd_kwargs(run_kwargs)
        try:
            func = funcs[cmd]
        except KeyError:
            raise Exception(f"`{cmd}` not supported in {self.__class__.__name__} mode")

        return await func(**cmd_kwargs)

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
        try:
            action_resp = await self.crawler.actions[action_type](action)
        except Exception as err:
            logger.debug(f"Executing action: {action} caused error: {err}")
            breakpoint()

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
        self, num_elems: int = 100, previous_commands: list[str] = [], filter_elements: bool = True
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
