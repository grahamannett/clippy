import pytest

from clippy.controllers.utils import find_json_response


@pytest.mark.parametrize(
    "input_string,expected",
    [
        (
            'This message is truncated: {"items":[{"key1": [123]',
            '{"items":[{"key1": [123]',
        ),
        (
            'This message is truncated: {"items":[{"key1": [123',
            '{"items":[{"key1": [123',
        ),
        (
            'This message is truncated: {"items":[{"key1": "abc"',
            '{"items":[{"key1": "abc"',
        ),
        (
            'This message is truncated: {"key": "value", "list": [1, 2, 3',
            '{"key": "value", "list": [1, 2, 3',
        ),
        (
            'This message is truncated: {"text": "Test", "numerical": 123, "reason": true, "sub_element": { "name": "Test" }, "items": ["Item 1", "Item 2',
            '{"text": "Test", "numerical": 123, "reason": true, "sub_element": { "name": "Test" }, "items": ["Item 1", "Item 2',
        ),
    ],
)
def test_find_json_response(input_string, expected):
    assert find_json_response(input_string) == expected
