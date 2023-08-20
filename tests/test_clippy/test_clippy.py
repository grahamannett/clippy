import unittest
import unittest.mock as mock

import torch
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser

from clippy.instructor import Instructor, PageState
from clippy.main import Clippy


class TestClippy(unittest.TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def test_buy(self):
        objective = "buy expensive candles"

        clippy = Clippy(objective=objective, headless=True)

        clippy.start()

        state = clippy.state

        mock_args = ["n", "type"]

        with mock.patch("builtins.input") as mocked_input:
            mocked_input.side_effect = mock_args
            state = clippy.step(state)
            self.assertEqual(
                state.response.cmd,
            )


class TestInstructor(unittest.IsolatedAsyncioTestCase):
    def test_suggest_from_fixture(self):
        instructor = Instructor(use_async=True)
        filepath = "tests/fixtures/soap/llm-assist.pt"
        data = torch.load(filepath)
        pel = data["page_elements"]

        pelb = data["page_element_buffer"]
        pel_ids = data["page_elements_ids"]
        url = data["url"]
        objective = "buy soap"

        url = url[:100]
        pel = pel[:20]

        instructor = Instructor()
        import time

        state = PageState(url=url, page_elements=pel)
        # state =

    async def test_show_suggest_on_page(self):
        url = "https://www.google.com/search?q=hand+soap"
        objective = "buy hand soap"
        instructor = Instructor(objective=objective, use_async=True)
        dom_parser = DOMSnapshotParser(keep_device_ratio=False)
        # page = await Crawler.get_page(url)
        async with Crawler(start_page=url, headless=False, key_exit=False) as crawler:
            page = crawler.page
            cdp_client = await crawler.get_cdp_client()
            await instructor.
            # tree = await crawler.get_tree(dom_parser.cdp_snapshot_kwargs, cdp_client=cdp_client)
            # self.assertIsNotNone(tree)


    async def test_scoring_actions(self):
        instructor = Instructor(use_async=True)

        scored_actions = await instructor.compare_all_page_elements(
            objective="made up objective", page_elements=["link 1", "link 2", "link 3"]
        )
        breakpoint()
