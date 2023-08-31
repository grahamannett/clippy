from typing import Any


def _print_console(*args, print_fn: callable = print):
    # args = [repr(str(a)) for a in args]
    args = [a if (len(a) < 20) else f"{a[:20]}..." for a in args]
    print_fn(f"=>{str(args)}")


def _otherloaded(name: str, logger: Any):
    """helper func for attaching to page events"""

    async def _fn(*args, **kwargs):
        logger.info(f"{name} event")

    return _fn
