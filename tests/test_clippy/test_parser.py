import unittest
import torch
from playwright.sync_api import sync_playwright, Locator, PlaywrightContextManager

from clippy.crawler.crawler import SelectorExtension
from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser, _get_from_location

data = torch.load("tests/fixtures/soap/llm-assist.pt")
url = data["url"]

# page_elements = data["page_elements"]
# page_element_buffer = data["page_element_buffer"]
# tree = data["tree"]

# page.evaluate("document.elementFromPoint(142, 248)")


class TestParser(unittest.TestCase):
    def test_elements_to_locators(self):
        with sync_playwright() as p:
            SelectorExtension.setup_tag_selectors(p)
            # p.selectors.register("tag", SelectorExtension.tag_selector)
            # p.selectors.register("pos", SelectorExtension.pos_selector)
            browser = p.chromium.launch(headless=False)

            context = browser.new_context()
            context.add_init_script(path="clippy/crawler/inject/empty.js")

            context.route("**/*", lambda route: route.continue_())

            page = context.new_page()
            print("going to url...", url)
            page.goto(url)

            client = page.context.new_cdp_session(page)
            viewport_size = page.viewport_size

            parser = DOMSnapshotParser(False)

            pel = parser.crawl(client, page)
            pelb = parser.page_element_buffer
            pel_ids = parser.ids_of_interest

            data = {
                "page_elements": pel,
                "page_element_buffer": pelb,
                "page_elements_ids": pel_ids,
                "tree": parser._tree,
                "url": url,
                "viewport_size": viewport_size,
            }

            torch.save(data, "tests/fixtures/soap/llm-assist.pt")

            width, height = viewport_size["width"], viewport_size["height"]

            locs = parser.get_locators(page=page)
            self.assertTrue(len(locs) == len(pel))
            # page.pause()
