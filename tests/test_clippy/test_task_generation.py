import unittest


from clippy.dm.task_bank import TaskBankManager, Words, _process_word_bank


class TestTaskBank(unittest.TestCase):
    def test_words(self):
        word_bank_file = "src/taskgen/wordbank/city_bank"
        words = _process_word_bank(word_bank_file)
        assert len(words) != 0

        words = Words.from_file(word_bank_file)
        assert len(words) != 0
        word = words.sample()
        assert word != ""

    def test_wordbank(self):
        tbm = TaskBankManager()
        tbm.process_task_bank()

        value = tbm.wordbank.timeslot

    def test_examples(self):
        tbm = TaskBankManager()
        tbm.process_task_bank()

        self.assertTrue(len(tbm) > 5)

        task = tbm.sample()
        assert task != ""

        for i, task in enumerate(tbm):
            assert task != ""

            if i > 50:
                break
