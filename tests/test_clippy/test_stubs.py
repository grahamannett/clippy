import unittest

from clippy.stubs import StubTemplates
from clippy.crawler.parser.dom_snapshot import filter_page_elements
from clippy.controllers.models import StateSchema, ActionSchema, GenerateActionSchema, EnhancedJSONEncoder

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


class TestStubs(unittest.IsolatedAsyncioTestCase):
    def test_state(self):
        filter_elements = list(filter_page_elements(elements))
        assert len(elements) > len(filter_elements)

        state = StubTemplates.state.render(
            objective="objective1", url="url1", browser_content=filter_elements, previous_commands=None
        )

        prompt_str = StubTemplates.prompt.render(
            state=state,
            objective="objective1",
            url="url1",
            browser_content=filter_elements,
        )

        assert "You are an" in prompt_str

        assert "Previous actions: None" in prompt_str

        prompt_str = StubTemplates.prompt.render(
            objective="objective1",
            url="url1",
            browser_content=None,
            previous_commands=["action 1", "action 2"],
        )

        assert "Current Browser Content: None" in prompt_str


class TestJsonSchema(unittest.IsolatedAsyncioTestCase):
    def test_schema(self):
        state = StateSchema("objective1", "https://yahoo.com")
        prev_actions = [ActionSchema("input", "7 'combobox'", "hackernews"), ActionSchema("button", "8 'Search'")]
        browser_content = [
            ActionSchema("button", "1 hnname"),
            ActionSchema("link", "2 'Hacker News'"),
            ActionSchema("link", "3 'new'"),
        ]
        generate_action = GenerateActionSchema(state, prev_actions, browser_content, "PLACEHOLDER")

        json_str = EnhancedJSONEncoder.dumps(generate_action)
        assert '"state": {' in json_str
