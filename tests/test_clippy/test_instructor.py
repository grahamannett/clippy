import unittest


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
