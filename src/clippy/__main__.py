import asyncio

from clippy.run import run


if __name__ == "__main__":
    clippy, args = run()
    asyncio.run(clippy.run(args=args))
