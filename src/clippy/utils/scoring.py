from typing import Any, List, Tuple


def best_score(scores: List[any], key=lambda x: x[1]["score"]) -> Tuple[int, Any]:
    # key should be like x[1]["score"] or x[1] since using enum
    arg_max, maximum = max(list(enumerate(scores)), key=key)
    return arg_max, maximum
