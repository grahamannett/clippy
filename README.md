# clippy

Web Agent + Data Labeler for Web Trajectory Research Project

The web app is being migrated/refactored to new repo:
  - [web-agent-collection-offline-dataset](https://github.com/grahamannett/web-agent-collection-offline-dataset)

The web crawler/agent is being migrated/refactored to a new repo as well but will eventually use this repo name.  Doing this to separate the web agent from the data labeling tool as there are two distinct use cases and the web app should be useable without the web agent integration.

## To Run

These keys must be set to run:
- OPENAI_API_KEY
- COHERE_KEY
- QDRANT_KEY
- KEEP_DEVICE_RATIO=0
    - necessary if you are using a mbp with non-retina screen

Then to run the program:

```bash
❯ python -m clippy --help                                                                                                                                   ─╯
usage: __main__.py [-h] [--objective str] [--seed int] [--headless bool] [--exec_type {sync,async}] [--start_page str] [--task_gen_from {llm,taskbank}]
                   [--key_exit bool] [--confirm_actions bool] [--task_id int|str]
                   {assist,capture,replay,datamanager} ...

options:
  -h, --help            show this help message and exit

ClippyArgs ['clippy_args']:
  class docstring

  --objective str       (default: Enter an objective: )
  --seed int
  --headless bool, --noheadless bool
                        should run without a browser window (default: False)
  --exec_type {sync,async}
                        should run in async or sync mode (default: async)
  --start_page str      (default: https://www.google.com)
  --task_gen_from {llm,taskbank}
                        generate random task from task/word bank (default: taskbank)
  --key_exit bool, --nokey_exit bool
                        should exit on key press (default: True)
  --confirm_actions bool, --noconfirm_actions bool
                        (default: False)
  --task_id int|str

command:
  {assist,capture,replay,datamanager}
```

For instance to run a local capture with random task generated from LLM with LLM suggestion on each page:

```bash
❯ python -m clippy --task_id=random --task_gen_from=llm capture --llm True
[22:41:06] Warning: USING SYNC LLM Client                                                                                              cohere_controller.py:64
           Info: Sampled TASK from                                                                                                          clippy_base.py:188
           TASK: When was The Picture of Dorian Gray published?
           Info: check if clear current                                                                                                     data_manager.py:79
           Info: should clear current dir                                                                                                   data_manager.py:81
           Info: crawler start...                                                                                                         capture_async.py:132
[22:41:07] Info: starting tracer...
```

# main app:
- src/clippy

# trajectory labeler:
- src/trajlab

To setup the labeler you need to symlink the data folder to the assets:

`ln -s /Users/graham/code/clippy/data /Users/graham/code/clippy/src/trajlab/assets/data`

# Example of Manual Data Labeling:

https://github.com/grahamannett/clippy/assets/7343667/5c904fb5-1fd8-43fa-9085-63e08271a993

# Outline Of Initial Proposed System

![clippy-outline](https://github.com/grahamannett/clippy/assets/7343667/f10c9a51-6158-4cee-9bf2-c2696003b6b3)

<!-- # old executor/regression test
https://gist.github.com/grahamannett/8f4194883dd13f4ccfcc1baf0975eb10
 -->

# Templating Notes:
For some of the templates where there are conditionals, I have the space with the "None" option rather than with the preceding and this might not be obvious if tests fail from string comparison. For instance with the following:

```jinja
Previous actions:{% if previous_commands %}{% for cmd in previous_commands %}
{{ action_prefix }}{{ cmd }}{% endfor %}{% else %} None{% endif %}
```
it is ` None` rather than `Previous actions: `.  Keep this formatting unless there is a good reason to switch away from it as it makes regression/testing more obvious.
