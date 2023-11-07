import os

MILLI_SECOND = 1000

ROOT_DIR = os.environ.get("CLIPPY_ROOT_DIR", "/Users/graham/code/clippy")
# defaults injection script location
# TODO: would be nice if i dont need to use the src/ prefix
default_preload_injection_script = f"{ROOT_DIR}/src/clippy/crawler/inject/preload.js"
default_empty_injection_script = f"{ROOT_DIR}/src/clippy/crawler/inject/empty.js"


# clippy defaults
default_start_page: str = "https://www.google.com"
default_objective: str = "Enter an objective: "


max_url_length = 100  # if None will print whole


# browser related
default_user_agent = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    + "AppleWebKit/537.36 (KHTML, like Gecko) "
    + "Chrome/105.0.0.0 Safari/537.36"
)
default_viewport_size = {"width": 1280, "height": 1080}

# input delay is delay betweeen each keypress/click.  ideally this should be more `random`
input_delay = 100  # ms
# action delay is the delay after executing an action to the next thing we do.
# for instance if we click a button and the page then shows a new modal that we input
#  into but url does not change ideally this should be more `random`
action_delay = 1  # seconds


# TASK BANK RELATED
TEMPLATES_DIR = f"{ROOT_DIR}/src/clippy/templates/"

TASK_BANK_DIR = f"{ROOT_DIR}/src/taskgen/wordbank"

# DATABASE RELATED
MIGRATION_DIR = f"{ROOT_DIR}/data/migrate"
TASKS_DATA_DIR = f"{ROOT_DIR}/data/tasks"
