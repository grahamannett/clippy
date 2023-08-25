import unittest


# from clippy.states.states import Step, Task
# from clippy.states.actions import Input, Action
from clippy.states import Step, Task, Actions, Input


class TestTask(unittest.TestCase):
    def test_dump(self):
        task = Task("testing task")
        out = task.dump()
        self.assertIsInstance(out, dict)
        self.assertEqual(out["steps"], [])

        step1 = Step("https://www.google.com")
        task.page_change(step1)

        type_action = Input(value="test", page_x=1, page_y=2)

        task(type_action)

        task(Actions["Click"](page_x=1, page_y=2, selector="a link"))

        out = task.dump()

        self.assertTrue(len(out["steps"]) > 0)
