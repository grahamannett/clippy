class InstructorStepHandler:
    def __init__(self, parent: Instructor):
        self.parent = parent

    def first_step(self, state: "ClippyState", parent: Instructor) -> "ClippyState":
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

    def second_step(self, state: "ClippyState") -> "ClippyState":
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

    def post_state(self, state: "ClippyState") -> "ClippyState":
        if state.response.feedback_fn:
            state.response.feedback_fn(state)

        return state


async def _get_elements_of_interest(self, cdp_client, page: Page, timeout=2):
    import time

    start_time = time.time()
    elements_of_interest = []
    logger.info("parsing tree...", end="")

    while ((time.time() - start_time) < timeout) and (len(elements_of_interest) == 0):
        tree = await self.crawler.get_tree(self.dom_parser.cdp_snapshot_kwargs)
        elements_of_interest = await self.dom_parser.crawl_async(tree=tree, page=page)
    return elements_of_interest


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


def get_page_state(self, state: "ClippyState") -> "ClippyState":
    """
    get the observation (meaning the page elements )
    """

    page_elements = state.crawler.crawl()
    page_state = PageState(url=state.crawler.page.url, page_elements=page_elements)
    state.page_state = page_state
    return state


def step(self, state: "ClippyState") -> "ClippyState":
    """
    loop is like this:
    1. get the page state (includes page elements)
    2. get prerequisites for state
    2. process page with instructor (get next command and next command target)
    3. get feedback

    """

    if state.pre_step:
        state = state.pre_step(state)

    state = state.next_step(state)

    if state.post_step:
        state = state.post_step(state)

    if self.clear_step_states:
        state.pre_step = None
        state.post_step = None

    state.pre_step = state.response.next_steps["pre_step"]
    state.next_step = state.response.next_steps["next_step"]
    state.post_step = state.response.next_steps["post_step"]

    return state


@dataclass
class PageState:
    url: str = None
    page_elements: List[str] = None

    previous_state: "PageState" = None


@dataclass
class ClippyState:
    objective: str = None

    response: Response = None
    response_type: str = None

    page_state: PageState = None

    pre_step: Callable[..., Any] = None
    next_step: Callable[..., Any] = None
    post_step: Callable[..., Any] = None

    def _replace(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self


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

        # print(
        #     "---"
        #     + f"LLM[high-score:{scored_elements[0].score},{scored_elements[0].next_command}][low-score:{scored_elements[-1].score},{scored_elements[-1].next_command}]"
        #     + "---"
        # )

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