import unittest

from clippy import logger
from clippy.stubs import StubTemplates
from clippy.crawler.parser.dom_snapshot import filter_page_elements
from clippy.states.actions import Actions
import pytest


elements = [
    "button 1 home",
    'link 2 "News"',
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
]


@pytest.mark.parametrize("elements,objective,url", [[elements, "test objective", "https://website-dot-com"]])
def test_stub_cmd_prompt(elements, objective, url):
    filter_elements = list(filter_page_elements(elements))
    assert len(elements) > len(filter_elements)

    state = StubTemplates.state.render(
        objective=objective, url=url, browser_content=filter_elements, previous_commands=None
    )
    assert "OBJECTIVE: test objective" in state

    logger.rule("STATE")
    logger.log(state)

    # Test With Default
    # base prompt that is most likely to be used
    prompt_str = StubTemplates.prompt.render(
        state=state,
        objective=objective,
        action_str_list=Actions.actions_for_templates(),
        url=url,
        browser_content=filter_elements,
    )

    assert "\n\nActions are specified in the following format:\n"
    assert "You are a" in prompt_str
    assert "Previous actions: None" in prompt_str
    assert "scroll down/up the page" not in prompt_str

    # Generally dont want scroll down/up the page as available action but testing
    # Test with All Action Strings
    prompt_str = StubTemplates.prompt.render(
        state=state,
        objective=objective,
        action_str_list=Actions.actions_for_templates(use_keys="all"),  # scroll should be in here
        url=url,
        browser_content=filter_elements,
    )
    assert "scroll down/up the page" in prompt_str

    # Test With Alternative Action Strings
    prompt_str = StubTemplates.prompt.render(
        state=state,
        objective=objective,
        action_str_list=["madeup action 1", "madeup action 2"],
        url=url,
        browser_content=filter_elements,
    )
    assert "Previous actions: None" in prompt_str
    assert "Actions are specified in the following format:\n- madeup action 1\n- madeup action 2" in prompt_str

    previous_commands = ["action 1", "action 2"]
    prompt_str = StubTemplates.prompt.render(
        objective=objective,
        url=url,
        browser_content=None,
        previous_commands=previous_commands,
    )

    assert "Current Browser Content: None" in prompt_str
    assert "\n\nActions are specified in the following format:\n- click "
    assert all([cmd in prompt_str for cmd in ["Previous actions:\n"] + previous_commands])


# TEST FOR Filter Template
@pytest.mark.parametrize(
    "elements,objective,title,url", [[elements, "test objective", "test title", "https://website-dot-com"]]
)
def test_stub_filter_prompt(elements, objective, title, url):
    # filtered_elements = [f"element {i}" for i in range(10)]
    previous_commands = [f"action {i}" for i in range(5)]

    prompt_str: str = StubTemplates.prompt.render(
        header_prompt=StubTemplates.header_filter_elements.render(max_elements=5),
        objective=objective,
        title=title,
        url=url,
        browser_content=elements,
        previous_commands=previous_commands,
        skip_available_actions=True,
        element_prefix="- ",
        footer_prompt="Filtered Browser Content:\n",
    )

    assert prompt_str.endswith("Filtered Browser Content:\n")
