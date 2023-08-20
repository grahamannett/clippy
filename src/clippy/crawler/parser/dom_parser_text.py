# NOTE:
# before I knew you could extend playwright with selectors, I was trying to parse the strings
# this is from that but it seems very unlikely you can get that to work bugfree and consistently across all sites
# use the selectors and grab by pos=x,y instead

from typing import List
from playwright.sync_api import Page, Locator


def _clean_str_quotes(string: str, empty_ret: str = None) -> str:
    if string == "":
        return empty_ret

    # if string[0] == '"' or string[0] == "'":
    #     string = string[1:-1]
    # if string[-1] == '"' or string[-1] == "'":
    #     string = string[:-1]
    string = string.lstrip('"').rstrip('"')
    string = string.lstrip("'").rstrip("'")
    string = string.lstrip(" ").rstrip(" ")

    return string


def _check_if_only_text(string: str):
    if string.startswith(('"', "'")) and string.endswith(('"', "'")):
        return True
    return False


def _combine_class_names(class_names: List[str]):
    # example: ...combine all the class names into one string that can be used with locator
    # 'node_meta': ['class="LC20lb MBeuO DKV0Md"', 'class="TbwUpd NJjxre iUh30 apx8Vc ojE3Fb"', 'class="
    cleaned_names = []
    for name in class_names:
        if "class=" in name:
            name = name.lstrip("class=")
            name = _clean_str_quotes(name)
            # name = name.replace("class=", "").lstrip('"').rstrip('"')
            if " " in name:
                cleaned_names.extend(name.split(" "))
            else:
                cleaned_names.append(name)
    if cleaned_names == []:
        return None

    class_name = "." + ",.".join(cleaned_names)
    return class_name


def _class_meta_parse_str(name: str):
    name = name.lstrip("class=")
    name = _clean_str_quotes(name)
    # name = name.replace("class=", "").lstrip('"').rstrip('"')
    if " " in name:
        return name.split(" ")
    else:
        return [name]


def _meta_parse_str_generic(name: str):
    if "=" not in name:
        return "class", _clean_str_quotes(name)

    key, value = name.split("=", 1)
    # if '" ' in value:
    #     breakpoint()

    value = _clean_str_quotes(value)
    return key, value


def _combine_node_meta(node_meta: List[str]):
    if node_meta == []:
        return {}

    out = {}
    for meta in node_meta:
        if ("class=" in meta) or ("=" not in meta):
            if "class" not in out:
                out["class"] = []
            out["class"].extend(_class_meta_parse_str(meta))

        else:
            key, value = _meta_parse_str_generic(meta)
            if key not in out:
                out[key] = []
            out[key].append(value)
    return out


def _get_role_info(el_meta: str):
    # example... may have multiple roles based on node_meta
    # 'link 20 role="text" role="text" "Soap - Wikipedia
    roles = []
    while "role=" in el_meta:
        role, el_meta = el_meta.split(" ", 1)
        role_label = role.split("=", 1)[1]
        role_label = _clean_str_quotes(role_label)
        roles.append(role_label)
    return roles, el_meta


def _get_kw_info(el_meta: str):
    tags = []
    _orig = el_meta
    try:
        while '="' in el_meta:
            tag, el_meta = el_meta.split(" ", 1)
            tag_key, tag_value = tag.split("=", 1)

            tag_value = _clean_str_quotes(tag_value)
            tags.append((tag_key, tag_value))
    except ValueError:
        breakpoint()

    if len(el_meta) == 0:
        el_meta = None

    return tags, el_meta


# def _get_by_link,


def _get_by_title(text: str, loc: Page | Locator):
    text = text.lstrip("title=")
    text = _clean_str_quotes(text)
    loc_out = loc.get_by_title(text)
    return loc_out


def _get_by_text(text: str, loc: Page | Locator):
    text = _clean_str_quotes(text)
    loc_out = loc.get_by_text(text)
    return loc_out


