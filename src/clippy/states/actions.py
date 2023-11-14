from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Awaitable, List, Optional, Type

from playwright.async_api import Locator, Page


# these are dataclasses rather than named tuple so I can attach objects to them
@dataclass
class NextAction:
    action: str
    element_id: int = None
    element_metadata: str = None
    action_args: str = None

    locator: Locator = None
    # needed if we score all actions
    score: float = None

    def __eq__(self, __value: object) -> bool:
        return self.action == __value

    def is_scroll(self) -> bool:
        """Check if the action is 'scrolldown'."""
        return (self.action == "scrolldown") or (self.action == "scrollup")

    def is_done(self) -> bool:
        """Check if the action is 'done'."""
        return self.action == "done"

    def format(self):
        """format the action for printing"""
        return f"{self.action}({self.element_id}, {self.element_metadata}, {self.action_args})"


@dataclass
class ActionMetadata:
    """action metadata class.
    seperate from action as it needs to have @dataclass but do not want to include
    the other various fields e.g. prev, data, allow_merge
    """

    action_type: str = field(default=None, repr=False)
    timestamp: str = field(default=None, repr=False)

    def __post_init__(self):
        self.action_type = self.__class__.__name__.lower()
        self.timestamp = str(datetime.now())


class Action:
    """
    Base class for all actions.
    """

    prev: "Action" = None  # Previous action
    data: Any = None  # Data associated with the action
    allow_merge: bool = False  # Flag to allow merging of actions

    def __post_init__(self):
        """
        Method called after initialization of dataclasses.
        """
        pass

    @classmethod
    def factory(cls, class_name: str, data: List[str]) -> "Action":
        """
        Factory method to create an Action instance.

        Parameters
        ----------
        class_name : str
            The name of the class to create an instance of.
        data : List[str]
            The data to pass to the class constructor.

        Returns
        -------
        Action
            An instance of the specified class.
        """
        return cls[class_name](**data)

    def should_merge(self, action: "Action") -> bool:
        """
        Determines if the current action should be merged with the provided action.

        Parameters
        ----------
        action : Action
            The action to potentially merge with.

        Returns
        -------
        bool
            True if the actions should be merged, False otherwise.
        """
        if same_type := (type(self) == type(action)) and hasattr(self, "check_merge"):
            return same_type and self.allow_merge and self.check_merge(action)

        return same_type and self.allow_merge

    def __repr__(self) -> str:
        """
        Returns a string representation of the Action instance.

        Returns
        -------
        str
            A string representation of the Action instance.
        """
        data = ["=".join([key, val]) for key, val in self.__dict__.items() if key != "prev"]
        return f"{self.__class__.__name__} || ({', '.join(data)})"

    def callback(self, *args, **kwargs):
        """
        Placeholder for callback method.
        """
        pass

    def update(self, action: "Action") -> "Action":
        """base function to update an action"""
        return self


@dataclass
class Position(ActionMetadata):
    """
    A class to represent a position with x and y coordinates.
    """

    x: int | float = None  # x-coordinate
    y: int | float = None  # y-coordinate


@dataclass
class BoundingBox(ActionMetadata):
    """
    A class to represent a bounding box.
    """

    x: Optional[float] = None  # x-coordinate
    y: Optional[float] = None  # y-coordinate

    width: Optional[float] = None  # Width of the bounding box
    height: Optional[float] = None  # Height of the bounding box

    bottom: Optional[float] = None  # Bottom coordinate of the bounding box
    top: Optional[float] = None  # Top coordinate of the bounding box

    left: Optional[float] = None  # Left coordinate of the bounding box
    right: Optional[float] = None  # Right coordinate of the bounding box

    scroll_x: Optional[float] = None  # Scroll position in the x-direction
    scroll_y: Optional[float] = None  # Scroll position in the y-direction

    def scale(self, scale: float) -> "BoundingBox":
        """
        Scales the bounding box by a given factor.

        Parameters
        ----------
        scale : float
            The factor to scale the bounding box by.

        Returns
        -------
        BoundingBox
            The scaled bounding box.
        """
        assert self.width and self.height and self.x and self.y
        width = int(self.width * scale)
        height = int(self.height * scale)

        x = self.x - int((width - self.width) / 2)
        y = self.y - int((height - self.height) / 2)

        if (x < 0) or (y < 0):
            print("WARNING: negative value... not sure if screenshot is correct")

        return BoundingBox(x=x, y=y, width=width, height=height)

    def to_dict(self) -> dict:
        """
        Converts the bounding box to a dictionary.

        Returns
        -------
        dict
            The bounding box as a dictionary.
        """
        return asdict(self)


