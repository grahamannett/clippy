import asyncio
import re
import shutil
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from loguru import logger
from playwright.async_api import expect

from clippy.run import Clippy
from tests.fixtures.fixture_cases import HNTestCase


class TestCapture(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        objective, start_page, test_task_output_dir = HNTestCase
        shutil.rmtree(test_task_output_dir, ignore_errors=True)
        self.clippy = Clippy(
            objective=objective,
            headless=True,
            start_page=start_page,
            data_dir=test_task_output_dir,
            key_exit=False,
        )
        self.delay = 100
        return super().setUp()

    async def asyncTearDown(self):
        if hasattr(self, "clippy"):
            try:
                await self.clippy.end_capture()
            except:
                pass

    async def test_capture_playwright(self):
        clippy, start_page = self.clippy, HNTestCase.start_page

        page = await clippy.start_capture(goto_start_page=True)
        logger.info("Capture Started")
        assert page.url == start_page

        await page.get_by_role("link", name="new", exact=True).click()
        event = clippy.wait_until("screenshot_event")
        await event
        assert len(clippy.capture.captured_screenshot_ids) == 2

        await page.wait_for_load_state("domcontentloaded")
        assert page.url == "https://news.ycombinator.com/newest"

        # generated selector: "getByRole('link', { name: 'comments', exact: true })"
        await page.get_by_role("link", name="comments", exact=True).click()
        # await page.wait_for_url("https://news.ycombinator.com/newcomments")
        assert page.url == "https://news.ycombinator.com/newcomments"

        logger.info("Need to wait for screenshot if we changed page...")
        await clippy.wait_until("screenshot_event")

        assert len(clippy.capture.captured_screenshot_ids) == 3
        await page.get_by_role("link", name="show", exact=True).click()

        await clippy.wait_until("screenshot_event")
        assert len(clippy.capture.captured_screenshot_ids) == 4

    async def test_capture_clippy(self):
        clippy = self.clippy
        clippy.headless = False
        clippy.objective = "go to the new posts page on hackernews"
        page = await clippy.start_capture(goto_start_page=True)

        action = await clippy.suggest_action()
        logger.info(f"Using action: {action}")
        await clippy.use_action(action)
        await clippy.wait_until("screenshot_event")
        logger.info("Check page title")

        await expect(page).to_have_url("https://news.ycombinator.com/newest")
        await clippy.end_capture()

    async def test_capture_steps(self):
        clippy = self.clippy
        clippy.objective = "buy bodywash on amazon"
        clippy.start_page = "https://google.com"
        clippy.headless = False

        page = await clippy.start_capture(goto_start_page=True)

        action = await clippy.suggest_action()

        assert action.action == "type"

        await clippy.use_action(action)
        await expect(page).to_have_title("body wash - Google Search")
        await clippy.wait_until("screenshot_event")
        # breakpoint()

        # HERE we should find an element in the page
        action = await clippy.suggest_action()
        await clippy.use_action(action)

    async def test_capture_actions(self) -> None:
        clippy = self.clippy
        clippy.start_page = "https://google.com"
        clippy.headless = False
        page = await clippy.start_capture()
        # breakpoint()
        await page.wait_for_load_state("domcontentloaded")
        locator = page.get_by_label("Search", exact=True)
        await locator.click()
        await locator.type("hotel in Boise Idaho", delay=self.delay)
        await page.keyboard.press("Enter", delay=self.delay)
        await clippy.wait_until("screenshot_event")

        # await page.type(text=

        element = page.get_by_text(
            "Top Hotels in Boise, ID - Cancel FREE on most hotelsHotels.comhttps://www.hotels"
        ).nth(0)
        element.scroll_into_view_if_needed(timeout=1000)
        await element.click()

        await expect(page).to_have_url(re.compile(".*hotels\.com.*"))

    async def test_clippy_google_search(self):
        clippy = self.clippy

        clippy.objective = "buy bodywash on amazon"
        clippy.start_page = "https://www.google.com/search?q=body+wash"

        page = await clippy.start_capture(goto_start_page=True)
        action = await clippy.suggest_action(previous_commands=["type input 9 body wash"])


class TestClippy(unittest.IsolatedAsyncioTestCase):
    def test_get_previous_actions(self):
        pass
