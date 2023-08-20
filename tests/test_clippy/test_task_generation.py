import unittest


from clippy.dm.task_bank import TaskBankManager


class TestTestBank(unittest.TestCase):
    def test_examples(self):
        tbm = TaskBankManager()
        tbm.process_task_bank()
        self.assertTrue(len(tbm) > 5)

        task = tbm.sample_task()
