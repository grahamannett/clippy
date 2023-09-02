MILLI_SECOND = 1000


# defaults injection script location
# TODO: would be nice if i dont need to use the src/ prefix
default_preload_injection_script = "src/clippy/crawler/inject/preload.js"
default_empty_injection_script = "src/clippy/crawler/inject/empty.js"

TEMPLATES_DIR = "src/clippy/templates/"

# clippy defaults
default_start_page: str = "https://www.google.com"
default_objective: str = "Enter an objective: "


max_url_length = 100  # if None will print whole
