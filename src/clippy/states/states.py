import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, List, Tuple

from playwright.async_api import Frame, Page
from playwright.sync_api import Frame as FrameSync
from playwright.sync_api import Page as PageSync

from clippy.states.actions import Action
from clippy.states.base import ModelBase

short_url_n = 100  # if None will print whole


# im using id which is a reserved word but without that
@dataclass
class Step(ModelBase):
    url: str | None
    id: str | uuid.UUID = None
    actions: List[Action] = field(default_factory=list)

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid5(uuid.NAMESPACE_URL, self.url))

    def __call__(self, action: Action, **kwargs):
        self.actions.append(action)

    def __repr__(self):
        actions = "\n".join(["\t\t" + "-" + str(a) for a in self.actions])
        return f"\tPage: {self.url}\n{actions}"

    @classmethod
    def from_dict(cls, data: dict):
        if len(data["actions"]) == 0:
            return None

        actions = data.pop("actions")
        step = cls(**data)

        for action_dict in actions:
            ActType = Action[action_dict.pop("type")]
            action = ActType(**action_dict)
            step.actions.append(action)
        return step

    @property
    def n_actions(self):
        return len(self.actions)

    def merge(self):
        if len(self.actions) < 2:
            return

        merged_actions = [self.actions.pop(0)]

        for idx, action in enumerate(self.actions):
            if merged_actions[-1].should_merge(action):
                merged_actions[-1].update(action)
            else:
                merged_actions.append(action)

        self.actions = merged_actions

    def format_url(self):
        url = self.url or self.id
        if (short_url_n is not None) and (len(url) > short_url_n):
            url = self.url[:short_url_n] + "..."
        return url

    def print(self):
        url = self.format_url()

        print(f"\n===\nprinting step:{url}")
        for action in self.actions:
            print(action)


@dataclass
class Task(ModelBase):
    objective: str
    id: str | None = str(uuid.uuid4())
    steps: List[Step] = field(default_factory=list)
    curr_step: Step = None
    timestamp: datetime | str = str(datetime.now())

    def __call__(self, action: Action, **kwargs):
        if not isinstance(action, Action):
            raise ValueError(f"action must be of type Action, not {type(action)}")

        self.curr_step(action, **kwargs)

    def __repr__(self):
        steps_info = "\n".join([f"{s}" for s in self.steps])
        return f"Task: {self.objective} | {len(self.steps)} steps \n{steps_info}"

    @property
    def current(self):
        return self.curr_step

    @current.setter
    def current(self, step: Step):
        self.curr_step = step
        self.steps.append(step)

    @classmethod
    def from_dict(cls, data: dict):
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
    def n_steps(self):
        return len(self.steps)

    @property
    def n_actions(self):
        return sum([step.n_actions for step in self.steps])

    def print(self):
        return self.__repr__()

    async def page_change_async(self, page: Page | Frame | str):
        self.page_change(page=page)

    def page_change(self, page: Page | Frame = None, url: str = None):
        if page:
            url = page.url

        if self._check_new_page(url) is False:
            return

        self.curr_step = Step(url=url)
        self.steps.append(self.curr_step)

    def _check_new_page(self, url: str):
        if self.curr_step:
            if self.curr_step.url == url:
                return False
            if self.curr_step.url is None:
                self.curr_step.url = url
                return False

        if (prev_step := self.curr_step) is not None:
            prev_step.merge()

        return True