def _check_get(loc: Page | Locator):
    loc_out = loc.all()
    if len(loc_out) == 0:
        return loc, "empty"
    elif len(loc_out) > 1:
        return loc_out, "multiple"
    loc_out = loc_out[0]
    return loc_out, "done"


def _loc_from_status(status: str, loc: Locator, old_loc: Locator | Page):
    if status == "empty":
        return old_loc
    elif status == "multiple":
        return loc


def _get_loc_with_buffer(element: str, element_buffer: dict, page: Page):
    # this is possible the worst code i have ever written.  i have no idea how to parse this from the dom snapshot
    # to get the locator.  probably to fix it means changing the dom snapshot tree crawl but that might break other
    # another way to fix this could be using more regex patters but i am not sure if that solves some parts of finding
    # the actual locator, rather it just makes parts of the code cleaner
    # TODO: make len(locs.all()) use locs.count() instead

    tags = []
    text = []

    eb_cpy = element_buffer.copy()

    node_meta = element_buffer["node_meta"]
    node_name = element_buffer["node_name"]
    node_value = element_buffer["node_value"]
    inner_text = element_buffer["selectors"]["inner_text"]
    conv_node_name = element_buffer["selectors"]["converted_node_name"]

    try:
        node_meta = _combine_node_meta(node_meta)
    except:
        breakpoint()

    # if element_buffer["node_index"] in ["269", "125"]:
    #     breakpoint()
    loc = page

    if "title" in node_meta:
        try:
            loc_out = loc.get_by_title(node_meta["title"][0])
        except:
            breakpoint()
        if len(loc_out.all()) == 1:
            return loc_out.first
        elif len(loc_out.all()) == 0:
            print("reverting back to old loc - title")
            loc_out = loc
        breakpoint()
        loc = loc_out

    # search by text ---
    if node_name == "#text" or node_name == "text":
        text = _clean_str_quotes(node_value)
        loc_out = loc.get_by_text(text)

        if len(loc_out.all()) == 1:
            return loc_out.first
        elif len(loc_out.all()) == 0:
            print("reverting back to old loc - #text")
            loc_out = loc
        loc = loc_out
    # --- end search by text

    # search by class ---
    if "class" in node_meta:
        class_str = "." + ",.".join(node_meta["class"])
        loc_out = loc.locator(class_str)
        if len(loc_out.all()) == 1:
            return loc_out.first
        elif len(loc_out.all()) == 0:
            breakpoint()
        elif inner_text != "":
            loc_out = loc_out.filter(has_text=inner_text)
            if len(loc_out.all()) == 1:
                return loc_out.first
            if len(loc_out.all()) == 0:
                breakpoint()

        if len(loc_out.all()) == 0:
            breakpoint()
            print("reverting back to old loc - class")
            loc_out = loc
        # seems like sometimes class makes it so the actual element is not in the locators so maybe just keep loc = old loc? or move class stuff to the very end
        # loc = loc_out
    # --- end search by class

    # search by text if theres no node_meta info ---
    if (node_meta is None) and (node_value != None) and (node_value != ""):
        loc_out = loc.get_by_text(node_value)
        if len(loc_out.all()) == 1:
            return loc_out.first
        elif len(loc_out.all()) == 0:
            print("reverting back to old loc - text")
            loc_out = loc
        loc = loc_out
    # --- end search by text

    # search by title ---
    if "title" in node_meta:
        loc_out = loc.get_by_title(node_meta["title"][0])
        if len(loc_out.all()) == 1:
            return loc_out.first
        elif len(loc_out.all()) == 0:
            print("reverting back to old loc - title")
            loc_out = loc
        breakpoint()
        loc = loc_out
    # --- end search by title

    # search for button ---
    if conv_node_name == "button":
        if conv_node_name != node_name:
            breakpoint()
        if "aria-label" in node_meta:
            loc_out = loc.get_by_role("button", name=node_meta["aria-label"][0])
            if len(loc_out.all()) == 1:
                return loc_out.first
            elif len(loc_out.all()) == 0:
                print("reverting back to old loc - button")
                loc_out = loc
            else:
                # this seems so brittle but sometimes the button search will give you like 3 locs and using the class
                # locator will give you 50+ locs but they arent the ones with button
                for l in loc_out.all():
                    _cls = l.get_attribute("class")
                    if " " in _cls:
                        _cls = _cls.split(" ", 1)[0]

                    if _cls != None and _cls in class_str:
                        return l

            breakpoint()
            loc = loc_out
    # --- end search for button

    # search by link ---
    if conv_node_name == "link":
        if inner_text != "":
            text = inner_text
        elif "aria-label" in node_meta:
            text = node_meta["aria-label"][0]
        else:
            breakpoint()

        loc_out = loc.get_by_role("link", name=text)
        if len(loc_out.all()) == 1:
            return loc_out.first
        elif len(loc_out.all()) == 0:
            print("reverting back to old loc - link")
            loc_out = loc
        else:
            for l in loc_out.all():
                _cls = l.get_attribute("class")
                if " " in _cls:
                    _cls = _cls.split(" ", 1)[0]

                if _cls != None and _cls in class_str:
                    return l
    if element_buffer["node_index"] == "304":
        breakpoint()
    breakpoint()
    # this is trying to get by class, but class can be a lot of locators so in that case try and use inner_text
    # class_strings = _combine_class_names(node_meta)
    # if class_strings != None:
    #     loc_tmp = loc.locator(class_strings)
    #     txt = inner_text or node_value
    #     if len(loc_tmp.all()) > 1:
    #         loc_tmp = loc_tmp.filter(has_text=txt)
    #     return loc_tmp.first

    # for meta in node_meta:
    #     if "title=" in meta:
    #         loc_out = _get_by_title(meta, loc)
    #         loc = status(loc_out)
    #         if status.s == "done":
    #             loc = loc.all()
    #             if len(loc) != 1:
    #                 breakpoint()
    #             return loc[0]
    #     if "class=" in meta:
    #         c_str = _combine_class_names()

    # if node_name == "a":
    #     loc = page.get_by_role().all()


