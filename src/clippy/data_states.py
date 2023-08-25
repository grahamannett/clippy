from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


from clippy.constants import default_start_page, default_objective


class HandleUserFeedback:
    def __init__(
        self,
        initial_prompt: str,
        default_feedback: str,
        error_prompt: str,
        response_callback: Callable,
        after_feedback: Callable = None,
    ):
        self.initial_prompt = initial_prompt
        self.default_feedback = default_feedback
        self.error_prompt = error_prompt
        self.response_callback = response_callback

        self.after_feedback = after_feedback

        self.entry_override: callable = None
        self.patch_input = None

    def __call__(self, *args, **kwargs) -> str:
        _fn = self._entry if self.entry_override is None else self.entry_override
        return _fn(*args, **kwargs)

    def _input(self, prompt: str):
        if self.patch_input is not None:
            print(f"DEBUG={prompt}")
            return self.patch_input

        return input(prompt)

    def _entry(self, *args, **kwargs) -> str:
        def _check_response(_feedback: str) -> str:
            while not self.response_callback(_feedback):
                _feedback = input(self.error_prompt)
                print("checking feedback", _feedback)
            return _feedback

        feedback = input(self.initial_prompt)
        if feedback == "y":
            feedback = self.default_feedback

        return _check_response(feedback)

    def _make_check_response(self, feedback: str) -> Callable:
        def _check_response(feedback: str) -> str:
            while not self.response_callback(feedback):
                feedback = input(self.error_prompt)
            return feedback

        return _check_response(feedback)

    # def _make_entry(self, ):
    #     _check_response = self._make_check_response(self.)

    def make_feedback_fn(self) -> Callable:
        def _fn(state):
            user_resp = self.__call__(state)
            if isinstance(user_resp, str):
                user_resp = [user_resp]

            for el in user_resp:
                state.response.cmd.append(el)

        return _fn


class Response:
    def __init__(self, next_steps: Dict[str, Callable] = None, metadata: dict = None) -> None:
        self.next_steps = next_steps
        self.metadata = metadata

    def get_next(self):
        return self.next_steps["next_step"]

    def get_input(self, prompt: str) -> str:
        return input(prompt)

    @classmethod
    def from_feedback_handler(
        cls, feedback_handler: HandleUserFeedback, pre_step: Callable = None, post_step: Callable = None
    ) -> "Response":
        next_steps = {
            "pre_step": pre_step,
            "next_step": feedback_handler.after_feedback,
            "post_step": post_step,
        }

        response = cls(feedback_fn=feedback_handler.make_feedback_fn(), next_steps=next_steps)
        return response


class ControllerResponse(Response):
    # this means the controller (LM) has looked at the state and needs feedback
    def __init__(self, feedback_fn: Callable = None, cmd: List[str] = [], **kwargs) -> None:
        super().__init__(**kwargs)
        self.feedback_fn = feedback_fn
        self.cmd = cmd


class CommandResponse(Response):
    # this means instructor has looked at everything nad ready to do command
    def __init__(self, cmd: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cmd = cmd


