from typing import List

def argmax(vals: List[float]) -> int:
    arg_max, maximum = max(list(enumerate(vals)), key=lambda x: x[1])
    return arg_max