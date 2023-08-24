import json
import re
import time
from os.path import exists
from sys import platform
from typing import Any, Dict, Iterator, List, Optional

from playwright.sync_api import Locator, Page, sync_playwright

from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser

from .plugins.page_parser import Parser, TasksInterface

black_listed_elements = set(
    [
        "html",
        "head",
        "title",
        "meta",
        "iframe",
        "body",
        "script",
        "style",
        "path",
        "svg",
        "br",
        "::marker",
    ]
)

URL_PATTERN = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
WINDOW_SIZE = {"width": 1280, "height": 1080}

TYPEABLE = ["input", "select"]
CLICKABLE = ["link", "button"]


def filter_page_elements(action: str, page_elements: List[str]) -> Iterator[str]:
    types_ = {
        "click": CLICKABLE,
        "type": TYPEABLE,
    }

    assert action in types_, f"action {action} not in {types_.keys()}"

    for element in page_elements:
        for avail in types_[action]:
            if avail in element:
                yield element


def replace_special_fields(cmd):
    if exists("specials.json"):
        with open("specials.json", "r") as fd:
            specials = json.load(fd)

        for k, v in specials.items():
            cmd = cmd.replace(k, v)

    return cmd


class Executor:
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"

    def __init__(self, keep_device_ratio: bool = False, headless: bool = False):
        self.browser = sync_playwright().start().chromium.launch(headless=headless)
        self.context = self.browser.new_context(user_agent=self.user_agent)

        self.page = self.context.new_page()
        self.page.set_viewport_size(WINDOW_SIZE)

        self.keep_device_ratio = keep_device_ratio
        self.parser = DOMSnapshotParser(self.keep_device_ratio, crawler=self)

    def go_to_page(self, url):
        self.page.goto(url=url if "://" in url else "http://" + url)
        self.client = self.page.context.new_cdp_session(self.page)
        self.page_element_buffer = {}

    def scroll(self, direction):
        if direction == "up":
            self.page.evaluate(
                "(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop - window.innerHeight;"
            )
        elif direction == "down":
            self.page.evaluate(
                "(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop + window.innerHeight;"
            )

    def click(self, id):
        # Inject javascript into the page which removes the target= attribute from all links
        js = """
        links = document.getElementsByTagName("a");
        for (var i = 0; i < links.length; i++) {
            links[i].removeAttribute("target");
        }
        """
        self.page.evaluate(js)

        element = self.page_element_buffer.get(int(id))
        if element:
            x = element.get("center_x")
            y = element.get("center_y")

            height, width = WINDOW_SIZE["height"], WINDOW_SIZE["width"]

            x_d = max(0, x - width)
            x_d += 5 * int(x_d > 0)
            y_d = max(0, y - height)
            y_d += 5 * int(y_d > 0)

            if x_d or y_d:
                self.page.evaluate(f"() => window.scrollTo({x_d}, {y_d})")

            if x_d or y_d:
                # not entirely sure this will work if there is scrolling
                self.page.mouse.click(x - x_d, y - y_d)
            else:
                self.page.mouse.click(x + element["origin_x"], y + element["origin_y"])
        else:
            print("Could not find element")

    def type(self, id, text):
        self.click(id)
        self.page.evaluate(f"() => document.activeElement.value = ''")
        self.page.keyboard.type(text)

    def enter(self):
        self.page.keyboard.press("Enter")

    def crawl(self):
        start = time.time()

        if isinstance(self.parser, DOMSnapshotParser):
            self.parser.crawl(self.client, self.page)
            self.page_element_buffer = self.parser.page_element_buffer
            self.elements_of_interest = self.parser.elements_of_interest

        return self.elements_of_interest

    def run_cmd(self, cmd, controller=None):
        print("cmd", cmd)
        cmd = replace_special_fields(cmd.strip())

        if cmd.startswith("SCROLL UP"):
            self.scroll("up")
        elif cmd.startswith("SCROLL DOWN"):
            self.scroll("down")
        elif cmd.startswith("summary"):
            short_text = Parser(self.page.content()).process()
            task_interface = TasksInterface()
            short_text_with_prompt = task_interface.summary(short_text)
            controller.use_text(short_text_with_prompt)
        elif cmd.startswith("click"):
            comma_split = cmd.split(",")
            id = comma_split[0].split(" ")[2]
            self.click(id)
        elif cmd.startswith("type"):
            space_split = cmd.split(" ")
            id = space_split[2]
            text = space_split[3:]
            text = " ".join(text)
            # Strip leading and trailing double quotes
            text = text[1:-1]
            text += "\n"
            self.type(id, text)

        time.sleep(1)


def _find_locator_for_element(
    self, element: Dict[str, Any], inner_text: str = None, meta=None, page: Page = None
) -> Optional[Locator]:
    if page is None:
        page = self.page

        # def __find_locator(element: Dict[str, Any], inner_text: str = None):

    # print("node_meta", element["node_meta"])
    if 'class="gNO89b"' in element["node_meta"]:
        breakpoint()
    if inner_text and self.page.is_visible(f"text={inner_text}"):
        locator = self.page.locator(f"text={inner_text}")

    elif self.page.is_visible(f"id={element['node_meta'][-1]}"):
        locator = self.page.locator(f"id={element['node_meta'][-1]}")

    elif self.page.is_visible(f"[{element['node_meta'][-1]}]"):
        locator = self.page.locator(f"[{element['node_meta'][-1]}]")
    elif any([self.page.is_visible(f"[class={i}]") for i in element["node_meta"]]):
        # breakpoint()
        for i in element["node_meta"]:
            if self.page.is_visible(f"[class={i}]"):
                locator = self.page.locator(f"[class={i}]")
                break
    else:
        print(f"failed to find locator for {meta}")


class CommandDispatch:
    def __init__(self, executor: Executor) -> None:
        self.executor = executor


def reset(self) -> ClippyState:
    executor = Executor(keep_device_ratio=self.keep_device_ratio, headless=self.headless)
    self.state = ClippyState(executor=executor)
    return self.state


def start_agent(self):
    state = self.reset()
    defaults = ClippyDefaults()
    state.executor.go_to_page(defaults.start_page)

    if self.objective is None:
        objective = self._get_input(defaults.objective)
    else:
        print(f"starting with objective: {self.objective}")
        objective = self.objective

    state.objective = objective
    self.instructor = Instructor(objective)

    # set initial loop states
    state.pre_step = self.get_page_state
    state.next_step = self.instructor.step_handler.first_step
    state.post_step = self.instructor.step_handler.post_state
