import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


class TestCourseContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.course = engine.Course.load(CONTENT_DIR)

    def test_loads_at_least_one_module(self):
        self.assertGreaterEqual(len(self.course.modules), 1)

    def test_all_modules_valid(self):
        problems = engine.validate(self.course)
        self.assertEqual(problems, [], "content validation problems:\n" + "\n".join(problems))

    def test_ids_unique(self):
        ids = list(self.course.modules)
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_production_has_answer(self):
        for m in self.course.modules.values():
            for ex in m["exercises"].values():
                if ex["type"] == "respond":
                    self.assertTrue(any(a.strip() for a in ex["a"]),
                                    f"{ex['id']} has no model answer")

    def test_every_quiz_one_correct(self):
        for m in self.course.modules.values():
            for ex in m["exercises"].values():
                if ex["type"] == "quiz":
                    correct = [o for o in ex["options"] if o["correct"]]
                    self.assertEqual(len(correct), 1, f"{ex['id']} bad correct count")


if __name__ == "__main__":
    unittest.main()
