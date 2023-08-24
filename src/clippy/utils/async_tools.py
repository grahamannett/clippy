from typing import Callable, Coroutine
from functools import wraps, partial
import asyncio

import time


use_async = False


def run_async_func(func: Coroutine):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(func)


def allow_async(func):
    if not use_async:
        return func

    @wraps(func)  # Makes sure that function is returned for e.g. func.__name__ etc.
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()  # Make event loop of nothing exists
        pfunc = partial(func, *args, **kwargs)  # Return function with variables (event) filled in
        return await loop.run_in_executor(executor, pfunc)

    return run


def from_async(func):
    # I feel like you want this to be an async def run so you can await  any of the func
    # but then you need to call use it within loop.run_until_complete? im not sure
    @wraps(func)
    def run(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))

    return run


# I dont even know if i do need to seperate these out but i think i might want other specs for async functions
def timer(func: Callable):
    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            print(f"{func.__name__} took {time.time() - start} seconds")
            return result

        return wrapper
    else:

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            print(f"{func.__name__} took {time.time() - start} seconds")
            return result

        return wrapper


def _allow_nested_loop(self):
    import nest_asyncio

    nest_asyncio.apply()
