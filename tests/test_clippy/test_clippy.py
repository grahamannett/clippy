import unittest
import unittest.mock as mock
import asyncio
from loguru import logger


from clippy.run import Clippy

import shutil

test_task_output_dir = "test_output/tasks"

objective = "find newest posts page on hackernews and then find the newest comments page"
start_page = "https://news.ycombinator.com/"


class TestCapture(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        shutil.rmtree(test_task_output_dir, ignore_errors=True)
        self.clippy = Clippy(objective=objective, headless=False, start_page=start_page, data_dir=test_task_output_dir)
        return super().setUp()

    async def asyncTearDown(self):
        if hasattr(self, "clippy"):
            await self.clippy.end_capture()

    async def test_capture_using_page(self):
        # clippy = Clippy(objective=objective, headless=False, start_page=start_page, data_dir=test_task_output_dir)

        clippy = self.clippy
        logger.info("Made Clippy")

        page = await clippy.start_capture(key_exit=False, goto_start_page=True)
        logger.info("Capture Started")
        # await page.goto(start_page)
        # logger.info("Goto Start Page")
        assert page.url == start_page

        await page.get_by_role("link", name="new", exact=True).click()
        await page.wait_for_load_state("domcontentloaded")
        assert page.url == "https://news.ycombinator.com/newest"

        # generated selector: "getByRole('link', { name: 'comments', exact: true })"
        await page.get_by_role("link", name="comments", exact=True).click()
        await page.wait_for_url("https://news.ycombinator.com/newcomments")
        assert page.url == "https://news.ycombinator.com/newcomments"

        logger.info("Need to wait for screenshot if we changed page...")
        await clippy.wait_until("screenshot_event")

        assert len(clippy.capture.captured_screenshot_ids) == 3
        await page.get_by_role("link", name="show", exact=True).click()

        # test wait_util
        await clippy.wait_until("screenshot_event")
        assert len(clippy.capture.captured_screenshot_ids) == 4

    async def test_capture_assist(self):
        clippy = self.clippy

        page = await clippy.start_capture(key_exit=False, goto_start_page=True)
        await clippy.suggest_action()


class TestClippy(unittest.IsolatedAsyncioTestCase):
    pass
    # async def test_capture_start(self):
    #     capture = CaptureAsync(objective="buy soap", headless=False)
    #     crawler = Crawler()
