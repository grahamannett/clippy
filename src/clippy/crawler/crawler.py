import asyncio
import os
import sys
from pathlib import Path
from typing import Awaitable, Callable, Coroutine, List

from loguru import logger

# async types and functions
from playwright.async_api import Browser, BrowserContext, CDPSession, Page
from playwright.async_api import PlaywrightContextManager


from clippy.crawler.selectors import Selector
from clippy import constants
from clippy.crawler.helpers import ainput, end_record, pause_crawler, all_cmd_input


class Crawler:
    """ideally i want to use crawler in async context manager but to make
    it possible to be used from so many places i need to think about how to do it"""

    async_tasks = {}
    browser: Browser
    ctx: BrowserContext
    page: Page
    cdp_client: CDPSession

    # js scripts or evals
    end_early_js: str = """() => {playwright.resume()}"""
    preload_injection_script: str = constants.default_preload_injection_script

    def __init__(
        self,
        is_async: bool = True,
        headless: bool = False,
        key_exit: bool = True,
    ):
        self._started = False
        self.is_async = is_async
        self.headless = headless
        self.key_exit = key_exit

    @staticmethod
    def sync_playwright():
        from playwright.sync_api import sync_playwright

        return sync_playwright

    @staticmethod
    def async_playwright():
        from playwright.async_api import async_playwright

        return async_playwright

    async def __aenter__(self):
        await self.start(use_instance_properties=True)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._end_async()

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

    async def pause(self, page: Page = None):
        if page is None:
            page = self.page
        await page.pause()

    async def pause_page_but_continue_crawler(self):
        self.add_async_task(self.pause())

    async def init_without_ctx_manager(self):
        self.ctx_manager = PlaywrightContextManager()
        self.pw = await self.ctx_manager.start()
        return self

    def _extra_background_tasks(self):
        self.add_async_task(all_cmd_input(self.page))
        self.add_async_task(pause_crawler(self.page, self))

    async def start(self, inject_preload: bool = True, key_exit: bool = None):
        self.is_async = True
        # ideally will make all this possible to use with then normal context manager
        # i.e. something like `with playwright as pw: self.pw = pw``
        await self.init_without_ctx_manager()
        # Selectors must be registered before creating the page.
        selectors = await asyncio.gather(*self.extend_selectors())
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.ctx = await self.browser.new_context()

        await self.ctx.route("**/*", lambda route: route.continue_())

        if inject_preload:
            await self.injection(ctx=self.ctx, script=self.preload_injection_script)

        self.page = await self.ctx.new_page()

        # if key_exit or self.key_exit:
        #     self.add_async_task(end_record(self.page, callback=self._end_async))

        self.cdp_client = await self.get_cdp_client()

        return self.page

    def get_cdp_client(self) -> Awaitable[CDPSession] | CDPSession:
        return self.page.context.new_cdp_session(self.page)

    def get_tree(self, cdp_snapshot_kwargs: dict, cdp_client: CDPSession = None) -> Awaitable[dict] | dict:
        cdp_client = cdp_client or self.cdp_client
        return cdp_client.send(
            "DOMSnapshot.captureSnapshot",
            cdp_snapshot_kwargs,
        )

    def extend_selectors(self):
        return Selector.register(self.pw)

    def injection(self, ctx: Browser | Page, script: str) -> Awaitable | None:
        return ctx.add_init_script(path=script)

    async def allow_end_early(self, end_early_str: str = "==press a key to exit=="):
        if not self.key_exit:
            return

        # not sure why but what i was prev using is broke:
        # asyncio.to_thread(sys.stdout.write, end_early_str)
        print(end_early_str)

        while line := await asyncio.to_thread(sys.stdin.readline):
            return await self.page.evaluate(self.end_early_js)

    async def add_background_task(self, fn: Awaitable, name: str = None):
        task = asyncio.create_task(fn)
        name = name or task.get_name()
        self.async_tasks[name] = task
        logger.info(f"added task {name}")

    def _check_if_instance_properties(self, use_instance_properties: bool, **kwargs):
        if use_instance_properties:
            # this makes it so we can use context manager and pass in args on init rather than here
            # could probably refactor part of this to be a classmethod instead
            start_page = self.start_page or start_page
            key_exit = self.key_exit if (self.key_exit != None) else key_exit
            headless = self.headless or headless

            # save them as well to the instance
            self.start_page = start_page
            self.key_exit = key_exit
            self.headless = headless
