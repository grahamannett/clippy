import asyncio
import json
from dataclasses import dataclass
from typing import List

from loguru import logger
from playwright.async_api import Locator, Page

from clippy.controllers.apis.cohere_controller import CohereController, Responses
from clippy.crawler.parser.dom_snapshot import get_action_type
from clippy.states import NextAction
from clippy.stubs.stubs import StubTemplates

action_options = [{"next_command": "click"}, {"next_command": "type"}]


class Instructor:
    """the instructor is the LLM that is used to score page elements and guess next action"""

    def __init__(self, use_async: bool = True, use_llm: bool = True, *args, **kwargs):
        self.use_async = use_async
        self.use_llm = use_llm

        self.lm_controller = CohereController()

    async def score_actions(
        self,
        elements: List[str],
        objective: str,
        url: str,
        previous_commands: List[str] = None,
        locators: List[Locator] = [],
    ) -> List[NextAction]:
        """given the page state, compare all page elements against the objective
        Args:
            objective (str): current objective
        """

        # state could be combined into prompt.render but seperate to allow examing state
        state = StubTemplates.state.render(
            objective=objective,
            url=url,
            browser_content=elements,
            previous_commands=previous_commands,
        )

        async def score_fn(el, idx):
            action_type = get_action_type(el)
            next_command = f"{action_type} - {el}"
            prompt = StubTemplates.prompt.render(state=state, next_command=next_command)
            score = await self.lm_controller.generate(prompt=prompt, max_tokens=0, return_likelihoods="ALL")
            action = NextAction(action=action_type, score=score[0].likelihood, action_args=el)
            if locators:
                action.locator = locators[idx]
            return action

        return await asyncio.gather(*[score_fn(el, idx) for idx, el in enumerate(elements)])

    async def generate_next_action(
        self,
        elements: List[str],
        objective: str,
        title: str,
        url: str,
        previous_commands: List[str] = None,
        max_tokens: int = 150,
        num_generations: int = 1,
        return_likelihoods: str = "GENERATION",
        temperature: float = 0.25,
    ) -> Responses.Generations:
        """given the page state, generate the next action, this is more ideal than scoring all actions"""
        prompt = StubTemplates.prompt.render(
            objective=objective,
            title=title,
            url=url,
            browser_content=elements,
            previous_commands=previous_commands,
        )

        response = await self.lm_controller.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            num_generations=num_generations,
            return_likelihoods=return_likelihoods,
            temperature=temperature,
        )
        return response

    async def filter_actions(
        self,
        elements: List[str],
        objective: str,
        title: str,
        url: str,
        max_elements: int = 20,
        max_tries: int = 1,
        previous_commands: List[str] = None,
        max_tokens: int = 500,
        num_generations: int = 1,
        return_likelihoods: str = "GENERATION",
        temperature: float = 0.0,
    ):
        filtered_elements = elements

        while max_tries > 0 and len(filtered_elements) > max_elements:
            max_tries -= 1

            prompt = StubTemplates.prompt.render(
                header_prompt=StubTemplates.header_filter_elements.render(max_elements=max_elements),
                objective=objective,
                title=title,
                url=url,
                browser_content=filtered_elements,
                previous_commands=previous_commands,
                skip_available_actions=True,
                element_prefix="- ",
                footer_prompt="Filtered Browser Content:\n",
            )
            logger.info("making filter request...")

            response = await self.lm_controller.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                num_generations=num_generations,
                return_likelihoods=return_likelihoods,
                temperature=temperature,
            )

            logger.info("done filter request...")

            # try to remove the left space and empty lines
            filtered_elements = [f.lstrip(" ") for f in response[0].text.split("\n") if f != ""]

        # we should probably match with original elements at this point
        return filtered_elements

    async def transform_action(
        self,
        generated_action: str,
        num_generations: int = 5,
        temperature: float = 0.25,
        **kwargs,
    ) -> NextAction:
        """given a generated action str, transform it into a valid action
        meaning it has an action type, an id/locator, and a value if needed
        """
        next_action = None
        prompt = StubTemplates.transform_generation.render(generated_action=generated_action)
        response = await self.lm_controller.generate(
            prompt=prompt,
            max_tokens=200,
            return_likelihoods="GENERATION",
            num_generations=num_generations,
            temperature=temperature,
            **kwargs,
        )

        # give multiple tries to get a valid response
        for resp in response:
            try:
                # should be similar to:
                # {"action": "type", "element_id": 9, "element_metadata": null, "action_args": "buy bodywash"}
                resp_dict = json.loads(resp.text)

                next_action = NextAction(
                    action=resp_dict.pop("action"),
                    element_id=resp_dict.pop("element_id"),
                    element_metadata=resp_dict.pop("element_metadata", None),
                    action_args=resp_dict.pop("action_args", None),
                    # score is the least needed
                    score=resp.likelihood,
                )

                if len(resp_dict) > 0:
                    logger.warning("resp has more keys than we expected")
                    # not a field
                    next_action.extra = resp_dict

                # attach the response to the action
                next_action.response = resp
                return next_action
            except json.decoder.JSONDecodeError or KeyError:
                logger.error(f"resp isn't json decodable: {resp[0].text}")
                continue
            except KeyError:
                logger.error(f"resp isn't doesnt have Keys we need: {resp_dict}")
                continue

        return next_action

    async def match_generated_output(self, text: str, elements: List[str]) -> int:
        """given a generated text, match it to an element on the page"""

        for i, el in enumerate(elements):
            if el in text:
                return i

        return None

    async def _find_action_from_elems(self, elems: List[str], locators: List[str]):
        next_action = await self.score_actions(
            elems,
            self.objective,
            url=self.crawler.page.url,
            locators=locators,
        )
        scored = await self.score_actions(elems, self.objective, url=self.crawler.page.url)
        # top action
        logger.info(f"top action: {scored[0]}")
        for i, score in enumerate(scored):
            score.locator = locators[i]

        scored = sorted(scored, key=lambda x: x.score, reverse=True)

        return scored
