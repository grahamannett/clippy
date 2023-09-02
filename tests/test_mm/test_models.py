import unittest
from playwright.async_api import async_playwright

from ..utils import ServeSite


class TestModel(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Start the SimpleHTTPServer in a separate thread
        cls.server = ServeSite()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.end()
        return super().tearDownClass()

    async def test_example(self):
        # Use the server's address as the base URL for your Playwright tests
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(f"http://localhost:{self.server.PORT}/tests/fixtures/sites/news.ycombinator.com/index.html")


if __name__ == "__main__":
    unittest.main()
