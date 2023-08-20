import unittest
from os import environ
from clippy.controllers.apis.cohere_controller import CohereController


prompt_test_str = """Given:
    (1) an objective that you are trying to achieve
    (2) the URL of your current web page
    (3) a simplified text description of what's visible in the browser window

Your commands are:
    click X - click on element X.
    type X "TEXT" - type the specified text into input X
    summary - summarize the text in the page

Present state:
Objective: objective1
Current URL: url1
Current Browser Content:
---
- 1
- 2
---
Previous actions:
None
Next Command:"""

from clippy.stubs import StubTemplates


class TestStubs(unittest.IsolatedAsyncioTestCase):
    def test_state(self):
        state = StubTemplates.state
        state_str = state.render(objective="objective1", url="url1", browser_content="- 1\n- 2", previous_commands="None")

        prompt = StubTemplates.prompt
        prompt_str = prompt.render(state=state_str)
        breakpoint()

        self.assertEquals(prompt_str, prompt_test_str)


class TestInstructor(unittest.IsolatedAsyncioTestCase):
    def test_instructor(self):
        pass

    async def test_embeds(self):
        objective1 = "buy bodywash"
        objective2 = "buy shampoo"
        objective3 = "find a ticket for taylor swift concert"
        client = CohereController.get_client_async(api_key=environ.get("COHERE_KEY"), check_api_key=True)
        controller = CohereController(client=client)
        _, obj, scores = await controller.find_most_similar_str(objective=objective1, objectives=[objective2, objective3], return_all=True)

        self.assertEqual(obj, objective2)
        self.assertTrue(scores[0] > scores[1])
        await controller.close()

