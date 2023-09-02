import sys
import re
from dataclasses import dataclass
from typing import Iterator, List, Any, Dict, Tuple
import asyncio
from playwright.async_api import CDPSession, Page, Locator

from clippy.crawler.crawler import Crawler
from clippy.states.actions import Position

black_listed_elements = set(
    [
        "html",
        "head",
        "title",
        "meta",
        "iframe",
        "body",
        "script",
        "style",
        "path",
        "svg",
        "br",
        "::marker",
    ]
)

# NOTE:
# this code is primarily from weblm but i need to use it
# i moved out these functions as the original _crawl function is very long and almost incomprehensible what it is doing
# to the best of my knowledge it is doing 2 things:
#       1. it is creating elements_of_interest which is a list of strings that are of some form like
#           'element-type number-id info'
#           where info is like class or text or something from the html.  sometimes this info is super good and
#           helpful but other times its kinda just random stuff from some class that is a random string
#       2. the other main thing it does is page_element_buffer which is a dict for each element on the page that is
#           something you can 'use', meaning its like inputs/clicks/etc.  The dict contains:
#              [
#                    'node_index', 'backend_node_id', 'node_name', 'node_value', 'node_meta',
#                     'is_clickable', 'origin_x', 'origin_y', 'center_x', 'center_y'
#              ]


TYPEABLE = ["input", "select"]
CLICKABLE = ["link", "button"]


@dataclass
class ElementOutOfViewport:
    scroll: Tuple[int, int]
    bounds: Tuple[int, int, int, int]


def element_allowed(element: str):
    for t in TYPEABLE + CLICKABLE:
        if t in element:
            return True
    return False


def filter_page_elements(elements: List[str]) -> Iterator[str]:
    for element in elements:
        if element_allowed(element):
            yield element


def get_action_type(element: str) -> str:
    for t in TYPEABLE:
        if t in element:
            return "type"

    for t in CLICKABLE:
        if t in element:
            return "click"

    raise ValueError(f"Could not find action type for {element}")


def convert_name(node_name: str, has_click_handler: bool):
    if node_name == "a":
        return "link"
    elif node_name in ["select", "img", "input"]:
        return node_name
    elif node_name in "button" or has_click_handler:  # found pages that needed this quirk
        return "button"
    elif node_name == "textarea":
        return "input"
    else:
        return "text"


def find_attributes(attributes: List[int], keys: List[str], strings: List[str]):
    values = {}

    for [key_index, value_index] in zip(*(iter(attributes),) * 2):
        if value_index < 0:
            continue
        key = strings[key_index]
        value = strings[value_index]

        if key in keys:
            values[key] = value
            keys.remove(key)

            if not keys:
                return values

    return values


def add_to_hash_tree(
    hash_tree: Dict[str, Tuple[bool, Any]],
    tag: List[str],
    node_id: int,
    node_name: str,
    parent_id: int,
    strings: List[str],
    node_names: List[int],
    parent: List[int],
    attributes: List[List[int]],
):
    parent_id_str = str(parent_id)
    if not parent_id_str in hash_tree:
        parent_name = strings[node_names[parent_id]].lower()
        grand_parent_id = parent[parent_id]

        add_to_hash_tree(
            hash_tree, tag, parent_id, parent_name, grand_parent_id, strings, node_names, parent, attributes
        )

    is_parent_desc_anchor, anchor_id = hash_tree[parent_id_str]

    element_attributes = find_attributes(attributes[node_id], ["role"], strings)

    # even if the anchor is nested in another anchor, we set the "root" for all descendants to be ::Self
    if node_name in tag or element_attributes.get("role") in tag:
        value = (True, node_id)
    elif is_parent_desc_anchor:  # reuse the parent's anchor_id (which could be much higher in the tree)
        value = (True, anchor_id)
    else:
        value = (
            False,
            None,
        )  # not a descendant of an anchor, most likely it will become text, an interactive element or discarded

    hash_tree[str(node_id)] = value

    return value


def _out_of_viewport_element(element_buffer: Dict[str, Any], page_viewport: Dict[str, int]):
    # TODO factor in if scrollX, scrollY are not 0

    height, width = page_viewport["height"], page_viewport["width"]

    scroll_x_factor = width // 2
    scroll_y_factor = height // 2

    el_x, el_y, el_w, el_h = element_buffer["bounds"]

    scroll_x = 0
    scroll_y = 0

    while (el_y + el_h) > height:
        # scroll down
        el_y -= scroll_y_factor
        scroll_y += scroll_y_factor

    while (el_x + el_w) > width:
        # scroll right
        el_x -= scroll_x_factor
        scroll_x += scroll_x_factor

    # return (scroll_x, scroll_y), (el_x, el_y, el_w, el_h)
    return ElementOutOfViewport((scroll_x, scroll_y), (el_x, el_y, el_w, el_h))


