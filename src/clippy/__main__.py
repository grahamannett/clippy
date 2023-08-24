import asyncio

from clippy.run import run


if __name__ == "__main__":
    clippy = run()
    asyncio.run(clippy.run_capture(use_llm=False))
