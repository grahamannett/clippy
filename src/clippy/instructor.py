import asyncio
from dataclasses import dataclass
from distutils.util import strtobool
from os import environ
from typing import List

from playwright.async_api import Locator, Page
from playwright.sync_api import Locator as LocatorSync

from clippy.controllers.apis.cohere_controller import CohereController
from clippy.stubs.stubs import StubHelper, StubTemplates

action_options = [{"next_command": "click"}, {"next_command": "type"}]


# these are dataclasses rather than named tuple so I can attach objects to them
@dataclass
class ScoredNextAction:
    next_command: str
    score: float


@dataclass
class ScoredActionTarget:
    target: str
    score: float


class Instructor:
    """the instructor is the LLM that is used to score page elements and guess next action"""

    def __init__(self, use_async: bool = True, use_llm: bool = True, *args, **kwargs):
        self.use_async = use_async
        self.use_llm = use_llm

        self.lm_controller = CohereController()
        self.enable_threadpool: bool = bool(strtobool(environ.get("ENABLE_TP", "True")))

    async def compare_all_page_elements(
        self,
        objective: str,
        page_elements: List[str] = None,
        url: str = None,
        return_sorted: bool = False,
    ) -> List[ScoredNextAction]:
        """given the page state, compare all page elements against the objective
        Args:
            objective (str): current objective
        """

        state_text = StubTemplates.state(
            objective=objective,
            url=url,
            browser_content="\n".join([f"- {el}" for el in page_elements]),
            previous_commands="None",
        )

        options = [{"next_command": e} for e in page_elements]
        scored_opts = await self.lm_controller.score_actions(
            str_template=StubTemplates.prompt, options=options, state=state_text
        )
        scored_opts = [ScoredNextAction(**opt) for opt in scored_opts]

        if return_sorted:
            scored_opts = sorted(scored_opts, key=lambda x: x.score, reverse=True)

        return scored_opts

    def predict_next_action(self, page_state, objective: str) -> List[ScoredNextAction]:
        """given the state, predict the next action (click/type/etc)"""

        state_text = StubTemplates.state(
            objective=objective,
            url=page_state.url,
            browser_content="\n".join([f"- {el}" for el in page_state.page_elements]),
            previous_commands="None",
        )

        scored_opts = self.lm_controller.score_actions(
            str_template=StubTemplates.prompt, options=action_options, state=state_text
        )
        scored_opts = sorted([ScoredNextAction(**opt) for opt in scored_opts], key=lambda x: x.score, reverse=True)
        return scored_opts

    def predict_action_target(
        self,
        action: str,
        objective: str,
        page_state=None,
        url: str = None,
        page_elements: List[str] = None,
    ) -> List[ScoredActionTarget]:
        filtered_page_elements = list(filter_page_elements(action, page_state.page_elements))
        browser_content = "\n".join([f"- {el}" for el in filtered_page_elements])

        state_text = StubTemplates.state(
            objective=objective,
            url=page_state.url,
            browser_content=browser_content,
            previous_commands="None",
        )

        next_command = action + " ${target}"
        target_template = StubHelper.template(StubTemplates.prompt(state=state_text, next_command=next_command))
        options = [{"target": t} for t in filtered_page_elements]

        if len(options) > 1:
            scored_opts = self.lm_controller.score_actions(
                str_template=target_template, options=options, state=state_text
            )
        else:
            scored_opts = [{"target": options[0]["target"], "score": 1.0}]

        scored_opts = sorted([ScoredActionTarget(**opt) for opt in scored_opts], key=lambda x: x.score, reverse=True)
        return scored_opts

    def predict_target_cmd(self, objective: str, next_cmd: List[str], page_state) -> str:
        # if its a type command, then we need to ask for the value

        browser_content = "\n".join([f"- {el}" for el in page_state.page_elements])
        state_text = StubTemplates.state(
            objective=objective, url=page_state.url, browser_content=browser_content, previous_commands="None"
        )
        next_command = " ".join(next_cmd) + "\nValue:"

        prompt_str = StubTemplates.prompt(state=state_text, next_command=next_command)
        _generated_text = self.lm_controller.generate(prompt_str, max_tokens=10, temperature=0.5, num_generations=1)
        generated_text = str(generated_text[0]).lstrip()
        return generated_text

    async def llm_assist_hook(self, page: Page):
        if not self.use_llm:
            return

        if (elements_of_interest := await self._get_elements_of_interest(self.cdp_client, page)) == []:
            print("tried to crawl but didnt work...")
            return

        # elements_of_interest = await self.dom_parser.crawl_async(self.cdp_client, page)
        element_buffer = self.dom_parser.page_element_buffer
        ids_of_interest = self.dom_parser.ids_of_interest

        if not ids_of_interest:
            print("no elements of interest, skipping...")
            return

        locators = await asyncio.gather(
            *[
                self.dom_parser._get_from_location_async(element_buffer[i], page)
                for idx, i in enumerate(ids_of_interest)
            ]
        )

        # TODO: shorten it for time being
        elements_of_interest = elements_of_interest[:50]
        scored_elements = await self.instructor.compare_all_page_elements_async(
            self.objective, page_elements=elements_of_interest, url=page.url
        )

        if not scored_elements:
            breakpoint()

        return await self.instructor.highlight_from_scored_async(scored_elements, locators=locators, page=page)
