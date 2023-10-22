import unittest

from clippy.instructor import Instructor, match_generated_output


class TestInstructor(unittest.IsolatedAsyncioTestCase):
    def test_suggest_from_fixture(self):
        pass

    def test_match_element(self):
        output = match_generated_output("obj3", ["obj1", "obj2", "obj3", "obj4"])
        assert output == 2