def _from_class_name(self, element, element_buffer, page):
    class_name = _combine_class_names(element_buffer["node_meta"])
    locator = page.query_selector_all(class_name)
    return locator


def element_to_locator(self, element: str, element_buffer: dict, page: Page):
    node_meta = element_buffer["node_meta"]
    class_name = _combine_class_names(node_meta)

    print("parsing element...", element)
    el_type, el_id, el_meta = element.split(" ", 2)
    if _check_if_only_text(el_meta):
        text = _clean_str_quotes(el_meta)
        locator = page.get_by_text(text).all()
        if len(locator) > 1:
            breakpoint()

        return locator[0]

    # roles, el_meta_rest = _get_role_info(el_meta)
    tags, el_meta_rest = _get_kw_info(el_meta)
    el_meta_rest = _clean_str_quotes(el_meta_rest)

    loc = page
    for tag_name, tag_value in tags:
        if tag_name == "role":
            loc = loc.get_by_role(tag_value, name=el_meta_rest)
            if len(loc.all()) == 1:
                return loc.all()[0]

        if tag_name == "title":
            loc = loc.get_by_title(tag_value, name=el_meta_rest)
            if len(loc.all()) == 1:
                return loc.all()[0]

    # if we just have roles
    # if (len(el_meta_rest) > 0) and _check_if_only_text(el_meta_rest):
    #     text = _clean_str_quotes(el_meta_rest)
    #     locator = page.get_by(text).all()
    #     if len(locator) > 1:
    #         breakpoint()

    #     return locator[0]

    breakpoint()


