import unittest
from os import environ

from clippy.stubs import StubTemplates
from clippy.controllers import Controller
from clippy.controllers.controller_config import ResponseConfig

from clippy.crawler.parser.dom_snapshot import filter_page_elements

elements = [
    "button 1 hnname",
    'link 2 "Hacker News"',
    'link 3 "new"',
    'text 4 "|"',
    'link 5 "past"',
    'text 6 "|"',
    'link 7 "comments"',
    'text 8 "|"',
    'link 9 "ask"',
    'text 10 "|"',
    'link 11 "show"',
    'text 12 "|"',
    'link 13 "jobs"',
    'text 14 "|"',
    'link 15 "submit"',
    'link 16 "login"',
    'text 17 "1."',
    'link 19 "OpenTF Announces Fork of Terraform"',
    'text 20 "("',
    'link 21 "opentf.org"',
]


class TestController(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.co = Controller.Clients.Cohere()

    async def asyncTearDown(self):
        await self.co.close()

    async def test_tokenize(self):
        co = self.co
        test_string = "tokenized string"
        base_tokens = await co.tokenize(test_string)

        ResponseConfig.return_raw = True

        tokens = await co.tokenize(test_string)
        breakpoint()

        tokens = (await co.tokenize(test_string)).tokens
        assert len(tokens) > 2

        string = (await co.detokenize(tokens=tokens)).text
        assert string == test_string

        bad_string = (await co.detokenize(tokens=tokens + [9000])).text

        assert string != bad_string
        breakpoint()

    async def test_controller_score(self):
        co = self.co

        scored_text = await co.score_text("This would be a good sentence to score.")
        bad_scored_text = await co.score_text("Rogue asdf !HEllo Friend!! Yessir.")
        assert scored_text > bad_scored_text
