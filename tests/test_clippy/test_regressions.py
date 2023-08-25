import unittest
from os import environ
from string import Template

from dataclasses import dataclass

from clippy.controllers.apis.cohere_controller import CohereController
from clippy.crawler import executor
from clippy.controllers.stubs.stubs import prompt_template
from clippy.utils.data_funcs import argmax

api_key = environ.get("COHERE_KEY")
lm_client = CohereController.get_client(api_key=api_key, check_api_key=True)


@dataclass
class FixtureStub:
    objective: str
    page_url: str


class TestController(unittest.TestCase):
    def test_llm_score(self):
        lm_controller = CohereController(lm_client, objective="test that the llm scores are working")

        special_tokens = lm_controller.get_special_tokens()
        self.assertIsNotNone(special_tokens)

        str_template = "For the next action we should pick $var1"
        elements_list = ["gah", "horr", "nothing"]
        elements = {"var1": elements_list}

        scores = lm_controller.score_elements(str_template, elements=elements)

        arg_ = argmax(scores)
        highest_elem = elements_list[arg_]

        self.assert_(highest_elem == "nothing")

        # score = lm_controller.score_text("test that the llm scores are working")


class TestClippy(unittest.TestCase):
    def setUp(self) -> None:
        self.objective = objective = ("where can i find the rules for hacker news",)
        self.page_url = "https://news.ycombinator.com/newsfaq.html"

        return super().setUp()

    def test_clippy(self):
        crawler = executor.Executor(headless=True)

        crawler.go_to_page(self.fixture.page)

        controller = CohereController(lm_client, objective=self.fixture.objective)

        elements = self.crawler.crawl()


class TestSite(unittest.TestCase):
    def setUp(self):
        self.crawler = executor.Executor()

        # this is the only site I can think of where I am guessing it has been roughly the same for a long time
        # and has elements to click based on actions
        self.site = "https://news.ycombinator.com/lists"

    def test_prioritize_elements(self):
        self.crawler.go_to_page(self.site)
        elements = self.crawler.crawl()
