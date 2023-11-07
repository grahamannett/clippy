import asyncio

from clippy.run import setup_run


if __name__ == "__main__":
    clippy, run_kwargs = setup_run()
    asyncio.run(clippy.run(run_kwargs))
