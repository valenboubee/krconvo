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


# --------------------------------------------------------------------------
# Conversation reconstruction (spec §21)
#
# Deterministic exercises generated from a module's parsed turns + frontmatter.
# Nothing is authored in the .md and nothing is graded by AI: each item is a
# recall prompt whose answer is revealed for self-rating, exactly like a card
# or a respond. Reconstruction items are deliberately NOT part of the mastery
# formula (recall_ids / quiz_ids), so adding this feature never disturbs the
# completion or spaced-repetition state of existing conversations. Items are
# returned as plain data (no HTML); app.py renders them.
# --------------------------------------------------------------------------

_RECON_MAX = {"speaker": 3, "phrase": 2, "line": 2}


def _pick_evenly(candidates: list, count: int) -> list:
    """Pick up to `count` items spread evenly across `candidates`, preserving
    order and never repeating. Deterministic."""
    if count <= 0 or not candidates:
        return []
    if len(candidates) <= count:
        return list(candidates)
    step = (len(candidates) - 1) / (count - 1) if count > 1 else 0
    picked, seen = [], set()
    for j in range(count):
        val = candidates[round(j * step)]
        if val not in seen:
            seen.add(val)
            picked.append(val)
    return picked


def _recon_speakers(turns: list) -> list:
    order: list = []
    for t in turns:
        s = t.get("speaker", "")
        if s and s not in order:
            order.append(s)
    return order


def _recon_stems(meta: dict) -> list:
    """Learning-point tokens to aim the 'missing phrase' blank at, drawn from
    frontmatter vocabulary then grammar. Parentheticals, leading dashes/tildes
    and trailing punctuation are stripped so a stem can be found inside a
    conjugated word (e.g. vocabulary 맛있다 -> 맛있, which is inside 맛있더라).
    Grammar markers written in bare jamo (e.g. -ㄹ래?) usually will not appear
    verbatim in a syllable-composed line; that is fine — the phrase generator
    falls back to the last word of the line."""
    stems: list = []
    for key in ("vocabulary", "grammar"):
        for item in (meta.get(key) or []):
            s = str(item).split("(")[0]
            s = s.strip().strip("-~").split("/")[0].strip(" -~?.!,")
            if key == "vocabulary" and s.endswith("다") and len(s) > 2:
                s = s[:-1]
            if s:
                stems.append(s)
    return stems


def _recon_window(turns: list, i: int) -> list:
    """Surrounding lines for a 'missing line' item: up to two lines before and
    one after turn `i`, with turn `i` flagged as the blank."""
    start = max(0, i - 2)
    end = min(len(turns), i + 2)
    return [
        {
            "speaker": turns[j].get("speaker", ""),
            "korean": turns[j].get("korean", ""),
            "english": turns[j].get("english", ""),
            "blank": j == i,
        }
        for j in range(start, end)
    ]


def reconstruction(module: dict) -> list:
    """Generate deterministic reconstruction exercises (spec §21) from a
    module's turns. Returns a list of plain-data item dicts, ramping in
    difficulty: speaker recall -> missing phrase -> missing line -> full
    rebuild. Empty for conversations too short to reconstruct (< 2 turns)."""
    turns = module.get("turns") or []
    meta = module.get("meta") or {}
    # Match content_parser's id convention: Course.load sets module["id"], but a
    # freshly parsed module carries its id only in the frontmatter.
    mid = str(module.get("id") or meta.get("id") or "module")
    n = len(turns)
    if n < 2:
        return []

    items: list = []

    # Speaker recall (English -> Korean line): warm-up, up to 3.
    spk = [i for i, t in enumerate(turns) if t.get("korean") and t.get("english")]
    for k, i in enumerate(_pick_evenly(spk, _RECON_MAX["speaker"]), start=1):
        t = turns[i]
        items.append({
            "id": f"{mid}-rs{k}",
            "kind": "speaker",
            "speaker": t.get("speaker", ""),
            "english": t.get("english", ""),
            "answer_ko": t.get("korean", ""),
        })

    # Missing phrase: prefer lines containing a learning-point word (vocab /
    # grammar); fall back to the last word of a line only to fill the quota.
    # Two passes keep the blank aimed at something worth practising.
    stems = _recon_stems(meta)
    stem_hits: list = []      # (turn_index, word_containing_a_stem)
    fallbacks: list = []      # (turn_index, last_word)
    for i, t in enumerate(turns):
        words = t.get("korean", "").split()
        if len(words) < 2:
            continue
        chosen = None
        for stem in stems:
            for w in words:
                if stem and stem in w:
                    chosen = w
                    break
            if chosen:
                break
        if chosen is not None:
            stem_hits.append((i, chosen))
        else:
            fallbacks.append((i, words[-1]))
    phrase_hits = sorted((stem_hits + fallbacks)[:_RECON_MAX["phrase"]])
    for k, (i, phrase) in enumerate(phrase_hits, start=1):
        ko = turns[i].get("korean", "")
        items.append({
            "id": f"{mid}-rp{k}",
            "kind": "phrase",
            "speaker": turns[i].get("speaker", ""),
            "masked": ko.replace(phrase, "____", 1),
            "english": turns[i].get("english", ""),
            "answer_phrase": phrase,
            "answer_ko": ko,
        })

    # Missing line: blank a whole line (never the opener), up to 2.
    line_cands = [i for i in range(1, n) if turns[i].get("korean")]
    for k, i in enumerate(_pick_evenly(line_cands, _RECON_MAX["line"]), start=1):
        t = turns[i]
        items.append({
            "id": f"{mid}-rl{k}",
            "kind": "line",
            "speaker": t.get("speaker", ""),
            "context": _recon_window(turns, i),
            "english_hint": t.get("english", ""),
            "answer_ko": t.get("korean", ""),
        })

    # Skeleton: rebuild the whole thing from situation + speakers + key vocab.
    items.append({
        "id": f"{mid}-rk1",
        "kind": "skeleton",
        "speakers": _recon_speakers(turns),
        "vocab": list(meta.get("vocabulary") or []),
        "dialogue": [
            {"speaker": t.get("speaker", ""), "korean": t.get("korean", ""), "english": t.get("english", "")}
            for t in turns
        ],
    })

    return items
