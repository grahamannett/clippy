import asyncio
import json

from clippy import logger
from playwright.async_api import ConsoleMessage, Page, Request

from clippy import logger
from clippy.capture.capture import Capture
from clippy.crawler.crawler import Crawler
from clippy.crawler.tools_capture import _print_console
from clippy.dm.data_manager import DataManager
from clippy.states import Action, Actions


def log_hook(name: str):
    async def hook(*args, **kwargs):
        logger.info(f"[LOG-HOOK|{name.upper()}] {args} {kwargs}")

    return hook


async def all_console_log(msg: ConsoleMessage):
    logger.info(f"msg", msg)
    logger.info(f"msg.args", msg.args)


async def catch_console_injections(msg: ConsoleMessage, print_injection: bool = True) -> Action:
    if not msg.text.startswith("CATCH"):  # if no CATCH prepended, its a skip
        return

    values = []
    for arg in msg.args:
        values.append(await arg.json_value())

    if print_injection:
        _print_console(*values, print_fn=logger.debug)

    if len(values) < 3:
        return

    catch_flag, class_name, data = values  # data is list of [CATCH, class_name, *data]
    data = json.loads(data)

    action = Actions[class_name](**data)
    return action


class CaptureAsync(Capture):
    def __init__(
        self,
        start_page: str = None,
        data_manager: DataManager = None,
        use_llm: bool = False,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(
            start_page=start_page,
            data_manager=data_manager,
            use_llm=use_llm,
            *args,
            **kwargs,
        )

        self.captured_screenshot_ids = []
        self.captured_screenshot_urls = []
        self._use_log_hook = False

    async def hook_dom_group(self, page: Page):
        logger.info(f"PAGE-CHANGE|{page.url}")
        await self.hook_update_task_new_page(page=page)
        await self.hook_capture_screenshot(page=page)
        logger.info(f"PAGE-CHANGE-DONE|{page.url}")

    async def hook_update_task_new_page(self, page: Page):
        await self.task.page_change_async(page=page)

    async def hook_capture_screenshot(self, page: Page):
        self.async_tasks["screenshot_event"].clear()
        self.captured_screenshot_urls.append(page.url)

        current_step = self.task.current

        if current_step.id in self.captured_screenshot_ids:
            return

        screenshot_path = self.data_manager.get_curr_step_screenshot_path()
        current_step.screenshot_path = screenshot_path
        await self.crawler.page.screenshot(path=screenshot_path, full_page=True)
        self.captured_screenshot_ids.append(current_step.id)

        self.async_tasks["screenshot_event"].set()
        logger.info(f"screenshot taken for {page.url[:50]}...")

    async def hook_console(self, msg: ConsoleMessage):
        try:
            action = await catch_console_injections(msg, print_injection=self.print_injection)
        except Exception as e:
            logger.error(f"Error catching msg: {msg}")
            action = None

        if action:
            self.task(action)

    async def hook_request_navigation_response(request: Request):
        if request.is_navigation_request():
            pass

    def setup_page_hooks(self, page: Page):
        # first create events that hooks may need
        self.async_tasks["screenshot_event"] = asyncio.Event()

        # captures actions from injections
        page.on("console", self.hook_console)
        # things that need to happen on page change
        page.on("domcontentloaded", self.hook_dom_group)

        # hooks that are only helpful when understanding the lifecycle of page/frames
        if self._use_log_hook:
            page.on("framenavigated", log_hook("framenavigated"))
            page.on("domcontentloaded", log_hook("domcontentloaded"))
            page.on("frameattached", log_hook("frameattached"))
            page.on("requestfinished", log_hook("requestfinished"))

    async def start(self, crawler: Crawler, start_page: str | bool = False) -> Page:
        self.crawler = crawler

        logger.info("crawler start...")
        page = await crawler.start()
        logger.info("add background tasks...")

        logger.info("setup page hooks...")
        self.setup_page_hooks(page=page)

        if isinstance(start_page, str):
            # think this might fuck up the capture
            logger.info("going to start page")
            await page.goto(start_page)

        return page
