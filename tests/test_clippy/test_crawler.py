import asyncio
from os import environ
from typing import Coroutine
import unittest
from clippy.controllers.apis.cohere_controller import CohereController
from clippy.crawler.crawler import Crawler
from playwright.async_api import async_playwright, expect


from clippy.constants import MILLI_SECOND as MS


from tests.utils import ServeSite


class TestServer(unittest.IsolatedAsyncioTestCase):
    async def test_server(self):
        with ServeSite("tests/fixtures/sites/simple", port=8081) as site:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(f"{site.url}/index.html")
                await page.get_by_text("Click Me for Results").click()
                await expect(page).to_have_title("Results Page")
                assert await page.title() == "Results Page"


class TestCrawler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.crawler = Crawler()

    async def asyncTearDown(self):
        await self.crawler.end()
        return await super().asyncTearDown()

    async def test_locator(self):
        with ServeSite("tests/fixtures/sites/simple", port=8081) as site:
            crawler = self.crawler
            await crawler.start()
            await crawler.page.goto(f"{site.url}/index.html")
            await asyncio.sleep(3)

    async def test_using_page_api(self):
        crawler = self.crawler
        await crawler.start()

        # await crawler.pause_page_but_continue_crawler()
        page = crawler.page
        await page.goto("https://www.google.com")

        await page.get_by_role("combobox", name="Search").fill("nail polish")
        await page.get_by_role("combobox", name="Search").press("Enter")
        await page.wait_for_url(
            "https://www.google.com/search?q=nail+polish**", timeout=10 * MS, wait_until="domcontentloaded"
        )
        await page.get_by_role("link", name="Nail Polish Amazon.com https://www.amazon.com").first.click()
        await page.wait_for_url("https://www.amazon.com/**", timeout=10 * MS, wait_until="domcontentloaded")
        await page.get_by_role("link", name="Gel Nail Polish").first.click()
        await page.wait_for_url("https://www.amazon.com/**", timeout=10 * MS, wait_until="domcontentloaded")
        await page.get_by_title("Add to Shopping Cart").click()
        await page.wait_for_url("https://www.amazon.com/cart/**", timeout=10 * MS, wait_until="domcontentloaded")
        # await page.get_by_role("button", name="Submit").click()
        await page.get_by_role("button", name="Proceed to checkout").click()
        await page.wait_for_url("https://www.amazon.com/ap/**", timeout=10 * MS, wait_until="domcontentloaded")
