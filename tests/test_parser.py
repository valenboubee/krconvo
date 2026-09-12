import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import content_parser as cp


SAMPLE = """---
id: sample-01
title: "Testing the parser"
phase: 1
turn: 1
difficulty: 2
source: original
speech_level: casual
themes:
  - daily_life
  - food
grammar:
  - -ㄹ까?
---

## A. Context

A quick test conversation.

## B. Conversation

**수민:** 오늘 뭐 먹을까?
> What should we eat today?

**지훈:** 떡볶이 어때?
> How about tteokbokki?

## C. Understand

[[card]]
Q: What does 당기다 mean?
A: to crave (food).
[[/card]]

[[respond]]
Q: Say "let's eat".
A: 먹자
[[/respond]]

[[respond]]
Q: React to sad news.
A:
- 괜찮아?
- 많이 힘들었어?
[[/respond]]

[[respond]]
Q: 이번 주말에 뭐 하고 싶어?
A: 집에서 쉬고 싶어. | I want to rest at home.
[[/respond]]

## Quiz Check

[[quiz]]
Q: Which is correct?
- 먹습니다
* 먹자
- 먹으세요
[[/quiz]]
"""


class TestFrontmatter(unittest.TestCase):
    def test_scalars_and_types(self):
        meta, body = cp.parse_frontmatter(SAMPLE)
        self.assertEqual(meta["id"], "sample-01")
        self.assertEqual(meta["title"], "Testing the parser")
        self.assertEqual(meta["phase"], 1)          # int coercion
        self.assertEqual(meta["difficulty"], 2)
        self.assertEqual(meta["source"], "original")
        self.assertTrue(body.lstrip().startswith("## A."))

    def test_lists(self):
        meta, _ = cp.parse_frontmatter(SAMPLE)
        self.assertEqual(meta["themes"], ["daily_life", "food"])
        self.assertEqual(meta["grammar"], ["-ㄹ까?"])

    def test_no_frontmatter(self):
        meta, body = cp.parse_frontmatter("no front matter here")
        self.assertEqual(meta, {})
        self.assertEqual(body, "no front matter here")


class TestBlocks(unittest.TestCase):
    def setUp(self):
        self.mod = cp.parse_module(SAMPLE)

    def test_ids_deterministic(self):
        ids = list(self.mod["exercises"])
        self.assertIn("sample-01-c1", ids)
        self.assertIn("sample-01-r1", ids)
        self.assertIn("sample-01-r2", ids)
        self.assertIn("sample-01-q1", ids)

    def test_card(self):
        card = self.mod["exercises"]["sample-01-c1"]
        self.assertEqual(card["type"], "card")
        self.assertIn("당기다", card["q"])
        self.assertEqual(card["a"], "to crave (food).")

    def test_single_model_answer(self):
        r = self.mod["exercises"]["sample-01-r1"]
        self.assertEqual(r["a"], ["먹자"])

    def test_multiple_model_answers(self):
        r = self.mod["exercises"]["sample-01-r2"]
        self.assertEqual(r["a"], ["괜찮아?", "많이 힘들었어?"])

    def test_quiz_one_correct(self):
        q = self.mod["exercises"]["sample-01-q1"]
        correct = [o for o in q["options"] if o["correct"]]
        self.assertEqual(len(correct), 1)
        self.assertEqual(q["options"][q["answer"]]["text"], "먹자")

    def test_answer_translation_split(self):
        # ' | English' gloss is split off into a_en, aligned by index.
        r = self.mod["exercises"]["sample-01-r3"]
        self.assertEqual(r["a"], ["집에서 쉬고 싶어."])
        self.assertEqual(r["a_en"], ["I want to rest at home."])

    def test_no_translation_leaves_a_en_empty(self):
        r = self.mod["exercises"]["sample-01-r1"]  # "먹자", no gloss
        self.assertEqual(r["a"], ["먹자"])
        self.assertEqual(r["a_en"], [""])


class TestDialogue(unittest.TestCase):
    def test_turns(self):
        mod = cp.parse_module(SAMPLE)
        self.assertEqual(len(mod["turns"]), 2)
        self.assertEqual(mod["turns"][0]["speaker"], "수민")
        self.assertEqual(mod["turns"][0]["korean"], "오늘 뭐 먹을까?")
        self.assertEqual(mod["turns"][0]["english"], "What should we eat today?")

    def test_meaning_line_not_treated_as_turn(self):
        # A "**Meaning:**" line outside Section B must NOT become a dialogue turn.
        text = SAMPLE + "\n## D. Language\n\n**Meaning:** just a bold label.\n"
        mod = cp.parse_module(text)
        speakers = [t["speaker"] for t in mod["turns"]]
        self.assertNotIn("Meaning", speakers)
        self.assertEqual(len(mod["turns"]), 2)


class TestMarkdown(unittest.TestCase):
    def test_korean_survives(self):
        html = cp.md_to_html("떡볶이 **매운** 거 좋아해")
        self.assertIn("떡볶이", html)
        self.assertIn("<strong>매운</strong>", html)

    def test_html_escaped(self):
        html = cp.md_to_html("2 < 3 & 4 > 1")
        self.assertIn("&lt;", html)
        self.assertIn("&gt;", html)
        self.assertIn("&amp;", html)


if __name__ == "__main__":
    unittest.main()
