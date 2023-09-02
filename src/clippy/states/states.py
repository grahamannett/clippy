import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, List, Optional, Tuple

from playwright.async_api import Frame, Page
from playwright.sync_api import Frame as FrameSync
from playwright.sync_api import Page as PageSync

from clippy.states.actions import Action
from clippy.states.base import ModelBase
from clippy.constants import max_url_length


@dataclass
class Step(ModelBase):
    """
    A class to represent a step in a task.

    Attributes
    ----------
    url : str | None
        The URL of the page for this step.
    id : str | uuid.UUID
        The unique identifier for this step. Defaults to None.
    actions : List[Action]
        The list of actions to be performed in this step. Defaults to an empty list.
    """

    url: str | None
    id: str | uuid.UUID = None
    actions: List[Action] = field(default_factory=list)

    def __post_init__(self):
        """
        Post-initialization method. Generates a unique ID for the step if not provided.
        """
        if self.id is None:
            # note: if a page updates and the url does not change then id will be same
            # this will be an issue later. will have to resolve it by understanding when
            # exactly to screenshot
            self.id = str(uuid.uuid5(uuid.NAMESPACE_URL, self.url))

    def __call__(self, action: Action, **kwargs) -> None:
        """
        Method to add an action to the step.

        Parameters
        ----------
        action : Action
            The action to be added.
        """
        self.actions.append(action)

    def __repr__(self) -> str:
        """
        Method to represent the step as a string.

        Returns
        -------
        str
            The string representation of the step.
        """
        actions = "\n".join(["\t\t" + "-" + str(a) for a in self.actions])
        return f"\tPage: {self.url}\n{actions}"

    @classmethod
    def from_dict(cls, data: dict) -> Optional["Step"]:
        """
        Class method to create a Step instance from a dictionary.

        Parameters
        ----------
        data : dict
            The dictionary containing the step data.

        Returns
        -------
        Optional[Step]
            The created Step instance or None if no actions are provided in the data.
        """
        if len(actions := data.pop("actions")) < 1:
            return None

        step = cls(**data)

        for action_dict in actions:
            ActType = Action[action_dict.pop("type")]
            action = ActType(**action_dict)
            step.actions.append(action)
        return step

    @property
    def n_actions(self) -> int:
        """
        Property to get the number of actions in the step.
        """
        return len(self.actions)

    def merge(self):
        """
        Method to merge actions in the step.
        """
        if len(self.actions) < 2:
            return

        merged_actions = [self.actions.pop(0)]

        for idx, action in enumerate(self.actions):
            breakpoint()
            if isinstance(action, merged_actions[-1]) and (merged_actions[-1].should_merge(action)):
                merged_actions[-1].update(action)
            else:
                merged_actions.append(action)

        self.actions = merged_actions

    def format_url(self):
        """
        Method to format the URL of the step.

        Returns
        -------
        str
            The formatted URL.
        """
        url = self.url or self.id
        if len(url) > max_url_length:
            url = self.url[:max_url_length] + "..."
        return url

    def print(self):
        """
        Method to print the step.
        """
        url = self.format_url()

        print(f"\n===\nprinting step:{url}")
        for action in self.actions:
            print(action)


@dataclass
class Task(ModelBase):
    """
    A class to represent a task.

    Attributes
    ----------
    objective : str
        The objective of the task.
    id : str | None
        The unique identifier for the task. Defaults to a new UUID.
    steps : List[Step]
        The list of steps in the task. Defaults to an empty list.
    curr_step : Step
        The current step in the task. Defaults to None.
    timestamp : datetime | str
        The timestamp of the task creation. Defaults to the current datetime.
    """

    objective: str
    id: str | None = str(uuid.uuid4())
    steps: List[Step] = field(default_factory=list)
    curr_step: Step = None
    timestamp: datetime | str = str(datetime.now())

    def __call__(self, action: Action, **kwargs):
        """
        Method to add an action to the current step of the task.

        Parameters
        ----------
        action : Action
            The action to be added.
        """
        if not isinstance(action, Action):
            raise ValueError(f"action must be of type Action, not {type(action)}")

        self.curr_step(action, **kwargs)

    def __repr__(self) -> str:
        """
        Method to represent the task as a string.

        Returns
        -------
        str
            The string representation of the task.
        """
        steps_info = "\n".join([f"{s}" for s in self.steps])
        return f"Task: {self.objective} | {len(self.steps)} steps \n{steps_info}"

    @property
    def current(self) -> Step:
        """
        Property to get the current step of the task.

        Returns
        -------
        Step
            The current step of the task.
        """
        return self.curr_step

    @current.setter
    def current(self, step: Step):
        """
        Setter for the current step of the task.

        Parameters
        ----------
        step : Step
            The step to be set as the current step.
        """
        self.curr_step = step
        self.steps.append(step)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """
        Class method to create a Task instance from a dictionary.

        Parameters
        ----------
        data : dict
            The dictionary containing the task data.

        Returns
        -------
        Task
            The created Task instance.
        """
        id = data.get("id", None)
        objective = data.get("objective", None)
        timestamp = data.get("timestamp", None)

        steps = data.pop("steps", [])

        task = cls(**data)
        for step_dict in steps:
            step = Step.from_dict(step_dict)

            if step is None:
                continue

            task.steps.append(step)
        return task

    @property
    def n_steps(self) -> int:
        """
        Property to get the number of steps in the task.

        Returns
        -------
        int
            The number of steps in the task.
        """
        return len(self.steps)

    @property
    def n_actions(self) -> int:
        """
        Property to get the total number of actions in all steps of the task.

        Returns
        -------
        int
            The total number of actions in all steps of the task.
        """
        return sum([step.n_actions for step in self.steps])

    def print(self) -> str:
        """
        Method to print the task.

        Returns
        -------
        str
            The string representation of the task.
        """
        return self.__repr__()

    async def page_change_async(self, page: Page | Frame | str):
        """
        Asynchronous method to handle page change.

        Parameters
        ----------
        page : Page | Frame | str
            The new page.
        """
        self.page_change(page=page)

    def page_change(self, page: Page | Frame = None, url: str = None) -> None:
        """
        Method to handle page change.

        Parameters
        ----------
        page : Page | Frame, optional
            The new page. Defaults to None.
        url : str, optional
            The URL of the new page. Defaults to None.
        """
        if page:
            url = page.url

        if self._check_new_page(url) is False:
            return

        self.curr_step = Step(url=url)
        self.steps.append(self.curr_step)

    def _check_new_page(self, url: str) -> bool:
        """
        Method to check if a new page has been loaded.

        Parameters
        ----------
        url : str
            The URL of the new page.

        Returns
        -------
        bool
            True if a new page has been loaded, False otherwise.
        """
        if self.curr_step:
            if self.curr_step.url == url:
                return False
            if self.curr_step.url is None:
                self.curr_step.url = url
                return False

        if (prev_step := self.curr_step) is not None:
            prev_step.merge()

        return True
