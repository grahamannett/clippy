from clippy.crawler.parser.dom_parser_text import _clean_str_quotes
from typing import Tuple, List, Dict


def _get_args_kwargs_from_string(string: str) -> Tuple[List[str], Dict[str, str]]:
    if string == "":
        return [], {}
    args, kwargs = [], {}
    segments = string.split(", ")
    for segment in segments:
        # what?
        if segment[0] == " ":
            segment = segment[1:]

        if "=" in segment:
            key_word, value = segment.split("=", 1)
            value = _clean_str_quotes(value)
            kwargs[key_word] = value
        else:
            args.append(_clean_str_quotes(segment))
    return args, kwargs


def _parse_segment(segment: str) -> Tuple[str, List[str], Dict[str, str]]:
    """
    type is the callable name, then if there are args/kwargs they are parsed and returned
    if no args/kwargs, then its not a callable just a attr/property

    NOTE: This parses strings/segments sent over from the playwright js injection that gets generated on the js/browser side
    We need to parse these strings to get the callable name, args, and kwargs
    """
    fns = []
    segments = segment.split(").")

    # def _parse_segment(segment: str) -> Tuple[str, List[str], Dict[str, str]]:
    #     pass

    for seg in segments:
        if "(" not in seg:
            fns.append((seg,))
            continue
        func_name, string = seg.split("(", 1)
        if "." in func_name:
            print("ERROR WE HAVE AN ATTR/PROPERTY BEFORE A CALL. NEED TO HANDLE THIS")
            breakpoint()
        string = string.rstrip(")")
        str_args, str_keywords = _get_args_kwargs_from_string(string)
        fns.append((func_name, str_args, str_keywords))
    return fns


def _make_segment_eval(segment: str):
    segment_val = f"action = page.{segment}"
    return segment_val
