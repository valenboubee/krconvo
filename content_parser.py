"""
content_parser.py — Markdown + custom-block parser for Korean Conversation Lab.

Deterministic, offline, stdlib-only. Parses a conversation module (.md) into a
structured dict:

    {
      "meta":     {frontmatter fields},
      "sections": [{"title": str, "elements": [element, ...]}, ...],
      "turns":    [{"speaker", "korean", "english"}, ...],   # from Section B
      "exercises":{exercise_id: exercise, ...},              # flat, doc order
    }

An element is one of:
    {"type": "md",           "html": "<...>"}
    {"type": "conversation", "turns": [...]}
    {"type": "card",         "id", "q", "a"}           # a is a str
    {"type": "respond",      "id", "q", "a"}           # a is list[str]
    {"type": "quiz",         "id", "q", "options":[{"text","correct"}], "answer": idx}

Custom block syntax (see spec §30):

    [[card]]     [[respond]]     [[quiz]]
    Q: ...       Q: ...          Q: ...
    A: ...       A:              - wrong option
    [[/card]]    - answer 1      * correct option
                 - answer 2      - wrong option
                 [[/respond]]    [[/quiz]]

IDs are assigned deterministically per module in document order:
    card -> <module_id>-c1, respond -> -r1, quiz -> -q1, ...
"""

from __future__ import annotations

import html
import re


