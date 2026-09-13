import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import content_parser as cp
import engine

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


# A small, controlled conversation (5 turns, 2 speakers) so we can pin the
# deterministic generator's behaviour exactly. Only Section B / frontmatter
# matter to reconstruction, so the other sections are kept minimal.
RECON_MD = """---
id: recon-01
title: "Reconstruct sample"
phase: 1
turn: 1
difficulty: 2
source: original
speech_level: casual
themes:
  - food
vocabulary:
  - 떡볶이
grammar:
  - -ㄹ까?
---

## A. Context

Two friends deciding what to eat.

## B. Conversation

**수민:** 오늘 뭐 먹을까?
> What should we eat today?

**지훈:** 떡볶이 어때?
> How about tteokbokki?

**수민:** 좋아, 먹으러 가자.
> Okay, let's go eat.

**지훈:** 나 지금 배고파.
> I'm hungry now.

**수민:** 그럼 빨리 가자.
> Then let's go quickly.

## C. Understand

[[card]]
Q: card q?
A: card a.
[[/card]]

## Quiz Check

[[quiz]]
Q: q?
* right
- wrong
[[/quiz]]
"""


def _short_module(n_turns):
    turns = [{"speaker": "A", "korean": "안녕", "english": "hi"} for _ in range(n_turns)]
    return {"id": "x", "meta": {}, "turns": turns, "exercises": {}, "sections": []}


class TestGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = cp.parse_module(RECON_MD)
        cls.items = engine.reconstruction(cls.mod)

    def _of_kind(self, kind):
        return [it for it in self.items if it["kind"] == kind]

    def test_all_four_kinds_present(self):
        self.assertEqual(
            {it["kind"] for it in self.items},
            {"speaker", "phrase", "line", "skeleton"},
        )

    def test_ids_unique_and_namespaced(self):
        ids = [it["id"] for it in self.items]
        self.assertEqual(len(ids), len(set(ids)), "reconstruction ids collide")
        for i in ids:
            self.assertTrue(i.startswith("recon-01-r"), f"unexpected id {i}")
        self.assertEqual(self._of_kind("skeleton")[0]["id"], "recon-01-rk1")

    def test_ids_do_not_collide_with_exercises(self):
        ids = {it["id"] for it in self.items}
        self.assertTrue(ids.isdisjoint(self.mod["exercises"].keys()))

    def test_caps(self):
        self.assertLessEqual(len(self._of_kind("speaker")), 3)
        self.assertLessEqual(len(self._of_kind("phrase")), 2)
        self.assertLessEqual(len(self._of_kind("line")), 2)
        self.assertEqual(len(self._of_kind("skeleton")), 1)

    def test_skeleton_shape(self):
        sk = self._of_kind("skeleton")[0]
        self.assertEqual(sk["speakers"], ["수민", "지훈"])
        self.assertEqual(sk["vocab"], ["떡볶이"])
        self.assertEqual(len(sk["dialogue"]), 5)
        self.assertEqual(sk["dialogue"][0]["korean"], "오늘 뭐 먹을까?")

    def test_speaker_items_match_a_real_turn(self):
        turns = self.mod["turns"]
        for it in self._of_kind("speaker"):
            match = any(
                t["english"] == it["english"] and t["korean"] == it["answer_ko"]
                for t in turns
            )
            self.assertTrue(match, f"speaker item does not match any turn: {it}")

    def test_missing_line_has_one_blank_and_never_the_first_line(self):
        for it in self._of_kind("line"):
            blanks = [c for c in it["context"] if c["blank"]]
            self.assertEqual(len(blanks), 1, "exactly one line must be blanked")
            # a non-blank context line always precedes the blank => the very
            # first turn of the conversation is never the one blanked out.
            self.assertFalse(it["context"][0]["blank"])
            self.assertEqual(blanks[0]["korean"], it["answer_ko"])

    def test_missing_phrase_mask_round_trips(self):
        for it in self._of_kind("phrase"):
            self.assertIn("____", it["masked"])
            self.assertIn(it["answer_phrase"], it["answer_ko"])
            self.assertEqual(
                it["masked"].replace("____", it["answer_phrase"], 1),
                it["answer_ko"],
            )

    def test_missing_phrase_prefers_a_vocab_word(self):
        # 떡볶이 is a vocabulary token and appears verbatim in a line, so at
        # least one phrase exercise should blank exactly that word.
        self.assertTrue(
            any(it["answer_phrase"] == "떡볶이" for it in self._of_kind("phrase"))
        )

    def test_deterministic(self):
        self.assertEqual(engine.reconstruction(self.mod), engine.reconstruction(self.mod))

    def test_too_short_returns_empty(self):
        self.assertEqual(engine.reconstruction(_short_module(1)), [])
        self.assertEqual(engine.reconstruction(_short_module(0)), [])


class TestAgainstRealCourse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.course = engine.Course.load(CONTENT_DIR)

    def test_every_conversation_generates_items(self):
        for m in self.course.modules.values():
            items = engine.reconstruction(m)
            self.assertTrue(items, f"{m['id']} produced no reconstruction items")

    def test_ids_unique_and_disjoint_from_exercises(self):
        for m in self.course.modules.values():
            ids = [it["id"] for it in engine.reconstruction(m)]
            self.assertEqual(len(ids), len(set(ids)), f"{m['id']} recon id collision")
            self.assertTrue(
                set(ids).isdisjoint(m["exercises"].keys()),
                f"{m['id']} recon id collides with an exercise id",
            )

    def test_reconstruction_is_excluded_from_mastery_ids(self):
        # recall/quiz id lists drive the mastery formula; reconstruction items
        # must never appear there, so mastery of existing conversations is
        # unaffected by this feature.
        for m in self.course.modules.values():
            recon_ids = {it["id"] for it in engine.reconstruction(m)}
            mastery_ids = set(engine.Course.recall_ids(m)) | set(engine.Course.quiz_ids(m))
            self.assertTrue(recon_ids.isdisjoint(mastery_ids))


class TestRender(unittest.TestCase):
    """Render-level checks. app.py holds module-level COURSE/PROGRESS globals, so
    isolate progress to a temp dir before importing it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["KCL_PROGRESS_DIR"] = cls.tmp.name
        import app
        cls.app = app
        cls.module = app.COURSE.get("goodnight-01") or next(iter(app.COURSE.modules.values()))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
        os.environ.pop("KCL_PROGRESS_DIR", None)

    def test_section_rendered_before_quiz(self):
        html = self.app.render_lesson(self.module)
        self.assertIn("Reconstruct the Conversation", html)
        self.assertIn("Quiz Check", html)
        self.assertLess(
            html.index("Reconstruct the Conversation"),
            html.index("Quiz Check"),
            "reconstruction section must come before the quiz",
        )

    def test_items_carry_persistence_hooks(self):
        html = self.app.render_reconstruct_section(self.module)
        self.assertIn('data-type="reconstruct"', html)
        self.assertIn('data-kind="reconstruction"', html)
        self.assertIn("rate-btn", html)
        self.assertIn(self.module["id"] + "-rk1", html)

    def test_empty_when_too_few_turns(self):
        stub = {"id": "stub", "meta": {}, "turns": [], "exercises": {}, "sections": []}
        self.assertEqual(self.app.render_reconstruct_section(stub), "")


if __name__ == "__main__":
    unittest.main()
