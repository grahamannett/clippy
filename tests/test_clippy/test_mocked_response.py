import asyncio
import shutil
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from playwright.async_api import expect

from clippy import logger
from clippy.run import Clippy
from tests.fixtures.cohere_responses import generation_responses
from tests.fixtures.fixture_cases import test_output_dir

objective = "buy bodywash on amazon"
start_page = "https://google.com"


class TestMockedResponses(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        shutil.rmtree(test_output_dir, ignore_errors=True)
        super().setUp()

    @patch("src.clippy.instructor.CohereController.generate", new_callable=AsyncMock)
    async def test_use_action_mock(self, mock_generate: AsyncMock):
        # Define the mock response
        mock_generate.side_effect = generation_responses

        clippy = Clippy(
            objective=objective, headless=True, start_page=start_page, data_dir=test_output_dir, key_exit=False
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
            response_data_file = f"tests/fixtures/cohere_responses_data/{response_idx}.pt"
            if Path(response_data_file).exists():
                responses.append(torch.load(response_data_file))
                response_idx += 1
            else:
                break

        mock_generate.side_effect = responses

        # mock_generate.side_effect =

        clippy = Clippy(
            objective=objective,
            headless=True,
            start_page=start_page,
            data_dir=test_output_dir,
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
