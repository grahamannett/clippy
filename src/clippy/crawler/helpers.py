import asyncio
import sys
import os

from playwright.async_api import Request, Route

import atexit

from clippy.utils.async_tools import run_async_func, _allow_nested_loop
from clippy.constants import action_delay


async def ainput(string: str) -> str:
    # can use aiconsole instead: await aioconsole.ainput(text)
    await asyncio.to_thread(sys.stdout.write, f"{string} ")
    # print(f"{string}")
    return await asyncio.to_thread(sys.stdin.readline)


async def end_record(page, crawler=None, callback: callable = None):
    DEBUG = os.environ.get("DEBUG", False)
    if DEBUG:
        return
    # this is pretty similar to aioconsole but trying to see if i can do without aiconsole
    line = await ainput("STARTING CAPTURE\n==press a key to exit==\n")
    status = await page.evaluate("""() => {playwright.resume()}""")

    # if crawler:
    #     await crawler.end()
    if callback:
        await callback()


async def _dummy_handle_route(route: Route, request: Request):
    # if i want to intercept requests so i can slow them down or something (for screenshots)
    # that will happen here
    await route.continue_()


async def pause_crawler(page):
    await page.pause()


async def all_cmd_input(page):
    user_input = None
    await asyncio.sleep(action_delay)

    while user_input != "q":
        # user_input = input("enter command\n")
        user_input = await ainput("enter command==>\n")
        user_input = user_input.rstrip("\n")
        print("evaluating=>", user_input)

        # user_input = await ainput("enter command\n")
        if user_input == "q":
            status = await page.evaluate("""() => {playwright.resume()}""")
            return
        try:
            await eval(user_input)
        except Exception as e:
            print("error evaluating command", e)
            return
