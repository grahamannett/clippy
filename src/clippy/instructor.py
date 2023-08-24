import asyncio
from distutils.util import strtobool
from os import environ
from typing import List

from playwright.async_api import Locator, Page
from playwright.sync_api import Locator as LocatorSync

from clippy.controllers.apis.cohere_controller import CohereController

from clippy.crawler.parser.dom_snapshot import DOMSnapshotParser
from clippy.data_states import ClippyState, ControllerResponse, HandleUserFeedback, PageState

# from clippy.stubs import StubTemplates, Template
from clippy.stubs.stubs import StubHelper, StubTemplates

action_options = [{"next_command": "click"}, {"next_command": "type"}]

from dataclasses import dataclass


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
    use_async: bool
    """the instructor is the LLM that is used to score page elements and guess next action"""

    def __init__(self, use_async: bool = True, use_llm: bool = True, *args, **kwargs):
        self.use_async = use_async
        self.use_llm = use_llm

        client_func = CohereController.get_client_async if use_async else CohereController.get_client
        # client_func = CohereController.get_client_async

        llm_client = client_func(api_key=environ.get("COHERE_KEY"), check_api_key=True)

        self.lm_controller = CohereController(llm_client)
        self.enable_threadpool: bool = bool(strtobool(environ.get("ENABLE_TP", "True")))

        self.step_handler = InstructorStepHandler(parent=self)

    def _get_input(self, prompt: str):
        # use this so we can mock input for testing
        return input(prompt)

    async def highlight_from_scored_async(
        self, scored_elements: List[ScoredActionTarget], locators: List["Locator"], is_sorted: bool = False, page=None
    ) -> None:
        if (len(locators) == 0) or (len(scored_elements) == 0):
            print("no scored elements or locators")
            return

        for i, el in enumerate(scored_elements):
            el.locator = locators[i]

        scored_elements = scored_elements if is_sorted else sorted(scored_elements, key=lambda x: x.score, reverse=True)

        _highlight = [False, None]
        for e_i, elem in enumerate(scored_elements):
            if isinstance(elem.locator, Locator | LocatorSync):
                await elem.locator.first.highlight()
                _highlight = [True, e_i]

                if e_i >= 1:
                    print(f"---highest scored element is {e_i}th in the list. score below doesnt match---")

                break

        if not _highlight[0]:
            print("---locator out of frame. not highlighting")

        if len(scored_elements) < 2:
            breakpoint()

        print(
            "---"
            + f"LLM[high-score:{scored_elements[0].score},{scored_elements[0].next_command}][low-score:{scored_elements[-1].score},{scored_elements[-1].next_command}]"
            + "---"
        )

    def highlight_from_scored(
        self, scored_elements: List[ScoredNextAction], locators: List["Locator"], is_sorted: bool = False, page=None
    ) -> None:
        if (len(locators) == 0) or (len(scored_elements) == 0):
            print("no scored elements or locators")
            return

        for i, el in enumerate(scored_elements):
            el.locator = locators[i]

        if not is_sorted:
            scored_elements = sorted(scored_elements, key=lambda x: x.score, reverse=True)

        scored_elements = scored_elements if is_sorted else sorted(scored_elements, key=lambda x: x.score, reverse=True)

        _highlight = [False, None]
        for e_i, elem in enumerate(scored_elements):
            if isinstance(elem.locator, Locator | LocatorSync):
                elem.locator.first.highlight()
                _highlight = [True, e_i]

                if e_i >= 1:
                    print(f"---highest scored element is {e_i}th in the list. score below doesnt match---")

                break

        if not _highlight[0]:
            print("---locator out of frame. not highlighting")

        if len(scored_elements) < 2:
            breakpoint()

        print(
            "---"
            + f"LLM[high-score:{scored_elements[0].score},{scored_elements[0].next_command}][low-score:{scored_elements[-1].score},{scored_elements[-1].next_command}]"
            + "---"
        )

    def compare_all_page_elements(
        self,
        objective: str,
        page_state: PageState | List[str] = None,
        page_elements: List[str] = None,
        url: str = None,
    ):
        if page_state:
            url = page_state.url
            page_elements = page_state.page_elements

        state_str = StubTemplates.state(
            objective=objective,
            url=url,
            browser_content="\n".join([f"- {el}" for el in page_elements]),
            previous_commands="None",
        )
        opts = [{"next_command": e} for e in page_elements]

        async def _a_fn():
            return [
                ScoredNextAction(**opt)
                for opt in await self.lm_controller.score_actions(
                    str_template=StubTemplates.prompt, options=opts, state=state_str
                )
            ]

        def _fn():
            return [
                ScoredNextAction(**opt)
                for opt in self.lm_controller.score_actions_sync(
                    str_template=StubTemplates.prompt, options=opts, state=state_str
                )
            ]

        fn = _a_fn if self.use_async else _fn
        return fn()

    async def compare_all_page_elements_async(
        self,
        objective: str,
        page_state: PageState | List[str] = None,
        page_elements: List[str] = None,
        url: str = None,
        return_sorted: bool = False,
    ) -> List[ScoredNextAction]:
        """given the page state, compare all page elements against the objective
        Args:
            page_state (PageState): current page state
            objective (str): current objective
        """

        if page_state:
            url = page_state.url
            page_elements = page_state.page_elements

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

    def compare_all_page_elements_sync(
        self,
        objective: str,
        page_state: PageState | List[str] = None,
        page_elements: List[str] = None,
        url: str = None,
        return_sorted: bool = False,
    ) -> List[ScoredNextAction]:
        """given the page state, compare all page elements against the objective
        # TODO might be best to keep this
        """

        if page_state:
            url = page_state.url
            page_elements = page_state.page_elements

        state_text = StubTemplates.state(
            objective=objective,
            url=url,
            browser_content="\n".join([f"- {el}" for el in page_elements]),
            previous_commands="None",
        )

        options = [{"next_command": e} for e in page_elements]
        scored_opts = self.lm_controller.score_actions_sync(
            str_template=StubTemplates.prompt, options=options, state=state_text
        )
        scored_opts = [ScoredNextAction(**opt) for opt in scored_opts]

        if return_sorted:
            scored_opts = sorted(scored_opts, key=lambda x: x.score, reverse=True)

        return scored_opts

    # def predict_next_action(self, state: ClippyState) -> ControllerResponse:
    def predict_next_action(self, page_state: PageState, objective: str) -> List[ScoredNextAction]:
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
        page_state: PageState = None,
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

    def predict_target_cmd(self, objective: str, next_cmd: List[str], page_state: PageState) -> str:
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

    def generate_text_for_input(self, state: ClippyState) -> ClippyState:
        cmd = state.response.cmd

        generated_txt = self.predict_target_cmd(objective=state.objective, next_cmd=cmd, page_state=state.page_state)

        initial_prompt = (
            f"The LM thinks the next command should be: {' '.join(cmd) + generated_txt}\nIs that correct? (y/n): "
        )

        def valid_response_cb(resp: str):
            pass

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


