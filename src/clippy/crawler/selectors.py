from typing import Awaitable, List


class Selector:
    name: str
    script: str

    @classmethod
    def register(cls, pw) -> List[Awaitable[None] | None]:
        selectors = [
            pw.selectors.register(**TagSelector.todict()),
            pw.selectors.register(**PosSelector.todict()),
        ]
        return selectors

    @classmethod
    def todict(cls):
        return {"name": cls.name, "script": cls.script}


class TagSelector(Selector):
    name = "tag"
    script = """
{
    // Returns the first element matching given selector in the root's subtree.
    query(root, selector) {
        return root.querySelector(selector);
    },
    // Returns all elements matching given selector in the root's subtree.
    queryAll(root, selector) {
        return Array.from(root.querySelectorAll(selector));
    }
}"""


class PosSelector(Selector):
    name = "pos"
    script = """
{

    query(root, selector) {
        let [x, y] = selector.split(",").map((v) => parseInt(v));
        return document.elementFromPoint(x, y);
    },

    queryAll(root, selector) {
        let [x, y] = selector.split(",").map((v) => parseInt(v));
        // you want document here as root throws an error
        return Array.from(document.elementsFromPoint(x, y));
    }
}
"""


pos_returner = """
{
}
"""


# class SelectorExtension:
#     tag_selector: str = tag_selector
#     pos_selector: str = pos_selector

#     @staticmethod
#     def setup_tag_selectors(pw) -> List[Awaitable[None] | None]:
#         selectors = [
#             pw.selectors.register("tag", SelectorExtension.tag_selector),
#             pw.selectors.register("pos", SelectorExtension.pos_selector),
#         ]
#         return selectors