def eoi_to_locator(self, eoi: str, page: Page) -> Locator:
    el_type, el_id, el_meta = eoi.split(" ", 2)

    # try to match by text first
    if el_meta.startswith('"') or el_meta.startswith("'"):
        if el_meta.startswith("'"):  # think im confused if i get this type of ' rather than "
            breakpoint()
        el_meta = el_meta.lstrip('"').rstrip('"')
        locator = page.get_by_text(el_meta).all()

        if len(locator) != 1:
            for loc in locator:
                inner_text = loc.inner_text()
                if inner_text == el_meta:
                    return loc

        locator = locator[0]
        return locator

    # here we try to match by aria-label/label or class
    pattern = r'(.*?)="(.*?)"'
    match = re.findall(pattern, el_meta)

    for attr, value in match:
        label = attr.lstrip(" ")
        if "aria" in label:
            locator = page.get_by_label(value).all()
            if len(locator) != 1:
                # breakpoint()
                continue
            return locator[0]

    for attr, value in match:
        if "class" in attr:
            if len(value.split(" ")) > 1:
                value = value.replace(" ", ",.")
            locator = page.locator(f".{value}").all()
            if len(locator) != 1:
                print("ERROR WE ARE GETTING TOO MANY LOCATORS")
            return locator[0]

    for attr, value in match:
        if "role" in attr:
            _text = el_meta.replace(f'{attr}="{value}"', "").strip()
            if _text[0] == '"':
                _text = _text.lstrip('"').rstrip('"')

            # locator = page.get_by_role(_text).first
            locator = page.get_by_text(_text).first
            return locator

    # here we try to match by class only but may have multiple classes
    class_selector = ""
    split_class_names = el_meta.split(" ")
    for idx, class_name in enumerate(split_class_names):
        class_selector += "." + class_name

        try:
            locator = page.locator(class_selector).all()
        except:
            print("HUGE ERROR WITH EOI!!!")
            print(eoi)
            print(class_selector)
            return None

        if len(locator) == 1:
            return locator[0]

        if idx != len(split_class_names) - 1:
            class_selector += ","

    return None


async def eoi_to_locator_async(self, eoi: str | List[str], page: Page) -> Locator:
    # WARNING: this might be a terrible idea lol
    # if isinstance(eoi, list):
    #     return [await self.eoi_to_locator(e, page) for e in eoi]
    try:
        el_type, el_id, el_meta = eoi.split(" ", 2)

        # try to match by text first
        if el_meta.startswith('"') or el_meta.startswith("'"):
            if el_meta.startswith("'"):  # think im confused if i get this type of ' rather than "
                breakpoint()
            el_meta = el_meta.lstrip('"').rstrip('"')
            locator = await page.get_by_text(el_meta).all()

            if len(locator) != 1:
                for loc in locator:
                    inner_text = await loc.inner_text()
                    if inner_text == el_meta:
                        return loc

            locator = locator[0]
            return locator

        # here we try to match by aria-label/label or class
        pattern = r'(.*?)="(.*?)"'
        match = re.findall(pattern, el_meta)

        for attr, value in match:
            label = attr.lstrip(" ")
            if "aria" in label:
                locator = await page.get_by_label(value).all()
                if len(locator) != 1:
                    # breakpoint()
                    continue
                return locator[0]

        for attr, value in match:
            if "class" in attr:
                if len(value.split(" ")) > 1:
                    value = value.replace(" ", ",.")
                locator = await page.locator(f".{value}").all()
                if len(locator) != 1:
                    print("ERROR WE ARE GETTING TOO MANY LOCATORS")
                return locator[0]

        for attr, value in match:
            if "role" in attr:
                _text = el_meta.replace(f'{attr}="{value}"', "").strip()
                if _text[0] == '"':
                    _text = _text.lstrip('"').rstrip('"')

                # locator = await page.get_by_role(_text).first
                locator = page.get_by_text(_text).first
                return locator

        # here we try to match by class only but may have multiple classes
        class_selector = ""
        split_class_names = el_meta.split(" ")
        for idx, class_name in enumerate(split_class_names):
            class_selector += "." + class_name

            try:
                locator = await page.locator(class_selector).all()
            except:
                print("HUGE ERROR WITH EOI!!!")
                print(eoi)
                print(class_selector)
                return None

            if len(locator) == 1:
                return locator[0]

            if idx != len(split_class_names) - 1:
                class_selector += ","
    except:
        return None

    print("UNABLE TO FIND LOCATOR FOR ", eoi)
    return None