class Locators:
    ElementOutOfViewport = ElementOutOfViewport
    Locator = Locator


class DOMSnapshotParser:
    cdp_snapshot_kwargs = {
        "computedStyles": ["display"],
        "includeDOMRects": True,
        "includePaintOrder": True,
    }

    def __init__(self, crawler: Crawler = None, keep_device_ratio: bool = False, *args, **kwargs):
        super().__init__()
        self.keep_device_ratio = keep_device_ratio
        self.page_element_buffer = {}
        self.elements_of_interest = []

        # allow for crawler to be passed for dev purposes
        self.crawler = crawler
        self.page = crawler.page
        self.cdp_client = crawler.cdp_client
        self._current_url = None

    async def _page_sizes(self, page: Page):
        device_pixel_ratio = await page.evaluate("window.devicePixelRatio")
        win_scroll_x = await page.evaluate("window.scrollX")
        win_scroll_y = await page.evaluate("window.scrollY")
        win_upper_bound = await page.evaluate("window.pageYOffset")
        win_left_bound = await page.evaluate("window.pageXOffset")
        win_width = await page.evaluate("window.screen.width")
        win_height = await page.evaluate("window.screen.height")
        return (device_pixel_ratio, win_scroll_x, win_scroll_y, win_upper_bound, win_left_bound, win_width, win_height)

    def get_loc_helper(self, element_buffer: Dict[str, Any]) -> Locator:
        origin_x, orgin_y, center_x, center_y = (
            element_buffer["origin_x"],
            element_buffer["origin_y"],
            element_buffer["center_x"],
            element_buffer["center_y"],
        )

        x = origin_x + center_x
        y = orgin_y + center_y

        loc = self.page.locator(f"pos={x},{y}")
        loc.position = Position(x, y)
        return loc

    def element_allowed(self, element: str):
        return element_allowed(element)

    async def get_locator(self, element: str, element_id: int) -> Locator | ElementOutOfViewport:
        if not element_allowed(element):
            return None
        element_buffer = self.page_element_buffer[element_id]
        loc = self.get_loc_helper(element_buffer)
        if await loc.count() <= 0:
            return _out_of_viewport_element(element_buffer, self.page.viewport_size)

        return loc

    def need_crawl(self, page: Page):
        if not isinstance(
            page.url, str
        ):  # if its not a str then page is being constructed or something and we cant do anything
            return False

        if (self._current_url != page.url) or (self.elements_of_interest == []):
            self._current_url = page.url
            return True

        return False

    async def get_tree(self):
        self.tree = await self.crawler.cdp_client.send(
            "DOMSnapshot.captureSnapshot",
            self.cdp_snapshot_kwargs,
        )

    async def parse(self) -> List[str]:
        await self.get_tree()
        pixel_ratio, win_s_x, win_s_y, upper_b, lower_b, win_w, win_h = await self.crawler.page_size()
        self.parse_tree(self.tree, upper_b, win_w, lower_b, win_h, pixel_ratio)

        return self.elements_of_interest

    def parse_tree(
        self,
        tree: Dict[str, Any],
        win_upper_bound: int = 0,
        win_width: int = 1280,
        win_left_bound: int = 0,
        win_height: int = 1080,
        device_pixel_ratio: int = 1,
        platform: str = "darwin",
    ):
        """
        returns:
            elements_of_interest: List[str] - list of strings that are of some form like
                ['button 1 hnname', 'link 2 "Hacker News"', 'link 3 "new"', 'text 4 "|"', ... ]
            ids_of_interest: List[ids] - list of ids of elements_of_interest that map to page_element_buffer
        """
        page_element_buffer = self.page_element_buffer

        page_state_as_text = []
        # TODO: FIX THIS, ITS NOT WORKIGN FOR ME WITH AN EXTERNAL MONITOR
        if (
            (getattr(self, platform, sys.platform) == "darwin")
            and (device_pixel_ratio == 1)
            and not self.keep_device_ratio
        ):  # lies
            device_pixel_ratio = 2
            # device_pixel_ratio = 1

        win_right_bound = win_left_bound + win_width * 2
        win_lower_bound = win_upper_bound + win_height * 2

        percentage_progress_start = 1
        percentage_progress_end = 2

        page_state_as_text.append(
            {
                "x": 0,
                "y": 0,
                "text": "[scrollbar {:0.2f}-{:0.2f}%]".format(
                    round(percentage_progress_start, 2), round(percentage_progress_end)
                ),
            }
        )

        strings = tree["strings"]
        document = tree["documents"][0]
        nodes = document["nodes"]
        backend_node_id = nodes["backendNodeId"]
        attributes = nodes["attributes"]
        node_value = nodes["nodeValue"]
        parent = nodes["parentIndex"]
        node_types = nodes["nodeType"]
        node_names = nodes["nodeName"]
        is_clickable = set(nodes["isClickable"]["index"])

        text_value = nodes["textValue"]
        text_value_index = text_value["index"]
        text_value_values = text_value["value"]

        input_value = nodes["inputValue"]
        input_value_index = input_value["index"]
        input_value_values = input_value["value"]

        input_checked = nodes["inputChecked"]
        layout = document["layout"]
        layout_node_index = layout["nodeIndex"]
        bounds = layout["bounds"]
        styles = layout["styles"]

        cursor = 0
        html_elements_text = []

        child_nodes = {}
        elements_in_view_port = []

        anchor_ancestry = {"-1": (False, None)}
        button_ancestry = {"-1": (False, None)}
        select_ancestry = {"-1": (False, None)}

        for index, node_name_index in enumerate(node_names):
            node_parent = parent[index]
            node_name = strings[node_name_index].lower()

            is_ancestor_of_anchor, anchor_id = add_to_hash_tree(
                hash_tree=anchor_ancestry,
                tag=["a"],
                node_id=index,
                node_name=node_name,
                parent_id=node_parent,
                strings=strings,
                node_names=node_names,
                parent=parent,
                attributes=attributes,
            )

            is_ancestor_of_button, button_id = add_to_hash_tree(
                button_ancestry,
                ["button"],
                index,
                node_name,
                node_parent,
                strings=strings,
                node_names=node_names,
                parent=parent,
                attributes=attributes,
            )

            is_ancestor_of_select, select_id = add_to_hash_tree(
                select_ancestry,
                ["select"],
                index,
                node_name,
                node_parent,
                strings=strings,
                node_names=node_names,
                parent=parent,
                attributes=attributes,
            )

            try:
                cursor = layout_node_index.index(select_id) if is_ancestor_of_select else layout_node_index.index(index)
            except:
                continue

            if node_name in black_listed_elements:
                continue

            style = map(lambda x: strings[x], styles[cursor])
            if "none" in style:
                continue

            [x, y, width, height] = bounds[cursor]
            x /= device_pixel_ratio
            y /= device_pixel_ratio
            width /= device_pixel_ratio
            height /= device_pixel_ratio

            elem_left_bound = x
            elem_top_bound = y
            elem_right_bound = x + width
            elem_lower_bound = y + height

            # comment this bit out to process the whole thing
            partially_is_in_viewport = (
                elem_left_bound < win_right_bound
                and elem_right_bound >= win_left_bound
                and elem_top_bound < win_lower_bound
                and elem_lower_bound >= win_upper_bound
            )

            if not partially_is_in_viewport:
                continue

            meta_data = []

            # inefficient to grab the same set of keys for kinds of objects but its fine for now
            element_attributes = find_attributes(
                attributes=attributes[index],
                keys=[
                    "type",
                    "placeholder",
                    "aria-label",
                    "name",
                    "class",
                    "id",
                    "title",
                    "alt",
                    "role",
                    "value",
                    "aria-labelledby",
                    "aria-description",
                    "aria-describedby",
                ],
                strings=strings,
            )

            ancestor_exception = is_ancestor_of_anchor or is_ancestor_of_button or is_ancestor_of_select
            ancestor_node_key = None
            if ancestor_exception:
                if is_ancestor_of_anchor:
                    ancestor_node_key = str(anchor_id)
                elif is_ancestor_of_button:
                    ancestor_node_key = str(button_id)
                elif is_ancestor_of_select:
                    ancestor_node_key = str(select_id)
            ancestor_node = None if not ancestor_exception else child_nodes.setdefault(str(ancestor_node_key), [])

            if node_name == "#text" and ancestor_exception:
                text = strings[node_value[index]]
                if text == "|" or text == "•":
                    continue
                ancestor_node.append({"type": "type", "value": text})
            else:
                if node_name == "input" and element_attributes.get("type") == "submit":
                    node_name = "input"
                    # element_attributes.pop("type", None)  # prevent [button ... (button)..]
                    # element_attributes.pop("role", None)  # prevent [button ... (button)..]

                elif (
                    # (node_name == "input" and element_attributes.get("type") == "submit")
                    node_name == "button"
                    or element_attributes.get("role") == "button"
                ):
                    if node_name == "input":
                        breakpoint()

                    node_name = "button"
                    element_attributes.pop("type", None)  # prevent [button ... (button)..]
                    element_attributes.pop("role", None)  # prevent [button ... (button)..]

                if element_attributes.get("role") == "textbox":
                    node_name = "input"

                for key in element_attributes:
                    if ancestor_exception and not is_ancestor_of_select:
                        ancestor_node.append({"type": "attribute", "key": key, "value": element_attributes[key]})
                    else:
                        meta_data.append(element_attributes[key])

            element_node_value = None

            if node_value[index] >= 0:
                element_node_value = strings[node_value[index]]

                # commonly used as a seperator, does not add much context - lets save ourselves some token space
                if element_node_value == "|":
                    continue
            elif node_name == "input" and index in input_value_index and element_node_value is None:
                node_input_text_index = input_value_index.index(index)
                text_index = input_value_values[node_input_text_index]
                if node_input_text_index >= 0 and text_index >= 0:
                    element_node_value = strings[text_index]

            # remove redudant elements
            if ancestor_exception and (node_name not in ["a", "button", "select"]):
                continue

            elements_in_view_port.append(
                {
                    "node_index": str(index),
                    "backend_node_id": backend_node_id[index],
                    "node_name": node_name,
                    "node_value": element_node_value,
                    "node_meta": meta_data,
                    "is_clickable": index in is_clickable,
                    "origin_x": int(x),
                    "origin_y": int(y),
                    "center_x": int(x + (width / 2)),
                    "center_y": int(y + (height / 2)),
                    "bounds": bounds[cursor],
                }
            )

        # lets filter further to remove anything that does not hold any text nor has click handlers + merge text from leaf#text nodes with the parent
        elements_of_interest = []
        ids_of_interest = []
        elements_locator = {}
        id_counter = 0
        flagg = False
        for e_idx, element in enumerate(elements_in_view_port):
            node_index = element.get("node_index")
            node_name = element.get("node_name")
            node_value = element.get("node_value")
            is_clickable = element.get("is_clickable")
            origin_x = element.get("origin_x")
            origin_y = element.get("origin_y")
            center_x = element.get("center_x")
            center_y = element.get("center_y")
            meta_data = element.get("node_meta")
            bounds = element.get("bounds")

            inner_text = f"{node_value} " if node_value else ""
            meta = ""

            if node_index in child_nodes:
                for child in child_nodes.get(node_index):
                    entry_type = child.get("type")
                    entry_value = child.get("value")

                    if entry_type == "attribute":
                        entry_key = child.get("key")
                        _append_str = f'{entry_key}="{entry_value}"'
                        meta_data.append(_append_str)
                    else:
                        inner_text += f"{entry_value} "

            if len(meta_data) > 2 or inner_text != "":
                meta_data = list(filter(lambda x: not re.match('(class|id)=".+"', x), meta_data))

            if meta_data:
                meta_string = " ".join(meta_data)
                meta = f" {meta_string}"

            if inner_text != "":
                inner_text = f"{inner_text.strip()}"

            converted_node_name = convert_name(node_name, is_clickable)

            # not very elegant, more like a placeholder
            if (
                converted_node_name not in ["button", "link", "input", "img", "textarea", "select"]
                and inner_text.strip() == ""
            ):
                continue
            elif converted_node_name == "button" and meta == "" and inner_text.strip() == "":
                continue

            page_element_buffer[id_counter] = element

            meta = re.sub("\s+", " ", meta)
            inner_text = re.sub("\s+", " ", inner_text)

            element["selectors"] = {
                "meta": meta,
                "inner_text": inner_text,
                "converted_node_name": converted_node_name,
            }

            if inner_text != "":
                to_append = f"""{converted_node_name} {id_counter}{meta} \"{inner_text}\""""
                elements_of_interest.append(to_append)
                ids_of_interest.append(id_counter)
            elif converted_node_name in ["input", "button", "textarea"] or "alt" in meta:
                to_append = f"""{converted_node_name} {id_counter}{meta}"""
                elements_of_interest.append(to_append)
                ids_of_interest.append(id_counter)
            elif converted_node_name == "select" and meta != "":
                to_append = f"""{converted_node_name} {id_counter}{meta}"""
                elements_of_interest.append(to_append)
                ids_of_interest.append(id_counter)
            else:
                # print(f"""{converted_node_name} {id_counter}{meta}""")
                pass  # pass so id counter is still incremented
                # continue
            id_counter += 1

        self.elements_of_interest, self.ids_of_interest = elements_of_interest, ids_of_interest
        return elements_of_interest, ids_of_interest
