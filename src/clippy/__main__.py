import asyncio

from clippy.run import setup_run

def main():
    clippy, run_kwargs = setup_run()
    asyncio.run(clippy.run(run_kwargs))


if __name__ == "__main__":
    main()