class InstructorStepHandler:
    def __init__(self, parent: Instructor):
        self.parent = parent

    def first_step(self, state: ClippyState, parent: Instructor) -> ClippyState:
        scored_actions = self.parent.predict_next_action(page_state=state.page_state, objective=state.objective)
        default_next_action = scored_actions[0].next_command
        initial_prompt = f"The LM thinks the next command should be: {default_next_action}\nIs that correct? (y/n): "

        def valid_responses_cb(resp: str):
            if resp in ["click", "type"]:
                return resp
            return None

        feedback_handler = HandleUserFeedback(
            initial_prompt=initial_prompt,
            default_feedback=default_next_action,
            error_prompt="What is correct action? (click/type): ",
            response_callback=valid_responses_cb,
            after_feedback=self.second_step,
        )

        next_steps = {
            "pre_step": None,
            "next_step": feedback_handler.after_feedback,
            "post_step": self.post_state,
        }

        response = ControllerResponse(
            feedback_fn=feedback_handler.make_feedback_fn(),
            next_steps=next_steps,
        )

        return state._replace(response=response)

    def second_step(self, state: ClippyState) -> ClippyState:
        cmd = state.response.cmd
        action = cmd[0]
        page_elements = state.page_state.page_elements
        scored_opts = self.parent.predict_action_target(
            action=action, objective=state.objective, page_state=state.page_state
        )

        default_target = scored_opts[0].target.split(" ")[:2]
        printed_page_elements = "\n".join(["- " + el for el in page_elements])
        initial_prompt = f"From the available page elements:\n{printed_page_elements}\nThe LM thinks for the action({action}) should be: {default_target}\nIs that correct? (y/n): "

        def valid_responses_cb(resp: str):
            if isinstance(resp, list):
                resp = resp[1]

            try:
                res = int(resp)
                if res in range(len(page_elements)):
                    return page_elements[res]
            except ValueError:
                print("Not a valid response, try again")
                return None
            return None

        feedback_handler = HandleUserFeedback(
            initial_prompt=initial_prompt,
            default_feedback=default_target,
            error_prompt=f"What is correct target?\{printed_page_elements}\n---\nEnter (0-{len(page_elements) - 1})",
            response_callback=valid_responses_cb,
            after_feedback=self.third_step,
        )

        next_steps = {
            "pre_step": None,
            "next_step": feedback_handler.after_feedback,
            "post_step": self.post_state,
        }

        state.response.next_steps = next_steps
        state.response.feedback_fn = feedback_handler.make_feedback_fn()
        return state

    def post_state(self, state: ClippyState) -> ClippyState:
        if state.response.feedback_fn:
            state.response.feedback_fn(state)

        return state


# async def _get_elements_of_interest(self, cdp_client, page: Page, timeout=2):
#     start_time = time.time()
#     elements_of_interest = []
#     logger.info("parsing tree...", end="")

#     while ((time.time() - start_time) < timeout) and (len(elements_of_interest) == 0):
#         tree = await self.crawler.get_tree(self.dom_parser.cdp_snapshot_kwargs)
#         elements_of_interest = await self.dom_parser.crawl_async(tree=tree, page=page)
#     return elements_of_interest


# # @timer
# async def llm_assist_hook(self, page: Page):
#     if not self.use_llm:
#         return

#     if (elements_of_interest := await self._get_elements_of_interest(self.cdp_client, page)) == []:
#         logger.info("tried to crawl but didnt work...")
#         return

#     # elements_of_interest = await self.dom_parser.crawl_async(self.cdp_client, page)
#     element_buffer = self.dom_parser.page_element_buffer
#     ids_of_interest = self.dom_parser.ids_of_interest

#     if not ids_of_interest:
#         logger.info("no elements of interest, skipping...")
#         return

#     locators = await asyncio.gather(
#         *[self.dom_parser._get_from_location_async(element_buffer[i], page) for idx, i in enumerate(ids_of_interest)]
#     )

#     # shorten it for time being
#     elements_of_interest = elements_of_interest[:50]
#     scored_elements = await self.instructor.compare_all_page_elements_async(
#         self.objective, page_elements=elements_of_interest, url=page.url
#     )

#     if not scored_elements:
#         breakpoint()

#     return await self.instructor.highlight_from_scored_async(scored_elements, locators=locators, page=page)
