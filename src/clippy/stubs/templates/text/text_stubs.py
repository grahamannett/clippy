# NOTE: This was from before i switched to jinja
# jinja seems to be a better fit for this project as it is more flexible and allows conditionals

from string import Template as TemplateBase
from typing import List, Dict


class Template(TemplateBase):
    """This Template is mostly just the default string.Template but also aimed at same functionality as mako.Template"""

    filename: str = None
    template: str = None

    def __init__(self, template: str = None, filename: str = None) -> None:
        if self.filename is not None:
            filename = self.filename
        if self.template is not None:
            template = self.template

        if filename is not None:
            with open(filename, "r") as f:
                template = f.read()

        super().__init__(template)
        self.identifiers = self.get_identifiers()
        self.optional_identifiers = self.get_optional_identifiers()

    def __call__(self, **kwargs) -> str:
        # replace the ids that are prepended with optional
        for opt_id, opt_val in self.optional_identifiers.items():
            if opt_id in kwargs:
                kwargs[f"optional_{opt_id}"] = kwargs[opt_id]
            else:
                kwargs[f"optional_{opt_id}"] = ""
        return super().substitute(**kwargs)

    def apply(self, options: List[Dict[str, str]], **kwargs) -> List[str]:
        return [self.__call__(**{**opt, **kwargs}) for opt in options]

    def compose(self, **kwargs) -> "Template":
        """compose a template within a template...
        I think there is a better name for this and should look how mako does it"""
        return Template(template=super().substitute(**kwargs))

    def render(self, **kwargs) -> str:
        return super().substitute(**kwargs)

    def get_identifiers(self):
        if hasattr(TemplateBase, "get_identifiers"):
            # breakpoint()
            # raise FutureWarning("This function is not needed anymore")
            return TemplateBase(self.template).get_identifiers()
        # this is in python 3.11 but not 3.10 which i have b/c of torch
        ids = []
        for mo in self.pattern.finditer(self.template):
            named = mo.group("named") or mo.group("braced")
            if named is not None and named not in ids:
                # add a named group only the first time it appears
                ids.append(named)
            elif named is None and mo.group("invalid") is None and mo.group("escaped") is None:
                # If all the groups are None, there must be
                # another group we're not expecting
                raise ValueError("Unrecognized named group in pattern", self.pattern)
        return ids

    def get_optional_identifiers(self):
        optional_identifiers = {}

        for identifier in self.identifiers:
            if identifier.startswith("optional_"):
                split_id = identifier.split("optional_")[1]
                optional_identifiers[split_id] = ""

        return optional_identifiers


def _setup_templates(cls_: "StubTemplates"):
    """this is a decorator that will add all the templates in the templates folder to the class as attributes
    its a wrapper because it looks cooler than calling a function in class definition
    """
    from pathlib import Path

    # template_files = glob.rglob("**/*.template")
    template_files = list(Path().rglob("**/*.template"))

    for file in template_files:
        name = Path(file).stem
        template = Template(filename=file)
        setattr(cls_, name, template)

    return cls_


@_setup_templates
class StubTemplates:
    factory = Template
