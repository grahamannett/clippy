import unittest
from clippy.states import Task, Step, Actions, Input


class TestTask(unittest.TestCase):
    def test_task(self):
        task = Task("testing task")
        self.assertEqual(task.objective, "testing task")
        self.assertEqual(task.steps, [])

        step1 = Step("https://www.google.com")
        task.page_change(step1)
        self.assertEqual(len(task.steps), 1)

        type_action = Input(value="test", x=1, y=2)
        task(type_action)
        self.assertEqual(len(task.steps[0].actions), 1)

        task(Actions["Click"](x=1, y=2, selector="a link"))
        self.assertEqual(len(task.steps[0].actions), 2)

    def test_merge(self):
        action1 = Actions.Click(x=1, y=2, selector="a link")
        action2 = Actions.Click(x=3, y=4, selector="another link")
        self.assertFalse(action1.should_merge(action2))

        action3 = Actions.Input(value="test", x=5, y=6)
        self.assertFalse(action1.should_merge(action3))

        action4 = Actions.Input(value="another test", x=5, y=6)
        self.assertTrue(action3.should_merge(action4))
