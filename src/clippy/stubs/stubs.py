from os import environ
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, Template

from clippy import constants


def map(self, options: List[Dict[str, str]], **kwargs) -> List[str]:
    return [self.render(**{**opt, **kwargs}) for opt in options]


def __call__(self, *args: Any, **kwds: Any) -> Any:
    return self.render(*args, **kwds)


# patch this class to be more useful
Template.map = map
Template.__call__ = __call__


class StubHelper:
    environment = Environment(loader=FileSystemLoader(environ.get("TEMPLATES_DIR", constants.TEMPLATES_DIR)))

    def map(self, template: Template, options: List[Dict[str, str]], **kwargs) -> List[str]:
        return [template(**{**opt, **kwargs}) for opt in options]

    @classmethod
    def get_template(cls, template_name: str) -> Template:
        return cls.environment.get_template(template_name)

    @staticmethod
    def template(text: str) -> Template:
        return Template(text)


class StubTemplates:
    Template = Template

    @classmethod
    def setup_template(cls, template_path: str, template_name: str = None):
        # alternative is to use
        # template_name = StubHelper.get_template(template_path)
        # e.g.
        # `state = StubHelper.get_template("state.jinja")`
        template_name = template_name or Path(template_path).stem
        setattr(cls, template_name, StubHelper.get_template(template_path))


StubTemplates.setup_template("examples_prompt.jinja")
StubTemplates.setup_template("state.jinja")
StubTemplates.setup_template("transform_generation.jinja")

# prompt is main template
StubTemplates.setup_template("prompt.jinja")
# headers for prompt
StubTemplates.setup_template("header_next_action.jinja")
StubTemplates.setup_template("header_filter_elements.jinja")

# task gen
StubTemplates.setup_template("task_gen/task_gen_json.jinja")
StubTemplates.setup_template("task_gen/task_gen.jinja")
