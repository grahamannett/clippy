import asyncio
from functools import wraps
from typing import Callable, Union


class Callback:
    _instance = None
    callbacks = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Callback, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, func: Callable) -> Union[Callable, Callable]:
        """
        Decorator that registers the function and adds callbacks to it.
        """
        func_key = f"{func.__module__}.{func.__qualname__}"

        if func_key not in cls.callbacks:
            cls.callbacks[func_key] = []

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Call the function itself
            result = await func(*args, **kwargs)
            # Call the callbacks after the function
            await cls._invoke(func_key, *args, **kwargs)
            return result

        return async_wrapper

    @classmethod
    async def _invoke(self, func_key, *args, **kwargs):
        """
        Private method to invoke all callbacks for a given function key.
        """
        if func_key in self.callbacks:
            for callback in self.callbacks[func_key]:
                if asyncio.iscoroutine(resp := callback(*args, **kwargs)):
                    await resp

    def add_callback(self, on: Callable, callback: Callable) -> None:
        """
        Method to add a callback to a function.
        """
        func_key = f"{on.__module__}.{on.__qualname__}"
        if func_key not in self.callbacks:
            self.callbacks[func_key] = []
        self.callbacks[func_key].append(callback)
