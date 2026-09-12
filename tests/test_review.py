import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import content_parser
import engine
import reviewbank
from progress import Progress

TODAY = date(2026, 1, 1)


def _module_md(mid, theme="food"):
    return f"""---
id: {mid}
title: "Title {mid}"
phase: 1
turn: 1
difficulty: 2
source: original
themes:
  - {theme}
vocabulary:
  - 밥
---

## A. Context
Some context.

## B. Conversation
**A:** 안녕.
> Hi.

## C. Understand
[[card]]
Q: q1 for {mid}?
A: a1.
[[/card]]
[[card]]
Q: q2 for {mid}?
A: a2.
[[/card]]
[[card]]
Q: q3 for {mid}?
A: a3.
[[/card]]

## E. Active Production
[[respond]]
Q: produce for {mid}?
A: 생산.
[[/respond]]

## G. Transfer
[[respond]]
Q: transfer for {mid}?
A: 전이.
[[/respond]]
"""


def make_course(specs):
    c = engine.Course()
    for mid, theme in specs.items():
        m = content_parser.parse_module(_module_md(mid, theme), fallback_id=mid)
        m["id"] = mid
        c.modules[mid] = m
    return c


class ReviewTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.progress = Progress(directory=Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def complete(self, mid, next_review=TODAY, stage=0):
        m = self.progress.module(mid)
        m["completed"] = True
        self.progress.set_next_review(mid, next_review.isoformat(), sr_index=stage)


class TestDue(ReviewTestBase):
    def test_incomplete_never_due(self):
        course = make_course({"a": "food"})
        # scheduled but NOT completed -> not due
        self.progress.set_next_review("a", TODAY.isoformat(), sr_index=0)
        self.assertEqual(reviewbank.due_module_ids(course, self.progress, TODAY), [])

    def test_completed_due_today(self):
        course = make_course({"a": "food"})
        self.complete("a", next_review=TODAY)
        self.assertEqual(reviewbank.due_module_ids(course, self.progress, TODAY), ["a"])

    def test_future_not_due(self):
        course = make_course({"a": "food"})
        self.complete("a", next_review=TODAY + timedelta(days=3))
        self.assertEqual(reviewbank.due_module_ids(course, self.progress, TODAY), [])

    def test_on_completed_schedules_first_review(self):
        course = make_course({"a": "food"})
        self.progress.module("a")["completed"] = True
        reviewbank.on_completed(self.progress, "a", TODAY)
        m = self.progress.module("a")
        self.assertEqual(m["sr_index"], 0)
        self.assertEqual(m["next_review"], (TODAY + timedelta(days=1)).isoformat())


class TestRecipes(ReviewTestBase):
    def test_stage0_is_three_recall(self):
        course = make_course({"a": "food"})
        self.complete("a", stage=0)
        items = reviewbank._build_items_for_module(course, self.progress, "a")
        self.assertEqual(len(items), 3)
        self.assertTrue(all(it["kind"] == "recall" for it in items))
        self.assertTrue(all(it["module"] == "a" for it in items))

    def test_stage1_two_recall_one_production(self):
        course = make_course({"a": "food"})
        self.complete("a", stage=1)
        items = reviewbank._build_items_for_module(course, self.progress, "a")
        kinds = sorted(it["kind"] for it in items)
        self.assertEqual(kinds, ["production", "recall", "recall"])

    def test_cross_only_uses_completed_modules(self):
        course = make_course({"a": "food", "b": "food"})
        self.complete("a", stage=2)          # base at stage 2 (has cross slots)
        # b is NOT completed -> cross slots must degrade to base's own recall
        items = reviewbank._build_items_for_module(course, self.progress, "a")
        self.assertTrue(all(it["module"] == "a" for it in items),
                        "cross drew from an incomplete module")

        # now complete b (same theme) -> cross slots should draw from b
        self.complete("b", stage=0)
        items = reviewbank._build_items_for_module(course, self.progress, "a")
        self.assertTrue(any(it["module"] == "b" for it in items),
                        "cross did not use the completed same-theme module")


class TestRanking(ReviewTestBase):
    def test_missed_ranked_first(self):
        course = make_course({"a": "food"})
        self.complete("a")
        pool = reviewbank.get_pool(course.get("a"), "recall")
        missed_id = pool[2]
        self.progress.set_rating("a", missed_id, "missed")
        ranked = reviewbank.rank_pool(self.progress, "a", pool)
        self.assertEqual(ranked[0], missed_id)


class TestSession(ReviewTestBase):
    def test_due_summary_does_not_create_session(self):
        course = make_course({"a": "food"})
        self.complete("a")
        summary = reviewbank.due_summary(course, self.progress, TODAY)
        self.assertEqual(summary["questions"], 3)
        self.assertIsNone(reviewbank.active_session(self.progress))

    def test_build_is_refresh_safe(self):
        course = make_course({"a": "food"})
        self.complete("a")
        s1 = reviewbank.build_session(course, self.progress, TODAY)
        s2 = reviewbank.build_session(course, self.progress, TODAY)
        self.assertEqual(s1["id"], s2["id"])
        self.assertEqual(len(s1["items"]), 3)
        # a fresh Progress load from disk still sees the same active session
        reloaded = Progress(directory=self.progress.dir)
        self.assertIsNotNone(reviewbank.active_session(reloaded))

    def test_complete_advances_and_reschedules(self):
        course = make_course({"a": "food"})
        self.complete("a", stage=0)
        session = reviewbank.build_session(course, self.progress, TODAY)
        for i in range(len(session["items"])):
            res = reviewbank.record_rating(course, self.progress, TODAY, i, "got")
        self.assertTrue(res["completed"])
        m = self.progress.module("a")
        self.assertEqual(m["sr_index"], 1)  # advanced
        self.assertEqual(m["next_review"], (TODAY + timedelta(days=3)).isoformat())
        self.assertIsNone(reviewbank.active_session(self.progress))

    def test_missed_holds_stage_and_logs_error(self):
        course = make_course({"a": "food"})
        self.complete("a", stage=1)
        session = reviewbank.build_session(course, self.progress, TODAY)
        n = len(session["items"])
        for i in range(n):
            rating = "missed" if i == 0 else "got"
            reviewbank.record_rating(course, self.progress, TODAY, i, rating)
        m = self.progress.module("a")
        self.assertEqual(m["sr_index"], 1)  # held, not advanced
        self.assertEqual(m["next_review"], (TODAY + timedelta(days=3)).isoformat())
        self.assertGreaterEqual(len(m["errors"]), 1)  # missed item logged

    def test_no_session_when_nothing_due(self):
        course = make_course({"a": "food"})  # not completed
        self.assertIsNone(reviewbank.build_session(course, self.progress, TODAY))


if __name__ == "__main__":
    unittest.main()
