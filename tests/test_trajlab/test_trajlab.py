from pathlib import Path
import pytest

from reflex.testing import AppHarness


@pytest.fixture()
def trajlab_app():
    with AppHarness.create(root=Path("/Users/graham/code/clippy/src/trajlab")) as harness:
        yield harness


def test_counter_app(trajlab_app: AppHarness):
    driver = trajlab_app.frontend()
    state_manager = trajlab_app.app_instance.state_manager
