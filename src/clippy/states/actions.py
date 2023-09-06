import json
from dataclasses import asdict, dataclass
from typing import Any, Awaitable, List, Type

from playwright.async_api import Page

# NOTE: Using camelCase so it matches more closely with js


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


@dataclass
class Position:
    """
    A class to represent a position with x and y coordinates.
    """

    x: int | float = None  # x-coordinate
    y: int | float = None  # y-coordinate


@dataclass
class BoundingBox:
    """
    A class to represent a bounding box.
    """

    x: float  # x-coordinate
    y: float  # y-coordinate

    width: float  # Width of the bounding box
    height: float  # Height of the bounding box

    bottom: float  # Bottom coordinate of the bounding box
    top: float  # Top coordinate of the bounding box

    left: float  # Left coordinate of the bounding box
    right: float  # Right coordinate of the bounding box

    scrollX: float  # Scroll position in the x-direction
    scrollY: float  # Scroll position in the y-direction

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
        width = int(self.width * scale)
        height = int(self.height * scale)

        x = self.x - int((width - self.width) / 2)
        y = self.y - int((height - self.height) / 2)

        if (x < 0) or (y < 0):
            print("WARNING: negative value... not sure if ss is correct")

        return BoundingBox(x, y, width, height)

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
class Click(Action):
    """
    A class to represent a click action.
    """

    x: int = None  # x-coordinate of the click
    y: int = None  # y-coordinate of the click
    selector: str = None  # Selector of the element to click
    python_locator: str = None  # Python locator of the element to click
    bounding_box: BoundingBox | str = None  # Bounding box of the element to click

    def __post_init__(self):
        """
        Method called after initialization of the Click instance.
        """
        super().__post_init__()
        self.position = Position(self.x, self.y)

        if self.bounding_box:
            if isinstance(self.bounding_box, str):
                self.bounding_box = json.loads(self.bounding_box)

            self.bounding_box = BoundingBox(**self.bounding_box)

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
        elements = await page.locator(self.selector).all()

        if elements is None:
            print("WARNING: NO ELEMENT FOUND FOR SCREENSHOT")
            return

            # print("WARNING: multiple elements found for screenshot... not sure if selector is correct")
        element = elements[0]

        if element is None:
            print("WARNING: element not found for screenshot")
            return None

        bbox = BoundingBox(**(await element.bounding_box()))
        screenshot = await page.screenshot(path=path, clip=bbox.scale(scale).to_dict())
        return screenshot


@dataclass
class Input(Action):
    """
    A class to represent an input action.
    """

    value: str = None  # The value to input
    x: int = None  # x-coordinate of the input
    y: int = None  # y-coordinate of the input

    def __post_init__(self):
        """
        Method called after initialization of the Input instance.
        """
        super().__post_init__()
        self.position = Position(self.x, self.y)
        self.allow_merge = True

    def update(self, action: "Input"):
        """
        Updates the value of the input.

        Parameters
        ----------
        action : Input
            The action to update the value from.
        """
        self.value = action.value

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
class Enter(Action):
    """
    A class to represent an enter action.
    """

    value: str = None  # The value to enter


@dataclass
class Wheel(Action):
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

    def update(self, action: "Wheel"):
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

    def __new__(cls, class_name: str, *args, **kwargs) -> Action:
        breakpoint()

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
