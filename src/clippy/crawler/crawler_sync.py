# sync types and functions
from playwright.sync_api import Browser, BrowserContext, CDPSession
from playwright.sync_api import PlaywrightContextManager
from playwright.sync_api import Request, Route

from playwright.sync_api import Page

from clippy.crawler.crawler import Crawler


class CrawlerSync(Crawler):
    def start(
        self,
        start_page: str = None,
        key_exit: bool = False,
        headless: bool = False,
        inject_preload: bool = True,
        use_instance_properties: bool = False,
    ) -> Page:
        if use_instance_properties:
            start_page = self.start_page or start_page
            key_exit = self.key_exit if (self.key_exit != None) else key_exit
            headless = self.headless or headless
            self.start_page = start_page
            self.key_exit = key_exit
            self.headless = headless

        self.is_async = False
        self.init_without_ctx_manager_sync()
        self.selectors = self.extend_selectors()
        self.browser = self.pw.chromium.launch(headless=headless)
        self.ctx = self.browser.new_context()
        self.ctx.route("**/*", lambda route: route.continue_())

        if inject_preload:
            self.injection(ctx=self.ctx, script=self.preload_injection_script)

        self.page = self.ctx.new_page()

        if key_exit:
            raise NotImplementedError("key_exit is not implemented for sync")
            # print("WARNING: key_exit is True, this likely does not work for sync")
            # self.add_async_task(end_record(self.page, crawler=self))

        if start_page:
            self.page.goto(start_page)
        return self.page

    def init_without_ctx_manager_sync(self):
        self.ctx_manager = PlaywrightContextManager()
        self.pw = self.ctx_manager.start()
        return self
