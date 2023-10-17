import subprocess

import os

# console module


class console:
    @staticmethod
    def log(msg, **kwargs):
        ...


def new_process(args, run: bool = False, show_logs: bool = False, **kwargs):
    """Wrapper over subprocess.Popen to unify the launch of child processes.

    Args:
        args: A string, or a sequence of program arguments.
        run: Whether to run the process to completion.
        show_logs: Whether to show the logs of the process.
        **kwargs: Kwargs to override default wrap values to pass to subprocess.Popen as arguments.

    Returns:
        Execute a child program in a new process.
    """
    node_bin_path = path_ops.get_node_bin_path()
    if not node_bin_path:
        console.warn(
            "The path to the Node binary could not be found. Please ensure that Node is properly "
            "installed and added to your system's PATH environment variable."
        )
    # Add the node bin path to the PATH environment variable.
    env = {
        **os.environ,
        "PATH": os.pathsep.join([node_bin_path if node_bin_path else "", os.environ["PATH"]]),  # type: ignore
        **kwargs.pop("env", {}),
    }
    kwargs = {
        "env": env,
        "stderr": None if show_logs else subprocess.STDOUT,
        "stdout": None if show_logs else subprocess.PIPE,
        "universal_newlines": True,
        "encoding": "UTF-8",
        **kwargs,
    }
    console.debug(f"Running command: {args}")
    fn = subprocess.run if run else subprocess.Popen
    return fn(args, **kwargs)
