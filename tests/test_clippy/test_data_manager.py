import unittest
import os
import shutil
from clippy.dm.data_manager import DataManager, Task


class TestDataManger(unittest.TestCase):
    def setUp(self):
        self.data_manager = DataManager("data/tasks")
        self.task = Task(
            objective="Test objective",
            steps=["Step 1", "Step 2"],
            notes="Test notes",
        )

    def tearDown(self):
        shutil.rmtree("data/migrate")
        shutil.rmtree("data/tasks")

    def test_load(self):
        os.makedirs("data/tasks/task1")
        with open("data/tasks/task1/task.json", "w") as f:
            f.write(self.task.dump())

        self.data_manager.load()
        self.assertEqual(len(self.data_manager.tasks), 1)

    def test_check_task(self):
        self.assertFalse(self.data_manager.check_task(Task()))
        self.assertFalse(self.data_manager.check_task(Task(objective="Test objective"), skip_empty=True))
        self.assertTrue(self.data_manager.check_task(self.task))

    def test_save(self):
        self.data_manager.save(self.task)
        self.assertTrue(os.path.exists("data/tasks/Test objective"))
        self.assertTrue(os.path.exists("data/tasks/Test objective/task.json"))

    def test_migrate_data(self):
        os.makedirs("data/tasks/current")
        os.makedirs("data/migrate/Test objective")
        self.data_manager.migrate_data(move_current=True, override=True)
        self.assertFalse(os.path.exists("data/tasks/current"))
        self.assertTrue(os.path.exists("data/migrate/current"))
