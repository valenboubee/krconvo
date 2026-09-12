"""
engine.py — course loader + content validation.

Scans content/ for *.md conversation modules, parses each with
content_parser, and exposes:

    Course.load(content_dir)      -> Course
    course.modules               -> {id: module}
    course.ordered()             -> [module, ...] sorted by phase then id
    course.get(module_id)        -> module or None
    course.by_phase()            -> {phase: [module, ...]}
    course.recall_ids(module)    -> [exercise_id, ...]  (cards + responds)
    course.quiz_ids(module)      -> [exercise_id, ...]

    validate(course)             -> [problem_str, ...]   (spec §37 gates)

The engine is pure content logic. It never touches the network or an AI
service, and never writes progress.
"""

from __future__ import annotations

from pathlib import Path

import content_parser

SECTION_LETTERS = ["A.", "B.", "C.", "D.", "E.", "F.", "G."]
VALID_TURNS = (1, 2)
VALID_DIFFICULTY = (1, 2, 3, 4, 5)
VALID_SPEECH_LEVELS = ("polite", "casual", "intimate", "formal", "mixed")


class Course:
    def __init__(self):
        self.modules: dict[str, dict] = {}
        self.load_errors: list[str] = []

    @classmethod
    def load(cls, content_dir: str | Path) -> "Course":
        course = cls()
        content_dir = Path(content_dir)
        if not content_dir.exists():
            return course
        for path in sorted(content_dir.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                course.load_errors.append(f"{path}: cannot read ({exc})")
                continue
            fallback = path.stem
            module = content_parser.parse_module(text, fallback_id=fallback)
            module["_path"] = str(path)
            module["_rel"] = str(path.relative_to(content_dir)) if path.is_relative_to(content_dir) else str(path)
            mid = str(module["meta"].get("id") or fallback)
            module["id"] = mid
            if mid in course.modules:
                course.load_errors.append(f"duplicate module id: {mid}")
            course.modules[mid] = module
        return course

    # ---- lookups ---------------------------------------------------------

    def get(self, module_id: str):
        return self.modules.get(module_id)

    def ordered(self) -> list[dict]:
        return sorted(
            self.modules.values(),
            key=lambda m: (m["meta"].get("phase", 99), m["meta"].get("difficulty", 99), m["id"]),
        )

    def by_phase(self) -> dict:
        phases: dict = {}
        for m in self.ordered():
            phases.setdefault(m["meta"].get("phase", 0), []).append(m)
        return phases

    @staticmethod
    def recall_ids(module: dict) -> list[str]:
        return [ex["id"] for ex in module["exercises"].values() if ex["type"] in ("card", "respond")]

    @staticmethod
    def quiz_ids(module: dict) -> list[str]:
        return [ex["id"] for ex in module["exercises"].values() if ex["type"] == "quiz"]

    @staticmethod
    def card_ids(module: dict) -> list[str]:
        return [ex["id"] for ex in module["exercises"].values() if ex["type"] == "card"]


# --------------------------------------------------------------------------
# Validation gates (spec §37). Returns a list of human-readable problems.
# --------------------------------------------------------------------------

def validate(course: Course) -> list[str]:
    problems: list[str] = list(course.load_errors)

    seen_ids: set[str] = set()

    for module in course.ordered():
        mid = module["id"]
        meta = module["meta"]
        rel = module.get("_rel", mid)

        # (1) frontmatter present + (2) unique id
        if not meta:
            problems.append(f"{rel}: missing frontmatter")
        if not meta.get("id"):
            problems.append(f"{rel}: frontmatter missing 'id'")
        if mid in seen_ids:
            problems.append(f"{rel}: duplicate id '{mid}'")
        seen_ids.add(mid)

        # (3) valid turn
        if meta.get("turn") not in VALID_TURNS:
            problems.append(f"{mid}: turn must be 1 or 2 (got {meta.get('turn')!r})")

        # (4) valid difficulty
        if meta.get("difficulty") not in VALID_DIFFICULTY:
            problems.append(f"{mid}: difficulty must be 1-5 (got {meta.get('difficulty')!r})")

        # speech level (spec §34)
        sl = meta.get("speech_level")
        if sl is not None and sl not in VALID_SPEECH_LEVELS:
            problems.append(f"{mid}: unknown speech_level '{sl}'")

        # (10) sections A-G + Quiz present
        titles = [s["title"] for s in module["sections"]]
        joined = " | ".join(titles)
        for letter in SECTION_LETTERS:
            if not any(t.startswith(letter) for t in titles):
                problems.append(f"{mid}: missing section '{letter}' (have: {joined})")
        if not any("quiz" in t.lower() for t in titles):
            problems.append(f"{mid}: missing 'Quiz' section")

        # (12) speaker labels present in conversation
        if not module["turns"]:
            problems.append(f"{mid}: no conversation turns parsed in Section B")
        for t in module["turns"]:
            if not t["speaker"]:
                problems.append(f"{mid}: a conversation turn is missing a speaker label")

        # (8) each quiz has exactly one correct answer; (9) production has model answer;
        # (11) no empty exercises
        for ex in module["exercises"].values():
            if not ex.get("q"):
                problems.append(f"{mid}/{ex['id']}: exercise has no question/prompt")
            if ex["type"] == "quiz":
                correct = [o for o in ex["options"] if o["correct"]]
                if len(correct) != 1:
                    problems.append(f"{mid}/{ex['id']}: quiz must have exactly one correct answer (has {len(correct)})")
                if len(ex["options"]) < 2:
                    problems.append(f"{mid}/{ex['id']}: quiz needs at least 2 options")
            if ex["type"] == "respond":
                if not ex["a"] or not any(a.strip() for a in ex["a"]):
                    problems.append(f"{mid}/{ex['id']}: production exercise has no model answer")
            if ex["type"] == "card":
                if not ex["a"].strip():
                    problems.append(f"{mid}/{ex['id']}: recall card has no answer")

    return problems
