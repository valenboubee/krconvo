# Design notes — Korean Conversation Lab

Offline, single-user, conversation-first Korean study app. No accounts, no
network, no AI at study time. Content lives in Markdown; the engine renders and
tracks it. See the full spec in `../Korean_Conversation_Lab_PROMPT.md`.

## Architecture (deliberately small — spec §28, §29)

```
app.py            HTTP server (stdlib http.server), routing, HTML rendering, JSON API
engine.py         Loads content/*.md into a Course; content validation gates (§37)
content_parser.py Markdown + custom-block ([[card]]/[[respond]]/[[quiz]]) parser
progress.py       Atomic JSON progress (~/.korean-conversation-lab/progress.json)
reviewbank.py     Spaced-repetition: due scheduling, real review questions, sessions (§19)
content/          Conversation modules (.md), grouped by theme folder
static/           style.css, app.js  (no CDNs, no frameworks)
tests/            unittest suites
```

No database. No third-party runtime dependencies. Python 3 standard library only.

## Data flow

1. `engine.Course.load(content/)` parses every `.md` into a module dict:
   `{meta, sections[], turns[], exercises{}}`.
2. `app.py` renders modules to HTML server-side. Persisted answers/ratings/quiz
   results are baked into the initial HTML, so **a refresh restores all state**.
3. `static/app.js` handles reveal → self-rate → persist via a small JSON API
   (`/api/answer`, `/api/rating`, `/api/quiz`). No answer is ever auto-graded as
   correct/incorrect except multiple-choice quizzes.
4. `progress.py` writes atomically (temp file + `os.replace`) and is
   corruption-safe (a broken file is backed up, not fatal). Progress lives
   **outside** the source bundle, so rebuilding the app never erases learning.

## Exercise IDs

Deterministic per module in document order: `<module_id>-c1` (card),
`-r1` (respond), `-q1` (quiz). Stable IDs let progress and the error log point
back to a specific exercise.

## Mastery & completion (§16)

Mastery = average of recall self-ratings (got=1.0 / mostly=0.6 / missed=0.0) and
quiz correctness. A module is "mastered" when mastery ≥ 80 **and** every quiz is
answered. Nothing is hard-gated — any lesson opens any time. Personal free-form
answers are never auto-judged.

## Error log (§18) — dedup-safe

Rating an exercise "Missed" appends an error entry keyed by (exercise, prompt).
Re-marking the same item increments `frequency` instead of adding a duplicate
row, and refreshing never re-posts ratings — so the log never duplicates.

## Spaced repetition (§19) — `reviewbank.py`

Completing a conversation schedules its first review at day +1; subsequent
reviews follow `SR_OFFSETS = [1, 3, 7, 14, 30, 60]` days. Each SR stage has a
**recipe** of real questions drawn from that conversation's stored exercises:

| Stage | Recipe |
|------:|--------|
| 0 | 3 recall |
| 1 | 2 recall + 1 production |
| 2 | 1 recall + 2 from another completed conversation in the same theme |
| 3 | 1 production + 1 transfer |
| 4 | recall + production + transfer |
| 5 | transfer + teach-back |

- **Only completed conversations** are reviewed; cross-conversation slots use
  only *other* completed conversations (they degrade to same-conversation recall
  if none exist).
- Within a conversation, candidates are ranked **missed-first**, then
  never-reviewed, then least-recently reviewed.
- A session is **built server-side and persisted** (`review.active`), so a
  refresh returns the same session — never a new one. Computing the due badge
  (`due_summary`) never creates a session.
- Sessions are capped at ~20 questions and a conversation's recipe is never split.
- On completion, each conversation advances one SR stage (holds its stage if any
  of its items were missed) and is rescheduled; the session is archived.

## Content authoring

A conversation module is one `.md` file with YAML frontmatter and sections
`A`–`G` + `Quiz Check` + `Mastery Check`. Custom blocks:

    [[card]]      Q:/A:                         recall (self-rated)
    [[respond]]   Q:/A: (A may be a - list)     production (self-rated)
    [[quiz]]      Q:/ - wrong / * correct       multiple choice (auto-graded)

Run the validator before adding lots of content:

    python -c "import engine; [print(p) for p in engine.validate(engine.Course.load('content'))]"

## The learner's voice (standing content rule)

See `../Korean Conversation Lab — Correction to Learner's Emotional Communication
Style.md`. When the learner is the one responding — dialogue lines for his
character, and every model/personal answer that represents *his* voice — write
him as warm, patient, reassuring, and non-judgmental, not directive.

In any emotionally loaded situation (stress, nerves, insecurity, mistakes,
studying, decisions, trying something new), the learner responds:

> **validate → reframe → encourage**   (not diagnose → instruct → prescribe)

Prefer soft-reflection structures — "I think / maybe / it's understandable /
once… / the more… / it'll probably…" (Korean: -잖아 reassuring, 하다 보면,
-ㄹ 거야 / -ㄹ 것 같아, 원래 ~, 당연히 ~지). Directive forms (해야 돼, 하지 마,
~하는 게 좋아) aren't banned, but must not be what *characterizes* his speech.
`content/everyday/02_new_start.md` is the reference example of this style.

## Status

Phases 0–2 complete: dashboard, one seed conversation, conversation display
modes, recall cards, production exercises (with optional `| English` gloss on
model answers), quiz grading, error log, mastery, atomic refresh-safe
persistence, **and spaced-repetition review** (real questions, due scheduling,
missed-first ranking, refresh-safe sessions, Study-Today priority). 40 tests
passing.

Not yet built (later phases): pattern & vocabulary banks (§22–23),
conversation-reconstruction lesson exercises (§21), speaking/audio mode polish
(§13), Turn-2 / higher-difficulty content, more seed conversations, packaging
(§29).