@dataclass
class Click(ActionMetadata, Action):
    """
    A class to represent a click action.
    """

    x: Optional[int] = None  # x-coordinate of the click
    y: Optional[int] = None  # y-coordinate of the click
    selector: Optional[str] = None  # Selector of the element to click
    python_locator: Optional[str] = None  # Python locator of the element to click
    bounding_box: Optional[BoundingBox | str | dict] = None  # Bounding box of the element to click

    def __post_init__(self):
        """
        Method called after initialization of the Click instance.
        """
        super().__post_init__()
        self.position = Position(self.x, self.y)

        if self.bounding_box:
            if isinstance(self.bounding_box, str):
                self.bounding_box = json.loads(self.bounding_box)

            if isinstance(self.bounding_box, dict):
                self.bounding_box = BoundingBox(**self.bounding_box)

    def format_for_llm(self, element_id: int, **kwargs) -> str:
        return f"click {element_id}"

    def callback(self, page: Page, path: str) -> Awaitable:
        """
        Asynchronous callback method for the Click instance.

        Parameters
        ----------
        page : Page
            The page to perform the click on.
        path : str
            The path to save the screenshot to.
        """
        if not self.selector:
            raise ValueError("No selector on click for callback")

        element = page.locator(self.selector)
        return element.screenshot(path=path)

    async def capture_element(self, page: Page, path: str, scale: float = 1.0):
        """
        Captures a screenshot of the element to click.

        Parameters
        ----------
        page : Page
            The page to capture the screenshot on.
        path : str
            The path to save the screenshot to.
        scale : float, optional
            The scale factor for the screenshot, by default 1.0
        """
        # elements = page.locator(self.selector).all()
        if not self.selector:
            raise ValueError("No selector on click for capture element")

        elements = await page.locator(self.selector).all()

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
class Input(ActionMetadata, Action):
    """
    A class to represent an input action.
    """

    value: Optional[str] = None  # The value to input
    x: Optional[int] = None  # x-coordinate of the input
    y: Optional[int] = None  # y-coordinate of the input

    def __post_init__(self):
        """
        Method called after initialization of the Input instance.
        """
        super().__post_init__()
        self.position = Position(self.x, self.y)
        self.allow_merge = True

    def format_for_llm(self, **kwargs) -> str:
        return f'type "{self.value}"'

    def update(self, action: "Input") -> "Input":
        """
        Updates the value of the input.

        Parameters
        ----------
        action : Input
            The action to update the value from.
        """
        self.value = action.value
        return self

    def check_merge(self, action: "Input") -> bool:
        """
        Checks if the input action can be merged with another.

        Parameters
        ----------
        action : Input
            The action to check for mergeability.

        Returns
        -------
        bool
            True if the actions can be merged, False otherwise.
        """
        return self.position == action.position


@dataclass
class Enter(ActionMetadata, Action):
    """
    A class to represent an enter action.
    """

    value: str = None  # The value to enter

    def format_for_llm(self, **kwargs) -> str:
        return f"press enter"


@dataclass
class Wheel(ActionMetadata, Action):
    """
    A class to represent a wheel action.
    """

    delta_x: int = None  # The change in x-coordinate
    delta_y: int = None  # The change in y-coordinate

    def __post_init__(self):
        """
        Method called after initialization of the Wheel instance.
        """
        super().__post_init__()
        self.allow_merge = True

    def update(self, action: "Wheel") -> "Wheel":
        """
        Updates the delta values of the wheel action.

        Parameters
        ----------
        action : Wheel
            The action to update the delta values from.
        """
        self.delta_x += action.delta_x
        self.delta_y += action.delta_y

    def merge(self, actions: List["Wheel"]):
        """
        Merges a list of wheel actions.

        Parameters
        ----------
        actions : List[Wheel]
            The list of actions to merge.
        """
        for action in actions:
            self.update(action)


class Actions(Action):
    """
    A class to represent a collection of actions. This class is used to prevent the
    sub-actions from having stuff like Input.Input or Click['Click'].
    It may be useful in the future, but is kept out for now.
    """

    Click: Type[Click] = Click  # Type hint for Click action
    Input: Type[Input] = Input  # Type hint for Input action
    Enter: Type[Enter] = Enter  # Type hint for Enter action
    Wheel: Type[Wheel] = Wheel  # Type hint for Wheel action

    # to allow Actions.Action for type hinting/isinstance
    Action: Type[Action] = Action  # Type hint for Action

    def __new__(cls, action_type: str, *args, **kwargs) -> Action:
        return cls.__dict__[action_type](*args, **kwargs)

    def __class_getitem__(cls, class_name: str) -> Type[Action]:
        """
        Method to get the class of a specific action.

        Parameters
        ----------
        class_name : str
            The name of the action class to get.

        Returns
        -------
        Type[Action]
            The class of the specified action.
        """
        return cls.__dict__[class_name]
