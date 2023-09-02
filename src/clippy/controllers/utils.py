from typing import Any, Union, TypeVar
from re import DOTALL, finditer
from typing import Callable

from clippy.controllers.controller_config import ResponseConfig


Response = TypeVar("Response")


def allow_full_response(default_value_func: Callable) -> Callable:
    """
    Decorator to allow full response from controller APIs.

    Args:
        default_value_func (Callable): The default value function to be used if ResponseConfig.return_raw is False.

    Returns:
        Callable: The decorated function.


    Example:
    --------
    @allow_full_response(default_value_func=lambda x: x.json())
    async def get_data():
        response = requests.get('https://api.example.com/data')
        return response

    In the above example, the decorator `allow_full_response` is used to wrap the function `get_data`.
    If `ResponseConfig.return_raw` is `True`, the raw response from the API call is returned.
    If `ResponseConfig.return_raw` is `False`, the `default_value_func` is called with the API response as its argument.
    In this case, the `default_value_func` is `lambda x: x.json()`, so it returns the JSON content of the response.


    """

    def decorator(func: Callable) -> Callable:
        """
        The actual decorator function.

        Args:
            func (Callable): The function to be decorated.

        Returns:
            Callable: The decorated function.
        """

        async def wrapper(*args, **kwargs) -> Union[Response, Any]:
            """
            The wrapper function that will be called instead of the decorated function.

            Args:
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                The response from the API or the result of the default value function.
            """
            resp = await func(*args, **kwargs)
            if ResponseConfig.return_raw:
                return resp
            return default_value_func(resp)

        return wrapper

    return decorator


def truncate_left(tokenize: Callable, prompt: str, *rest_of_prompt, limit: int = 2048):
    i = 0
    chop_size = 5
    print(f"WARNING: truncating sequence of length {len(tokenize(prompt + ''.join(rest_of_prompt)))} to length {limit}")
    while len(tokenize(prompt + "".join(rest_of_prompt))) > limit:
        prompt = prompt[i * chop_size :]
        i += 1
    return prompt


def find_json_response(full_response, extract_type: type = dict):
    """
    Takes a full response that might contain other strings and attempts to extract the JSON payload.
    Has support for truncated JSON where the JSON begins but the token window ends before the json is
    is properly closed.

    https://github.com/piercefreeman/gpt-json/blob/main/gpt_json/parsers.py

    """
    # Deal with fully included responses as well as truncated responses that only have one
    if extract_type != dict:
        raise ValueError("Unknown extract_type")
    extracted_responses = list(finditer(r"({[^}]*$|{.*})", full_response, flags=DOTALL))

    if not extracted_responses:
        print(f"Unable to find any responses of the matching type `{extract_type}`: `{full_response}`")
        return None

    if len(extracted_responses) > 1:
        print("Unexpected response > 1, continuing anyway...", extracted_responses)

    extracted_response = extracted_responses[0]

    if is_truncated(extracted_response.group(0)):
        # Start at the same location and just expand to the end of the message
        extracted_str = full_response[extracted_response.start() :]
    else:
        extracted_str = extracted_response.group(0)

    return extracted_str


def is_truncated(json_str: str):
    """
    Check if the json string is truncated by checking if the number of opening
    brackets is greater than the number of closing brackets.

    """
    stack, _, _, _ = build_stack(json_str)
    return len(stack) > 0


def build_stack(json_str: str):
    stack = []
    fixed_str = ""
    open_quotes = False

    # a flag indicating whether we've seen a comma or colon most recently
    # since last opening/closing a dict or list
    last_seen_comma_or_colon = None

    for i, char in enumerate(json_str):
        if not open_quotes:
            # opening a new nested
            if char in "{[":
                stack.append(char)
                last_seen_comma_or_colon = None
            # closing a nested
            elif char in "}]":
                stack.pop()
                last_seen_comma_or_colon = None
            if char in ",:":
                last_seen_comma_or_colon = char
        # opening or closing a string, only it's not escaped
        if char == '"' and i > 0 and json_str[i - 1] != "\\":
            open_quotes = not open_quotes

        fixed_str += char

    return (stack, fixed_str, open_quotes, last_seen_comma_or_colon)
