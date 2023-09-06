import unittest
import json
import torch

from clippy.stubs import StubTemplates
from clippy.controllers import Controller
from clippy.controllers.apis.cohere_controller_utils import CohereJSONEncoder
from clippy.controllers.controller_config import ResponseConfig

from cohere.responses.generation import Generation, Generations, TokenLikelihood


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
        self.controller = Controller.Clients.Cohere()

    async def asyncTearDown(self):
        await self.controller.close()

    async def test_tokenize(self):
        co = self.controller
        test_string = "tokenized string"
        base_tokens = await co.tokenize(test_string)

        ResponseConfig.return_raw = True

        tokens = await co.tokenize(test_string)

        assert tokens.tokens == base_tokens

        tokens = (await co.tokenize(test_string)).tokens
        assert len(tokens) > 2

        string = (await co.detokenize(tokens=tokens)).text
        assert string == test_string

        bad_string = (await co.detokenize(tokens=tokens + [9000])).text
        assert string != bad_string

    async def test_embeds(self):
        controller = self.controller
        test_string = "tokenized string"
        embeddings = await controller.embed(test_string)
        assert len(embeddings.embeddings[0]) == 4096

    async def test_controller_score(self):
        co = self.controller

        scored_text = await co.score_text("This would be a good sentence to score.")
        bad_scored_text = await co.score_text("Rogue asdf !HEllo Friend!! Yessir.")
        assert scored_text > bad_scored_text


class TestCohere(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.response_generate_pt = "test_output/cohere_responses/test_generate.pt"
        self.response_embed_pt = "test_output/cohere_responses/test_embed.pt"

    async def test_generate(self):
        co = Controller.Clients.Cohere()
        response = await co.generate(prompt="test generate")
        torch.save(response, self.response_generate_pt)
        await co.close()

    async def test_embed(self):
        co = Controller.Clients.Cohere()
        response = await co.embed(texts="test generate")
        torch.save(response, self.response_embed_pt)
        await co.close()

    async def test_encode(self):
        response = torch.load(self.response_generate_pt)

        # generation_encoded = json.dumps(response.generations[0].__dict__, cls=CohereJSONEncoder)
        # generation_dict = json.loads(generation_encoded)
        # generation = Generation(**generation_dict)

        generations = [json.dumps(g.__dict__, cls=CohereJSONEncoder) for g in response.generations]
        generations = [Generation(**json.loads(g)) for g in generations]

        generation = Generations(generations=generations, return_likelihoods=response.return_likelihoods)

        data = json.dumps(response, cls=CohereJSONEncoder)

        dict_data = json.loads(data)
        generations = [Generation.from_response(d) for d in dict_data["data"]]
        cohere_struct = Generations(
            generations=generations, return_likelihoods=dict_data["return_likelihoods"], meta=dict_data["meta"]
        )

        response = torch.load(self.response_embed_pt)
        data = json.dumps(response, cls=CohereJSONEncoder)
