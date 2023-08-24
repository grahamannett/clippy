from collections import UserDict
from typing import Any, Dict, List
from dataclasses import asdict, dataclass

import json
from playwright.async_api import ConsoleMessage, Frame, Page
from playwright.sync_api import Frame as FrameSync
from playwright.sync_api import Page as PageSync

from enum import Enum

# NOTE: Using camelCase so it matches more closely with js


class ActionBase:
    prev: "Action" = None
    data: Any = None
    allow_merge: bool = False
    # data["type"] = self.__class__.__name__

    def __post_init__(self):
        """will be called in all dataclasses"""
        pass

    @classmethod
    def factory(cls, class_name: str, data: List[str]):
        return cls[class_name](**data)

    def should_merge(self, action: "Action"):
        same_type = type(self) == type(action)
        if same_type and hasattr(self, "check_merge"):
            _check_merge = self.check_merge(action)
            return same_type and self.allow_merge and _check_merge

        return same_type and self.allow_merge

    def __repr__(self) -> str:
        data = ["=".join([key, val]) for key, val in self.__dict__.items() if key != "prev"]
        return f"{self.__class__.__name__} || ({', '.join(data)})"

    def callback(self, *args, **kwargs):
        pass

    async def async_callback(self, *args, **kwargs):
        pass


class Action(ActionBase):
    """
    - why is this not just ActionBase? prevent the sub-actions from having stuff like Input.Input or Click['Click']
    Maybe could be useful but keep out for now
    """

    Click: Click = Click
    Input: Input = Input
    Enter: Enter = Enter
    Wheel: Wheel = Wheel

    def __class_getitem__(cls, class_name: str):
        return cls.__dict__[class_name]

    @classmethod
    def get_types(cls):
        # WARNING: prefer to use ActionTypes[] instead as its faster
        return {s.__name__: s for s in cls.__subclasses__()}


@dataclass
class BoundingBox:
    x: float
    y: float

    width: float
    height: float

    bottom: float
    top: float

    left: float
    right: float

    scrollX: float
    scrollY: float

    def scale(self, scale: float):
        width = int(self.width * scale)
        height = int(self.height * scale)

        x = self.x - int((width - self.width) / 2)
        y = self.y - int((height - self.height) / 2)

        if (x < 0) or (y < 0):
            print("WARNING: negative value... not sure if ss is correct")

        return BoundingBox(x, y, width, height)

    def to_dict(self):
        return asdict(self)


@dataclass
class Click(ActionBase):
    page_x: int = None
    page_y: int = None
    selector: str = None
    python_locator: str = None
    bounding_box: BoundingBox | str = None

    def __post_init__(self):
        super().__post_init__()
        self.position = (self.page_x, self.page_y)

        if self.bounding_box:
            if isinstance(self.bounding_box, str):
                self.bounding_box = json.loads(self.bounding_box)

            self.bounding_box = BoundingBox(**self.bounding_box)

    async def async_callback(self, page: Page, path: str):
        element = page.locator(self.selector)
        screenshot = await element.screenshot(path=path)

    async def capture_element(self, page: Page, path: str, scale: float = 1.0):
        # elements = page.locator(self.selector).all()
        elements = page.locator(self.selector).first()
        # if len(elements := await page.locator(self.selector).all()) > 1:
        if elements is None:
            print("WARNING: NO ELEMENT FOUND FOR SCREENSHOT")
            return

            # print("WARNING: multiple elements found for screenshot... not sure if selector is correct")
        element = elements[0]

        if element is None:
            print("WARNING: element not found for screenshot")
            return None
        bbox = await element.bounding_box()

        bbox = BoundingBox(**bbox)
        screenshot = await page.screenshot(path=path, clip=bbox.scale(scale).to_dict())
        return screenshot


@dataclass
class Input(ActionBase):
    value: str = None
    page_x: int = None
    page_y: int = None

    def __post_init__(self):
        super().__post_init__()
        self.position = (self.page_x, self.page_y)
        self.allow_merge = True

    def update(self, action: "Input"):
        self.value = action.value

    def check_merge(self, action: "Input"):
        return self.position == action.position


@dataclass
class Enter(ActionBase):
    value: str = None


@dataclass
class Wheel(ActionBase):
    deltaX: int = None
    deltaY: int = None

    def __post_init__(self):
        super().__post_init__()
        self.allow_merge = True

    def update(self, action: "Wheel"):
        self.deltaX += action.deltaX
        self.deltaY += action.deltaY

    def merge(self, actions: List["Wheel"]):
        for action in actions:
            self.update(action)


# Make This A Class For Type Hinting
# class ActionTypes(Enum):
#     Click = Click
#     Input = Input
#     Enter = Enter
#     Wheel = Wheel


# class ActionTypes(object):
#     Click: Click = Click
#     Input: Input = Input
#     Enter: Enter = Enter
#     Wheel: Wheel = Wheel

#     def __class_getitem__(cls, class_name: str):
#         return cls.__dict__[class_name]
