from os import environ

from typing import Any, Dict, List
from jinja2 import Environment, FileSystemLoader, Template


def map(self, options: List[Dict[str, str]], **kwargs) -> List[str]:
    return [self.render(**{**opt, **kwargs}) for opt in options]


def __call__(self, *args: Any, **kwds: Any) -> Any:
    return self.render(*args, **kwds)


# monkey patch
Template.map = map
Template.__call__ = __call__


# environment = Environment(loader=FileSystemLoader(environ.get("TEMPLATES_DIR", "clippy/stubs/templates/")))


class StubHelper:
    available_templates = {}
    environment = Environment(loader=FileSystemLoader(environ.get("TEMPLATES_DIR", "clippy/stubs/templates/")))

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
    prompt = StubHelper.get_template("prompt.jinja")
    examples_prompt = StubHelper.get_template("examples_prompt.jinja")
    message = StubHelper.get_template("message.jinja")
    state = StubHelper.get_template("state.jinja")


if __name__ == "__main__":
    prompt = StubTemplates.prompt
    print(prompt.render())
    print("prompt done!! !! !!!")
    print(prompt())
