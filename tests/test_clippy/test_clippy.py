import asyncio
import shutil
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from loguru import logger
from playwright.async_api import expect

from clippy.run import Clippy
from src.clippy.instructor import Instructor
from tests.fixtures.cohere_responses import generation_responses

test_task_output_dir = "test_output/tasks"

objective = "find newest posts page on hackernews and then find the newest comments page"
start_page = "https://news.ycombinator.com/"


class TestCapture(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        shutil.rmtree(test_task_output_dir, ignore_errors=True)
        self.clippy = Clippy(
            objective=objective,
            headless=True,
            start_page=start_page,
            data_dir=test_task_output_dir,
            key_exit=False,
        )
        return super().setUp()

    async def asyncTearDown(self):
        if hasattr(self, "clippy"):
            await self.clippy.end_capture()

    async def test_capture_playwright(self):
        clippy = self.clippy

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

        # test wait_util
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
        breakpoint()

        await expect(page).to_have_title("New Links | Hacker News")

        logger.info(f"Suggest Action for {page.url[:50]}")
        action = await clippy.suggest_action()
        breakpoint()
        await clippy.use_action(action)
        await asyncio.sleep(1)

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
        # await asyncio.sleep(1)

    async def test_clippy_google_search(self):
        clippy = self.clippy

        clippy.objective = "buy bodywash on amazon"
        clippy.start_page = "https://www.google.com/search?q=body+wash"

        page = await clippy.start_capture(goto_start_page=True)
        action = await clippy.suggest_action(previous_commands=["type input 9 body wash"])


class TestClippy(unittest.IsolatedAsyncioTestCase):
    def test_get_previous_actions(self):
        pass


class TestMockedResponses(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        shutil.rmtree(test_task_output_dir, ignore_errors=True)
        super().setUp()

    @patch("src.clippy.instructor.CohereController.generate", new_callable=AsyncMock)
    async def test_use_action_mock(self, mock_generate: AsyncMock):
        # Define the mock response
        mock_generate.side_effect = generation_responses

        objective = "buy bodywash on amazon"
        start_page = "https://google.com"

        clippy = Clippy(
            objective=objective, headless=True, start_page=start_page, data_dir=test_task_output_dir, key_exit=False
        )

        await clippy.start_capture(goto_start_page=True)

        action = await clippy.suggest_action()

        await clippy.use_action(action)
        assert "https://www.google.com/search?q=body+wash" in clippy.url

        # Assert that the mock was called
        mock_generate.assert_called()

    @patch("src.clippy.instructor.CohereController.generate", new_callable=AsyncMock)
    async def test_capture_clippy(self, mock_generate: AsyncMock):
        import torch

        response_idx = 0
        responses = []
        while True:
            if Path(f"test_output/cohere_responses/{response_idx}.pt").exists():
                responses.append(torch.load(f"test_output/cohere_responses/{response_idx}.pt"))
                response_idx += 1
            else:
                break

        mock_generate.side_effect = responses

        # mock_generate.side_effect =

        clippy = Clippy(
            objective=objective,
            headless=True,
            start_page=start_page,
            data_dir=test_task_output_dir,
            key_exit=False,
        )
        # clippy.headless = True

        clippy.objective = "go to the new posts page on hackernews"

        page = await clippy.start_capture(goto_start_page=True)
        action = await clippy.suggest_action()

        logger.info(f"Using action: {action}")
        await clippy.use_action(action)
        await clippy.wait_until("screenshot_event")
        logger.info("Check page title")

        await expect(page).to_have_title("New Links | Hacker News")

        logger.info(f"Suggest Action for {page.url[:50]}")
        action = await clippy.suggest_action()
        await clippy.use_action(action)

        await asyncio.sleep(1)
