# Korean Conversation Lab

An offline, single-user Korean study app built around **fixed conversations** —
not a chatbot. You study realistic dialogues, retrieve Korean from memory,
produce it, compare against stored model answers, and revisit what you miss.

No accounts. No internet. No AI at study time. Your answers stay on your computer.

## Run it

```bash
python app.py
```

Then open <http://127.0.0.1:5050> (it opens automatically). Press `Ctrl+C` to stop.

Requires Python 3 (tested on 3.14). No packages to install.

### Run it on another machine, or host it online

Clone the repo anywhere and `python app.py` — that's the whole install. The server
also reads `$PORT` (binds `0.0.0.0` when set) and `KCL_PROGRESS_DIR` (where to keep
progress), so it drops onto a host with a persistent disk without code changes.
See [DEPLOY.md](DEPLOY.md) for web hosting — including a **free** Render deploy
that works on phone/laptop/tablet — and why Vercel doesn't fit.

## What works now (Phases 0–2)

- **Dashboard** with your progress and a **Study Today** entry point that
  prioritizes reviews that are due.
- One seed conversation (`content/everyday/01_plans.md`) with all sections A–G.
- **Conversation modes:** Korean + English · Korean only · Cover (tap to reveal).
- **Recall cards** and **production exercises** — try first, reveal, self-rate.
  Personal model answers include an English translation.
- **Quizzes** with instant grading.
- **Spaced repetition** — finish a conversation and it comes back as *real
  review questions* on a 1/3/7/14/30/60-day schedule. Missed items come first;
  sessions survive a refresh.
- **Error log** — anything you rate "Missed" lands here to revisit.
- **Mastery** score and refresh-safe progress saved to
  `~/.korean-conversation-lab/progress.json` (never erased when you rebuild).

## Test it

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Add your own conversation

Copy an existing file in `content/`, keep the frontmatter fields and the
`A`–`G` + `Quiz Check` + `Mastery Check` sections, then validate:

```bash
python -c "import engine; [print(p) for p in engine.validate(engine.Course.load('content'))] or print('ok')"
```

See `docs/DESIGN.md` for architecture and `docs/SOURCES.md` for the content rules.
