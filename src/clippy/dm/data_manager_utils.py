from loguru import logger
from clippy.utils.input_utils import _get_input



def confirm_override(func):
    def wrapper(*args, **kwargs):
        if kwargs.get("override", False):
            logger.info("override set, skipping confirm")
            return func(*args, **kwargs)

        confirm_input = _get_input(f"confirm action for {func.__name__}. Press c/y to confirm or n to skip: ")

        if confirm_input.lower() in ["n", "no"]:
            logger.info(f"skipping... {func.__name__}")
            return
        elif confirm_input.lower() not in ["c", "y"]:
            # allow breakpoint for debugger to inspect
            breakpoint()
        return func(*args, **kwargs)

    return wrapper
