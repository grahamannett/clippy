import unittest


class TestInstructor(unittest.IsolatedAsyncioTestCase):
    def test_suggest_from_fixture(self):
        instructor = Instructor(use_async=True)
        filepath = "tests/fixtures/soap/llm-assist.pt"
        data = torch.load(filepath)
        pel = data["page_elements"]

        pelb = data["page_element_buffer"]
        pel_ids = data["page_elements_ids"]
        url = data["url"]
        objective = "buy soap"

        url = url[:100]
        pel = pel[:20]

        instructor = Instructor()
        import time

        state = PageState(url=url, page_elements=pel)
        # state =

    async def test_show_suggest_on_page(self):
        url = "https://www.google.com/search?q=hand+soap"
        objective = "buy hand soap"
        instructor = Instructor(objective=objective, use_async=True)
        dom_parser = DOMSnapshotParser(keep_device_ratio=False)
        # page = await Crawler.get_page(url)
        async with Crawler(start_page=url, headless=False, key_exit=False) as crawler:
            page = crawler.page
            cdp_client = await crawler.get_cdp_client()
            await instructor.
            # tree = await crawler.get_tree(dom_parser.cdp_snapshot_kwargs, cdp_client=cdp_client)
            # self.assertIsNotNone(tree)


    async def test_scoring_actions(self):
        instructor = Instructor(use_async=True)

        scored_actions = await instructor.compare_all_page_elements(
            objective="made up objective", page_elements=["link 1", "link 2", "link 3"]
        )
        breakpoint()


    async def test_embeds(self):
        objective1 = "buy bodywash"
        objective2 = "buy shampoo"
        objective3 = "find a ticket for taylor swift concert"
        controller = Controller.using_client(Controller.COHERE)
        client = CohereController.get_client_async(api_key=environ.get("COHERE_KEY"), check_api_key=True)
        controller = CohereController(client=client)
        _, obj, scores = await controller.find_most_similar_str(
            objective=objective1, objectives=[objective2, objective3], return_all=True
        )

        self.assertEqual(obj, objective2)
        self.assertTrue(scores[0] > scores[1])
        await controller.close()


if __name__ == "__main__":
    import torch

    data = "tests/fixtures/soap/llm-assist.pt"
    data = torch.load(data)
    pel = data["page_elements"]

    pelb = data["page_element_buffer"]
    pel_ids = data["page_elements_ids"]
    url = data["url"]
    objective = "buy soap"

    url = url[:100]
    pel = pel[:20]

    instructor = Instructor()
    instructor_async = Instructor(use_async=True)
    import asyncio
    import time

    state = PageState(url=url, page_elements=pel)
