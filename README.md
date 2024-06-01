# clippy layout


# main app:
src/clippy

# trajectory labeler:

src/trajlab

To setup the labeler you need to symlink the data folder to the assets:

`ln -s /Users/graham/code/clippy/data /Users/graham/code/clippy/src/trajlab/assets/data`

## How to use:

https://github.com/grahamannett/clippy/assets/7343667/5c904fb5-1fd8-43fa-9085-63e08271a993

# Outline Of Proposed System

![clippy-outline](https://github.com/grahamannett/clippy/assets/7343667/f10c9a51-6158-4cee-9bf2-c2696003b6b3)

# old executor/regression test
https://gist.github.com/grahamannett/8f4194883dd13f4ccfcc1baf0975eb10


# Templating Notes:
For some of the templates where there are conditionals, I have the space with the "None" option rather than with the preceding and this might not be obvious if tests fail from string comparison.  for instance with the following:

```jinja
Previous actions:{% if previous_commands %}{% for cmd in previous_commands %}
{{ action_prefix }}{{ cmd }}{% endfor %}{% else %} None{% endif %}
```

it is ` None` rather than `Previous actions: `.  Keep this formatting unless there is a good reason to switch away from it as it makes regression/testing more obvious.
