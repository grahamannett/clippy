from random import randint

from clippy.constants import input_delay


def _get_input(string: str = None) -> str:
    return input(string)


def _random_delay(rand_range: tuple[int, int] = (-50, 50), mean: int = input_delay) -> int:
    return abs(mean + randint(*rand_range))
