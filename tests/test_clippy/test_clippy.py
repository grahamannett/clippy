import unittest
import unittest.mock as mock

import torch
from clippy.capture.capture_async import CaptureAsync
from clippy.crawler.crawler import Crawler
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser

from clippy.instructor import Instructor, PageState
from clippy.run import Clippy


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


class TestCapture(unittest.IsolatedAsyncioTestCase):
    async def test_capture_start(self):
        capture = CaptureAsync(objective="buy soap", headless=False)
        crawler = Crawler()