# --------------------------------------------------------------------------
# Frontmatter (minimal YAML subset: scalars + one-level "- " lists)
# --------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _coerce_scalar(value: str):
    """Turn a scalar string into int/bool/None/str, stripping quotes."""
    v = value.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~", "none", ""):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def parse_frontmatter(text: str):
    """Return (meta_dict, body_str). meta is {} if no frontmatter present."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    block = m.group(1)
    body = text[m.end():]

    meta: dict = {}
    current_key = None  # key currently accumulating list items
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        # list item under the current key
        item_match = re.match(r"^\s+-\s+(.*)$", line)
        if item_match and current_key is not None:
            meta.setdefault(current_key, [])
            if isinstance(meta[current_key], list):
                meta[current_key].append(_coerce_scalar(item_match.group(1)))
            continue
        # key: value  OR  key: (start of list)
        kv = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val == "":
                current_key = key
                meta[key] = []  # provisional; stays [] if no items follow
            else:
                current_key = None
                meta[key] = _coerce_scalar(val)
    return meta, body


# --------------------------------------------------------------------------
# Minimal inline + block Markdown -> HTML (safe: escapes & < >)
# --------------------------------------------------------------------------

def _inline(text: str) -> str:
    """Inline markdown on already-escaped text."""
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    """Render a chunk of markdown to HTML. Handles headings, blockquotes,
    unordered lists, and paragraphs. Korean passes through untouched."""
    lines = html.escape(md, quote=False).split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # headings ### / ####
        h = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if h:
            level = min(len(h.group(1)) + 2, 6)  # ### -> h5-ish; keep modest
            out.append(f"<h{level}>{_inline(h.group(2))}</h{level}>")
            i += 1
            continue

        # blockquote (consecutive > lines)
        if stripped.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = _inline(" ".join(q.strip() for q in quote_lines))
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # unordered list (consecutive - / * items)
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                items.append(f"<li>{_inline(item)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # paragraph (gather until blank / block start)
        para = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|>|[-*]\s)", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(para))}</p>")

    return "\n".join(out)


# --------------------------------------------------------------------------
# Conversation turns
# --------------------------------------------------------------------------

_TURN_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.+)$")
_ENG_RE = re.compile(r"^>\s*(.*)$")


def parse_turns(block_lines: list[str]):
    """Parse conversation turns from lines. A turn is a **Speaker:** line
    (Korean) optionally followed by a `> English` line."""
    turns = []
    i = 0
    n = len(block_lines)
    while i < n:
        line = block_lines[i].rstrip()
        m = _TURN_RE.match(line.strip())
        if m:
            speaker = m.group(1).strip()
            korean = m.group(2).strip()
            english = ""
            if i + 1 < n:
                em = _ENG_RE.match(block_lines[i + 1].strip())
                if em:
                    english = em.group(1).strip()
                    i += 1
            turns.append({"speaker": speaker, "korean": korean, "english": english})
        i += 1
    return turns


# --------------------------------------------------------------------------
# Custom blocks
# --------------------------------------------------------------------------

_BLOCK_OPEN = re.compile(r"^\[\[(card|respond|quiz)\]\]\s*$")
_BLOCK_CLOSE = re.compile(r"^\[\[/(card|respond|quiz)\]\]\s*$")


def _parse_qa(lines: list[str]):
    """Parse Q:/A: content. Returns (question, answer_lines) where
    answer_lines is the raw list of lines after 'A:'."""
    question = ""
    answer_lines: list[str] = []
    mode = None
    for line in lines:
        q = re.match(r"^Q:\s*(.*)$", line)
        a = re.match(r"^A:\s*(.*)$", line)
        if q:
            mode = "q"
            question = q.group(1).strip()
        elif a:
            mode = "a"
            rest = a.group(1).strip()
            if rest:
                answer_lines.append(rest)
        elif mode == "q":
            question = (question + " " + line.strip()).strip()
        elif mode == "a":
            answer_lines.append(line.rstrip())
    return question, answer_lines


def _split_answer(text: str):
    """A model answer may carry an optional English gloss after ' | ':
        한국어 문장 | English translation
    Returns (korean, english). English is '' when no gloss is present."""
    if " | " in text:
        ko, en = text.split(" | ", 1)
        return ko.strip(), en.strip()
    return text.strip(), ""


def _answers_with_translations(answer_lines: list[str]):
    """Extract model answers + optional per-answer translations. Supports a
    single scalar or a '- ' bullet list. Returns (koreans, englishes) as two
    aligned lists (english entry is '' where no ' | ' gloss was given)."""
    bullets = [re.sub(r"^-\s+", "", ln.strip()) for ln in answer_lines if ln.strip().startswith("- ")]
    if bullets:
        pairs = [_split_answer(b) for b in bullets]
    else:
        joined = " ".join(ln.strip() for ln in answer_lines if ln.strip())
        pairs = [_split_answer(joined)] if joined else []
    koreans = [p[0] for p in pairs]
    englishes = [p[1] for p in pairs]
    return koreans, englishes


def _parse_quiz_body(lines: list[str]):
    """Parse quiz. '* option' is correct, '- option' is a distractor."""
    question = ""
    options = []
    for line in lines:
        q = re.match(r"^Q:\s*(.*)$", line)
        if q:
            question = q.group(1).strip()
            continue
        s = line.strip()
        if s.startswith("* "):
            options.append({"text": s[2:].strip(), "correct": True})
        elif s.startswith("- "):
            options.append({"text": s[2:].strip(), "correct": False})
    answer = next((idx for idx, o in enumerate(options) if o["correct"]), None)
    return question, options, answer


# --------------------------------------------------------------------------
# Top-level module parse
# --------------------------------------------------------------------------

def parse_module(text: str, fallback_id: str = "module"):
    """Parse a full conversation module into the structured dict described in
    the module docstring."""
    meta, body = parse_frontmatter(text)
    module_id = str(meta.get("id") or fallback_id)

    counters = {"card": 0, "respond": 0, "quiz": 0}
    id_prefix = {"card": "c", "respond": "r", "quiz": "q"}

    sections: list[dict] = []
    exercises: dict = {}
    turns: list[dict] = []

    # Section 0 (content before the first ## header) is kept as "intro".
    current = {"title": "", "elements": []}
    sections.append(current)

    lines = body.split("\n")
    i = 0
    n = len(lines)
    md_buffer: list[str] = []

    def flush_md():
        if md_buffer:
            chunk = "\n".join(md_buffer).strip()
            if chunk:
                current["elements"].append({"type": "md", "html": md_to_html(chunk)})
            md_buffer.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # New section header
        h = re.match(r"^##\s+(.*)$", stripped)
        if h:
            flush_md()
            current = {"title": h.group(1).strip(), "elements": []}
            sections.append(current)
            i += 1
            continue

        # Custom block open
        bo = _BLOCK_OPEN.match(stripped)
        if bo:
            flush_md()
            kind = bo.group(1)
            block_lines = []
            i += 1
            while i < n and not _BLOCK_CLOSE.match(lines[i].strip()):
                block_lines.append(lines[i])
                i += 1
            i += 1  # consume the closing tag (or run off end)

            counters[kind] += 1
            ex_id = f"{module_id}-{id_prefix[kind]}{counters[kind]}"

            sec_match = re.match(r"^([A-Z])[.\s]", current["title"])
            sec_letter = sec_match.group(1) if sec_match else ""

            if kind == "card":
                q, a_lines = _parse_qa(block_lines)
                full = " ".join(ln.strip() for ln in a_lines if ln.strip())
                ko, en = _split_answer(full)
                ex = {"type": "card", "id": ex_id, "q": q, "a": ko, "a_en": en}
            elif kind == "respond":
                q, a_lines = _parse_qa(block_lines)
                answers, translations = _answers_with_translations(a_lines)
                ex = {"type": "respond", "id": ex_id, "q": q, "a": answers, "a_en": translations}
            else:  # quiz
                q, options, answer = _parse_quiz_body(block_lines)
                ex = {"type": "quiz", "id": ex_id, "q": q, "options": options, "answer": answer}

            ex["section"] = sec_letter
            exercises[ex_id] = ex
            current["elements"].append(ex)
            continue

        # Conversation turn(s) — only parsed inside Section B, so that
        # "**Meaning:**"-style lines elsewhere render as bold markdown instead.
        in_conversation = current["title"].startswith("B.") or current["title"].startswith("B ")
        if in_conversation and _TURN_RE.match(stripped):
            flush_md()
            turn_block = []
            while i < n:
                s = lines[i].strip()
                if _TURN_RE.match(s) or _ENG_RE.match(s) or not s:
                    if not s and turn_block and i + 1 < n and not _TURN_RE.match(lines[i + 1].strip()):
                        break
                    turn_block.append(lines[i])
                    i += 1
                else:
                    break
            parsed = parse_turns(turn_block)
            if parsed:
                turns.extend(parsed)
                current["elements"].append({"type": "conversation", "turns": parsed})
            continue

        md_buffer.append(line)
        i += 1

    flush_md()

    # Drop empty leading intro section
    sections = [s for s in sections if s["title"] or s["elements"]]

    return {
        "meta": meta,
        "sections": sections,
        "turns": turns,
        "exercises": exercises,
    }
