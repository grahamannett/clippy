import asyncio
import json
from typing import List, Optional

from clippy import logger
from playwright.async_api import Locator, Page

from clippy.controllers.apis.cohere_controller import CohereController, Responses
from clippy.controllers.apis.cohere_controller_utils import Generation, Generations
from clippy.crawler.parser.dom_snapshot import get_action_type
from clippy.states import NextAction
from clippy.stubs.stubs import StubTemplates


def match_generated_output(text: str, elements: List[str]) -> Optional[int]:
    """Given a generated text, match it to an element on the page."""
    return next((i for i, el in enumerate(elements) if el in text), None)


class Instructor:
    """the instructor is the LLM that is used to score page elements and guess next action"""

    def __init__(self, use_async: bool = True, use_llm: bool = True, *args, **kwargs):
        self.use_async = use_async
        self.use_llm = use_llm

        self.lm_controller = CohereController()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.end()

    async def end(self):
        """Ends the language model controller, ignoring any exceptions."""
        try:
            await self.lm_controller.end()
        except Exception as err:
            logger.error(f"Error ending language model controller: {err}")

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
        """Given the page state, generate the next action. This is more ideal than scoring all actions."""
        prompt = StubTemplates.prompt.render(
            objective=objective,
            title=title,
            url=url,
            browser_content=elements,
            previous_commands=previous_commands,
        )

        response: Generations = await self.lm_controller.generate(
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

        for _ in range(max_tries):
            if len(filtered_elements) <= max_elements:
                break

            prompt: str = StubTemplates.prompt.render(
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

            response: Generations = await self.lm_controller.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                num_generations=num_generations,
                return_likelihoods=return_likelihoods,
                temperature=temperature,
            )

            logger.info("done filter request...")

            if len(response.generations) > 1:
                raise ValueError("response has more than one generation")
            # try to remove the left space and empty lines
            filtered_elements = [f.lstrip() for f in response[0].text.split("\n") if f]

        # we should probably match with original elements at this point
        return filtered_elements

    async def transform_action(
        self,
        generated_action: str,
        num_generations: int = 5,
        temperature: float = 0.25,
        **kwargs,
    ) -> NextAction:
        """Transforms a generated action string into a valid action.
        A valid action has an action type, an id/locator, and a value if needed.
        """
        prompt = StubTemplates.transform_generation.render(generated_action=generated_action)
        response = await self.lm_controller.generate(
            prompt=prompt,
            max_tokens=200,
            return_likelihoods="GENERATION",
            num_generations=num_generations,
            temperature=temperature,
            **kwargs,
        )

        # Attempt to get a valid response
        for resp in response:
            try:
                # Expected format will be similar to:
                # {"action": "type", "element_id": 9, "element_metadata": null, "action_args": "buy bodywash"}
                resp_dict = json.loads(resp.text)

                next_action = NextAction(
                    action=resp_dict.pop("action"),
                    element_id=resp_dict.pop("element_id"),
                    element_metadata=resp_dict.pop("element_metadata", None),
                    action_args=resp_dict.pop("action_args", None),
                    score=resp.likelihood,
                )

                if resp_dict:
                    logger.warn("Response has more keys than expected")
                    next_action.extra = resp_dict

                next_action.response = resp
                return next_action
            except (json.decoder.JSONDecodeError, KeyError) as e:
                logger.error(f"Error processing response: {e}")
                continue

        if next_action is None:
            raise ValueError("Unable to transform generated action into a valid action")
        return next_action

    async def score_actions(
        self,
        elements: List[str],
        objective: str,
        url: str,
        previous_commands: List[str] = None,
        locators: List[Locator] = [],
    ) -> List[NextAction]:
        """Scores all page elements against the current objective.

        Args:
            objective (str): Current objective.
            elements (List[str]): Page elements to score.
            url (str): Current URL.
            previous_commands (List[str], optional): Previous commands. Defaults to None.
            locators (List[Locator], optional): Locators for the elements. Defaults to [].

        Returns:
            List[NextAction]: List of scored actions.
        """
        state = StubTemplates.state.render(
            objective=objective,
            url=url,
            browser_content=elements,
            previous_commands=previous_commands,
        )

        async def score_element(element: str, index: int) -> NextAction:
            action_type = get_action_type(element)
            next_command = f"{action_type} - {element}"
            prompt = StubTemplates.prompt.render(state=state, next_command=next_command)
            score = await self.lm_controller.generate(prompt=prompt, max_tokens=0, return_likelihoods="ALL")
            action = NextAction(action=action_type, score=score[0].likelihood, action_args=element)
            if locators:
                action.locator = locators[index]
            return action

        return await asyncio.gather(*[score_element(element, index) for index, element in enumerate(elements)])

    async def _find_action_from_elems(self, elems: List[str], locators: List[str]):
        scored = await self.score_actions(
            elems,
            self.objective,
            url=self.crawler.page.url,
            locators=locators,
        )
        # top action
        logger.info(f"top action: {scored[0]}")
        for i, score in enumerate(scored):
            score.locator = locators[i]

        scored = sorted(scored, key=lambda x: x.score, reverse=True)

        return scored
