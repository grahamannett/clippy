from __future__ import annotations

import asyncio
import sys
from typing import Awaitable, Callable, Sequence

from loguru import logger
from playwright.async_api import Browser, BrowserContext, CDPSession, Page, PlaywrightContextManager

from clippy.constants import (
    default_preload_injection_script,
    default_user_agent,
    default_viewport_size,
    input_delay,
    END_EARLY_STR,
)
from clippy.crawler.selectors import Selector
from clippy.states.actions import NextAction


class Crawler:
    """ideally i want to use crawler in async context manager but to make
    it possible to be used from so many places i need to think about how to do it"""

    async_tasks = {"crawler_pause": None}
    browser: Browser
    page: Page
    ctx: BrowserContext
    cdp_client: CDPSession

    # js scripts or evals
    end_early_js: str = "() => {playwright.resume()}"
    preload_injection_script: str = default_preload_injection_script

    input_delay: int = input_delay

    def __init__(
        self,
        is_async: bool = True,
        headless: bool = False,
        clippy: Clippy = None,
    ) -> None:
        self._started = False
        self.is_async = is_async
        self.headless = headless
        self.clippy = clippy

        if self.clippy:
            self.async_tasks = self.clippy.async_tasks
            self.async_tasks["crawler_pause"] = None

    async def __aenter__(self) -> Crawler:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._end_async()

    @staticmethod
    def sync_playwright():
        from playwright.sync_api import sync_playwright

        return sync_playwright

    @staticmethod
    def async_playwright():
        from playwright.async_api import async_playwright

        return async_playwright

    @property
    def title(self):
        return self.page.title()

    @property
    def url(self):
        return self.page.url

    @property
    def pause_task(self) -> asyncio.Task:
        if (task := self.async_tasks["crawler_pause"]) is None:
            task = self.pause()
        return task

    def pause(self, page: Page | None = None) -> asyncio.Task:
        if task := self.async_tasks["crawler_pause"]:
            return task

        page = page or self.page
        return self.add_background_task(page.pause(), name="crawler_pause")

    def _check_if_instance_properties(self, use_instance_properties: bool, **kwargs):
        if use_instance_properties:
            # this makes it so we can use context manager and pass in args on init rather than here
            # could probably refactor part of this to be a classmethod instead
            start_page = self.start_page or start_page
            headless = self.headless or headless

            # save them as well to the instance
            self.start_page = start_page
            self.headless = headless

    async def _end_async(self):
        # close cdp client before page
        if hasattr(self, "cdp_client"):
            await self.cdp_client.detach()

        if hasattr(self, "page"):
            await self.page.close()
        if hasattr(self, "browser"):
            await self.browser.close()
        if hasattr(self, "ctx_manager"):
            await self.ctx_manager.__aexit__()

    async def end(self) -> Awaitable[None] | None:
        if not self.is_async:
            raise Exception("end() can only be called in async mode")
        return await self._end_async()

    async def init_without_ctx_manager(self):
        self.ctx_manager = PlaywrightContextManager()
        self.pw = await self.ctx_manager.start()
        return self

    async def start(self, inject_preload: bool = True):
        self._started, self.is_async = True, True
        # ideally will make all this possible to use with then normal context manager
        # i.e. something like `with playwright as pw: self.pw = pw``
        await self.init_without_ctx_manager()
        # Selectors must be registered before creating the page.
        self.selectors = await asyncio.gather(*self.extend_selectors())
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.ctx = await self.browser.new_context(user_agent=default_user_agent)

        await self.ctx.route("**/*", lambda route: route.continue_())

        if inject_preload:
            await self.injection(ctx=self.ctx, script=self.preload_injection_script)

        self.page = await self.ctx.new_page()
        await self.page.set_viewport_size(default_viewport_size)

        self.cdp_client = await self.get_cdp_client()
        return self.page

    def get_cdp_client(self) -> Awaitable[CDPSession] | CDPSession:
        return self.page.context.new_cdp_session(self.page)

    def extend_selectors(self):
        return Selector.register(self.pw)

    def injection(self, ctx: Browser | Page, script: str) -> Awaitable | None:
        return ctx.add_init_script(path=script)

    async def playwright_resume(self) -> Awaitable[None]:
        return await self.page.evaluate(self.end_early_js)

    async def allow_end_early(self, end_early_str: str = END_EARLY_STR, callback: Callable = None) -> Awaitable[None]:
        # not sure why but what i was prev using is broke:
        if getattr(self.clippy, "DEBUG", False):
            logger.debug("NOT ALLOWING TO END EARLY SINCE DEBUG=True")
            return

        logger.info(end_early_str.upper())

        while line := await asyncio.to_thread(sys.stdin.readline):
            resp = await self.playwright_resume()
            if callback:
                return callback(resp, line=line)
            return resp

    def add_background_task(self, fn: Awaitable, name: str = None) -> asyncio.Task:
        task = asyncio.create_task(fn)
        name = name or task.get_name()
        self.async_tasks[name] = task
        logger.info(f"added task {name}")
        return task

    async def page_size(self) -> Sequence[int]:
        device_pixel_ratio = await self.page.evaluate("window.devicePixelRatio")
        win_scroll_x = await self.page.evaluate("window.scrollX")
        win_scroll_y = await self.page.evaluate("window.scrollY")
        win_upper_bound = await self.page.evaluate("window.pageYOffset")
        win_left_bound = await self.page.evaluate("window.pageXOffset")
        win_width = await self.page.evaluate("window.screen.width")
        win_height = await self.page.evaluate("window.screen.height")
        return (device_pixel_ratio, win_scroll_x, win_scroll_y, win_upper_bound, win_left_bound, win_width, win_height)

    async def execute_click(self, action: NextAction, **kwargs):
        loc = action.locator.nth(0)
        logger.info(f"doing click at {loc}")
        await loc.click(delay=self.input_delay)
        await self.page.wait_for_load_state()

    async def execute_type(self, action: NextAction, **kwargs):
        await self.execute_click(action)

        logger.info(f"doing type...{action.action_args}")
        await self.page.keyboard.type(action.action_args, delay=self.input_delay)

        logger.info("doing enter...")
        # TODO: i should ask for next action after typing from LM, NOT just press enter
        await self.page.keyboard.press("Enter", delay=self.input_delay)

    async def execute_scroll(self, action: NextAction, **kwargs):
        viewport_height = self.page.viewport_size["height"]
        logger.info("doing scroll...")

        def direction(_dir: int) -> int:
            _amt = 0.75  # 3/4ths the page up or down
            return round(_dir * viewport_height * _amt)

        if action.action == "scrolldown":
            await self.page.mouse.wheel(delta_x=0, delta_y=direction(1))
        elif action.action == "scrollup":
            await self.page.mouse.wheel(delta_x=0, delta_y=direction(-1))

    actions = {
        "type": execute_type,
        "click": execute_click,
        "scrolldown": execute_scroll,
        "scrollup": execute_scroll,
    }
