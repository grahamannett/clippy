from dataclasses import dataclass, field, is_dataclass, asdict
from typing import Any, List, Optional
import json


@dataclass
class StateSchema:
    objective: str
    url: str


@dataclass
class ActionSchema:
    type: str
    id: str
    args: Optional[str] = field(default=None)


@dataclass
class GenerateActionSchema:
    state: StateSchema
    previous_actions: Optional[List[ActionSchema]]
    browser_content: Optional[List[ActionSchema]]
    next_action: Any = "NEXT_ACTION_PLACEHOLDER"


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)

    @classmethod
    def dumps(cls, o):
        return json.dumps(o, cls=cls, indent=2)


# json.dumps(foo, cls=EnhancedJSONEncoder)
