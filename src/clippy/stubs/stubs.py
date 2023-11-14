from os import environ
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
    examples_prompt = StubHelper.get_template("examples_prompt.jinja")
    state = StubHelper.get_template("state.jinja")
    transform_generation = StubHelper.get_template("transform_generation.jinja")

    # prompt is main template
    prompt = StubHelper.get_template("prompt.jinja")
    # headers for prompt
    header_next_action = StubHelper.get_template("header_next_action.jinja")
    header_filter_elements = StubHelper.get_template("header_filter_elements.jinja")

    # task gen
    task_gen = StubHelper.get_template("task_gen/task_gen.jinja")
    task_gen_json = StubHelper.get_template("task_gen/task_gen_json.jinja")
