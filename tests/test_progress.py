import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from progress import Progress


class ProgressTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def fresh(self):
        return Progress(directory=self.dir)


class TestSaveLoad(ProgressTestBase):
    def test_roundtrip_and_atomic(self):
        p = self.fresh()
        p.set_answer("plans-01", "plans-01-r1", "먹자")
        self.assertTrue(p.path.exists())
        # reload from disk in a new instance
        q = self.fresh()
        self.assertEqual(q.get_answer("plans-01", "plans-01-r1"), "먹자")

    def test_corrupt_file_recovers(self):
        p = self.fresh()
        p.set_answer("m", "e", "x")
        p.path.write_text("{ not valid json", encoding="utf-8")
        q = self.fresh()  # should not raise
        self.assertEqual(q.data["modules"], {})
        self.assertTrue((self.dir / "progress.corrupt.json").exists())


class TestRatingsPersist(ProgressTestBase):
    def test_rating_restores_after_refresh(self):
        """Mandated: refreshing a completed lesson does not reset recall (§49)."""
        p = self.fresh()
        p.set_rating("plans-01", "plans-01-c1", "got")
        p.set_rating("plans-01", "plans-01-r1", "mostly")
        # simulate a full app restart / page refresh: brand-new load from disk
        q = self.fresh()
        self.assertEqual(q.get_rating("plans-01", "plans-01-c1"), "got")
        self.assertEqual(q.get_rating("plans-01", "plans-01-r1"), "mostly")

    def test_invalid_rating_rejected(self):
        p = self.fresh()
        with self.assertRaises(ValueError):
            p.set_rating("m", "e", "perfect")


class TestErrorLog(ProgressTestBase):
    def test_missed_twice_increments_no_duplicate(self):
        """Mandated: revisiting a persisted mistake does not create a duplicate
        error-log entry (§49). Same (source, prompt) increments frequency."""
        p = self.fresh()
        entry = {
            "type": "production",
            "source": "plans-01-r1",
            "prompt": "Say 'let's eat'.",
            "learner_answer": "먹어",
            "model_answer": "먹자",
        }
        p.log_error("plans-01", dict(entry))
        p.log_error("plans-01", dict(entry))  # replay / revisit
        p.log_error("plans-01", dict(entry))

        errors = p.module("plans-01")["errors"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["frequency"], 3)

        # survives reload without duplicating
        q = self.fresh()
        self.assertEqual(len(q.module("plans-01")["errors"]), 1)

    def test_different_prompts_are_separate(self):
        p = self.fresh()
        p.log_error("plans-01", {"source": "a", "prompt": "P1"})
        p.log_error("plans-01", {"source": "b", "prompt": "P2"})
        self.assertEqual(len(p.module("plans-01")["errors"]), 2)


class TestQuizAndMastery(ProgressTestBase):
    def test_quiz_persist(self):
        p = self.fresh()
        p.set_quiz("plans-01", "plans-01-q1", 1, True)
        q = self.fresh()
        saved = q.get_quiz("plans-01", "plans-01-q1")
        self.assertEqual(saved["choice"], 1)
        self.assertTrue(saved["correct"])

    def test_mastery_combines_recall_and_quiz(self):
        p = self.fresh()
        # all recall got, all quiz correct -> 100
        p.set_rating("m", "m-c1", "got")
        p.set_rating("m", "m-r1", "got")
        p.set_quiz("m", "m-q1", 0, True)
        mastery = p.recompute_mastery("m", {"recall": ["m-c1", "m-r1"], "quiz": ["m-q1"]})
        self.assertEqual(mastery, 100)

        # one missed recall lowers it
        p.set_rating("m", "m-r1", "missed")
        mastery = p.recompute_mastery("m", {"recall": ["m-c1", "m-r1"], "quiz": ["m-q1"]})
        self.assertLess(mastery, 100)
        self.assertGreater(mastery, 0)


if __name__ == "__main__":
    unittest.main()
