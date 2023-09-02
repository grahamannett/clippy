import asyncio
import os
import sys
from pathlib import Path
from typing import Awaitable, Callable, Coroutine, List

from loguru import logger

# async types and functions
from playwright.async_api import Browser, BrowserContext, CDPSession, Page, PlaywrightContextManager

from clippy import constants
from clippy.crawler.selectors import Selector


class Crawler:
    """ideally i want to use crawler in async context manager but to make
    it possible to be used from so many places i need to think about how to do it"""

    async_tasks = {"pause": None}
    browser: Browser
    ctx: BrowserContext
    page: Page
    cdp_client: CDPSession

    # js scripts or evals
    end_early_js: str = "() => {playwright.resume()}"
    preload_injection_script: str = constants.default_preload_injection_script

    input_delay: int = 100

    def __init__(
        self,
        is_async: bool = True,
        headless: bool = False,
        clippy: "Clippy" = None,
    ):
        self._started = False
        self.is_async = is_async
        self.headless = headless
        self.clippy = clippy

    async def __aenter__(self):
        await self.start(use_instance_properties=True)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._end_async()

    @property
    def url(self):
        return self.page.url

    @property
    def pause_task(self) -> asyncio.Task:
        if (task := self.async_tasks["pause"]) is None:
            task = self.pause()
        return task

    def pause(self, page: Page = None) -> asyncio.Task:
        if task := self.async_tasks["pause"]:
            return task

        page = page or self.page
        return self.add_background_task(page.pause(), name="pause")

    async def _end_async(self):
        if self.cdp_client:
            await self.cdp_client.detach()

        await self.page.close()
        await self.browser.close()
        await self.ctx_manager.__aexit__()

    def _end_sync(self):
        if self.cdp_client:
            self.cdp_client.detach()
        self.page.close()
        self.browser.close()
        self.ctx_manager.__exit__()

    def end(self) -> Awaitable[None] | None:
        return self._end_async() if self.is_async else self._end_sync()

    async def init_without_ctx_manager(self):
        self.ctx_manager = PlaywrightContextManager()
        self.pw = await self.ctx_manager.start()
        return self

    async def start(self, inject_preload: bool = True):
        self.is_async = True
        # ideally will make all this possible to use with then normal context manager
        # i.e. something like `with playwright as pw: self.pw = pw``
        await self.init_without_ctx_manager()
        # Selectors must be registered before creating the page.
        self.selectors = await asyncio.gather(*self.extend_selectors())
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.ctx = await self.browser.new_context()

        await self.ctx.route("**/*", lambda route: route.continue_())

        if inject_preload:
            await self.injection(ctx=self.ctx, script=self.preload_injection_script)

        self.page = await self.ctx.new_page()

        self.cdp_client = await self.get_cdp_client()
        return self.page

    def get_cdp_client(self) -> Awaitable[CDPSession] | CDPSession:
        return self.page.context.new_cdp_session(self.page)

    def extend_selectors(self):
        return Selector.register(self.pw)

    def injection(self, ctx: Browser | Page, script: str) -> Awaitable | None:
        return ctx.add_init_script(path=script)

    async def allow_end_early(self, end_early_str: str = "==press a key to exit=="):
        # not sure why but what i was prev using is broke:
        # asyncio.to_thread(sys.stdout.write, end_early_str)
        if getattr(self.clippy, "DEBUG", False):
            return

        print(end_early_str)

        while line := await asyncio.to_thread(sys.stdin.readline):
            return await self.page.evaluate(self.end_early_js)

    def add_background_task(self, fn: Awaitable, name: str = None) -> asyncio.Task:
        task = asyncio.create_task(fn)
        name = name or task.get_name()
        self.async_tasks[name] = task
        logger.info(f"added task {name}")
        return task

    def _check_if_instance_properties(self, use_instance_properties: bool, **kwargs):
        if use_instance_properties:
            # this makes it so we can use context manager and pass in args on init rather than here
            # could probably refactor part of this to be a classmethod instead
            start_page = self.start_page or start_page
            headless = self.headless or headless

            # save them as well to the instance
            self.start_page = start_page
            self.headless = headless

    async def page_size(self):
        device_pixel_ratio = await self.page.evaluate("window.devicePixelRatio")
        win_scroll_x = await self.page.evaluate("window.scrollX")
        win_scroll_y = await self.page.evaluate("window.scrollY")
        win_upper_bound = await self.page.evaluate("window.pageYOffset")
        win_left_bound = await self.page.evaluate("window.pageXOffset")
        win_width = await self.page.evaluate("window.screen.width")
        win_height = await self.page.evaluate("window.screen.height")
        return (device_pixel_ratio, win_scroll_x, win_scroll_y, win_upper_bound, win_left_bound, win_width, win_height)

    async def execute_action(self, action: "NextAction"):
        _actions = {
            "type": self.execute_type,
            "click": self.execute_click,
        }

        await _actions[action.action](action)

    async def execute_click(self, action: "NextAction", **kwargs):
        loc = action.locator.nth(0)
        await loc.click(delay=self.input_delay)
        await self.page.wait_for_load_state(timeout=500)

    async def execute_type(self, action: "NextAction", **kwargs):
        await self.execute_click(action)
        await self.page.keyboard.type(action.action_args, delay=self.input_delay)

        # TODO: i should ask for next action after typing, NOT just press enter
        await self.page.keyboard.press("Enter")

    @staticmethod
    def sync_playwright():
        from playwright.sync_api import sync_playwright

        return sync_playwright

    @staticmethod
    def async_playwright():
        from playwright.async_api import async_playwright

        return async_playwright
