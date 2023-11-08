import asyncio
import unittest
from clippy.states import Task, Step, Actions, Input
from clippy.callback import Callback


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


class TestCallbacks(unittest.IsolatedAsyncioTestCase):
    async def test_async_callbacks(self):
        task = Task("testing task")
        callbacks = Callback()

        page_change = Step("https://www.page-start.com")
        page_change_sync = Step("https://www.page-sync-change.com")
        page_change_async = Step("https://www.page-change-async.com")
        page_change_async_after_callback = Step("https://www.page-change-async-after-callback.com")

        callback_check = {"sync": 0, "async": 0}

        def callback_fn(*args, **kwargs):
            callback_check["sync"] += 1

        async def callback_fn_async(*args, **kwargs):
            await asyncio.sleep(0.01)
            callback_check["async"] += 1

        # page change without callback added
        first_page_change = task.page_change(page_change)
        self.assertEqual(callback_check["sync"], 0)
        self.assertEqual(callback_check["async"], 0)

        # add callback but nothing should change
        callbacks.add_callback(callback=callback_fn, on=Task.page_change_async)
        self.assertEqual(callback_check["sync"], 0)
        self.assertEqual(callback_check["async"], 0)

        # make sure callback is not invoked yet for normal page change
        current_page_sync = task.page_change(page_change_sync)
        self.assertEqual(callback_check["sync"], 0)
        self.assertEqual(callback_check["async"], 0)
        self.assertEqual(current_page_sync.url, page_change_sync.url)

        # check that first callback is invoked
        current_page_async = await task.page_change_async(page_change_async)
        self.assertEqual(callback_check["sync"], 1)
        self.assertEqual(callback_check["async"], 0)
        self.assertEqual(current_page_async.url, page_change_async.url)

        # add async callback
        callbacks.add_callback(callback=callback_fn_async, on=Task.page_change_async)
        current_page_async_after = await task.page_change_async(page_change_async_after_callback)

        self.assertEqual(callback_check["sync"], 2)
        self.assertEqual(callback_check["async"], 1)
