from typing import List, Optional
import random

import reflex as rx

from trajlab.models import Task


class State(rx.State):
    """The app state."""

    count = 0
    tasks: Optional[List[Task]] = None

    def increment(self):
        """Increment the count."""
        self.count += 1

    def decrement(self):
        """Decrement the count."""
        self.count -= 1

    def random(self):
        """Randomize the count."""
        self.count = random.randint(0, 100)


def index() -> rx.Component:
    return rx.vstack(rx.foreach(State.get_trajectories, show_trajectory_menu_item))


# Add state and page to the app.
app = rx.App()
app.add_page(index, title="Counter")
app.compile()
