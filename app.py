#!/usr/bin/env python3
"""
app.py — Korean Conversation Lab (offline, single-user, stdlib only).

Run:

    python app.py

Serves a local study app at http://127.0.0.1:5050 and opens a browser.
No accounts, no network calls, no AI. All content is local Markdown; all
progress is a local JSON file that survives rebuilds (see progress.py).
"""

from __future__ import annotations

import html
import json
import os
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import engine
import reviewbank
from progress import Progress


def today() -> date:
    return date.today()

# Hosting platforms (Render, Railway, Fly, etc.) inject $PORT and expect the
# server to bind 0.0.0.0. Locally we stay on 127.0.0.1:5050 and open a browser.
ON_SERVER = bool(os.environ.get("PORT"))
PORT = int(os.environ.get("PORT") or os.environ.get("KCL_PORT") or 5050)
HOST = os.environ.get("KCL_HOST") or ("0.0.0.0" if ON_SERVER else "127.0.0.1")
MASTERY_THRESHOLD = 80

BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "content"
STATIC_DIR = BASE_DIR / "static"

# Loaded once at startup; progress mutations are serialized with a lock.
COURSE = engine.Course.load(CONTENT_DIR)
PROGRESS = Progress()
LOCK = threading.Lock()


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


# --------------------------------------------------------------------------
# Page shell
# --------------------------------------------------------------------------

def page(title: str, body: str, active: str = "") -> str:
    def nav_link(href, label, key):
        cls = ' class="active"' if key == active else ""
        return f'<a href="{href}"{cls}>{label}</a>'

    due = reviewbank.due_summary(COURSE, PROGRESS, today())
    review_label = "Review"
    if due["questions"]:
        review_label = f'Review <span class="badge">{due["questions"]}</span>'
    nav = "".join([
        nav_link("/", "Dashboard", "dashboard"),
        nav_link("/review", review_label, "review"),
        nav_link("/errors", "Error Log", "errors"),
    ])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Korean Conversation Lab</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="topbar">
  <a class="brand" href="/">한국어 <span>Conversation Lab</span></a>
  <nav>{nav}</nav>
</header>
<main>
{body}
</main>
<footer class="foot">Offline personal study · no AI · no accounts · your answers stay on this computer</footer>
<script src="/static/app.js"></script>
</body>
</html>"""


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

PHASE_NAMES = {
    1: "Everyday Korean",
    2: "People & relationships",
    3: "Experiences & stories",
    4: "Feelings & opinions",
    5: "Work, study & health",
    6: "Intermediate everyday",
}


def render_dashboard() -> str:
    ordered = COURSE.ordered()
    total = len(ordered)
    completed = sum(1 for m in ordered if PROGRESS.module(m["id"])["completed"])

    # recommended = first not-completed module in order
    recommended = next((m for m in ordered if not PROGRESS.module(m["id"])["completed"]), None)

    cards = []
    by_phase = COURSE.by_phase()
    for phase in sorted(by_phase):
        pname = PHASE_NAMES.get(phase, f"Phase {phase}")
        rows = []
        for m in by_phase[phase]:
            mp = PROGRESS.module(m["id"])
            status = "MASTERED" if mp["completed"] else ("IN PROGRESS" if mp["opened"] else "NEW")
            status_cls = status.lower().replace(" ", "-")
            diff = m["meta"].get("difficulty", "?")
            mastery = mp["mastery"]
            rows.append(f"""
        <a class="lesson-row" href="/lesson/{esc(m['id'])}">
          <span class="lesson-title">{esc(m['meta'].get('title', m['id']))}</span>
          <span class="lesson-meta">
            <span class="pill diff">difficulty {esc(diff)}</span>
            <span class="pill mastery">{mastery}%</span>
            <span class="status {status_cls}">{status}</span>
          </span>
        </a>""")
        cards.append(f"""
    <section class="phase">
      <h3>Phase {phase} · {esc(pname)}</h3>
      <div class="lesson-list">{''.join(rows)}</div>
    </section>""")

    due = reviewbank.due_summary(COURSE, PROGRESS, today())

    # Study Today priority (§26): overdue spaced repetition, then a due new conversation.
    if due["questions"]:
        q = due["questions"]
        study_btn = f'<a class="cta" href="/review">▶ STUDY TODAY — Review ({q} question{"s" if q != 1 else ""})</a>'
    elif recommended:
        study_btn = f'<a class="cta" href="/lesson/{esc(recommended["id"])}">▶ STUDY TODAY — {esc(recommended["meta"].get("title", recommended["id"]))}</a>'
    else:
        study_btn = '<p class="muted">All caught up. Add more content in <code>content/</code>.</p>'

    review_line = ""
    if due["questions"]:
        review_line = f'<p class="muted">{due["questions"]} review question{"s" if due["questions"] != 1 else ""} due across {due["modules"]} conversation{"s" if due["modules"] != 1 else ""}.</p>'

    header = f"""
    <div class="dash-head">
      <div>
        <h1>Today's study</h1>
        <p class="muted">{completed} of {total} conversations mastered.</p>
        {review_line}
      </div>
      {study_btn}
    </div>"""

    return header + "".join(cards)


# --------------------------------------------------------------------------
# Lesson rendering
# --------------------------------------------------------------------------

def render_conversation(turns) -> str:
    rows = []
    for t in turns:
        rows.append(f"""
      <div class="turn">
        <div class="speaker">{esc(t['speaker'])}</div>
        <div class="lines">
          <div class="ko">{esc(t['korean'])}</div>
          <div class="en">{esc(t['english'])}</div>
        </div>
      </div>""")
    return f"""
    <div class="conversation-block">
      <div class="mode-controls" role="tablist">
        <button type="button" class="mode-btn active" data-mode="both">Korean + English</button>
        <button type="button" class="mode-btn" data-mode="ko">Korean only</button>
        <button type="button" class="mode-btn" data-mode="cover">Cover (tap a line to reveal)</button>
      </div>
      <div class="conversation mode-both">{''.join(rows)}</div>
    </div>"""


def _rating_controls(module_id, ex, current) -> str:
    def btn(val, label):
        cls = "rate-btn" + (" chosen" if current == val else "")
        return f'<button type="button" class="{cls}" data-rate="{val}">{label}</button>'
    prompt = ex["q"]
    model = ex["a"] if isinstance(ex["a"], str) else " / ".join(ex["a"])
    return f"""
        <div class="rating" data-module="{esc(module_id)}" data-exercise="{esc(ex['id'])}"
             data-prompt="{esc(prompt)}" data-model="{esc(model)}">
          <span class="rate-label">Self-rate:</span>
          {btn('got', 'Got it')}
          {btn('mostly', 'Mostly')}
          {btn('missed', 'Missed')}
        </div>"""


def render_card(module_id, ex) -> str:
    rating = PROGRESS.get_rating(module_id, ex["id"])
    revealed = "revealed" if rating else ""
    return f"""
    <div class="exercise card {revealed}" data-type="card">
      <div class="tag">RECALL</div>
      <div class="prompt">{esc(ex['q'])}</div>
      <div class="answer">
        <div class="answer-label">Answer</div>
        <div class="answer-body">{esc(ex['a'])}</div>
        {f'<div class="answer-en">{esc(ex.get("a_en"))}</div>' if ex.get("a_en") else ''}
      </div>
      <button type="button" class="reveal-btn">Reveal answer</button>
      {_rating_controls(module_id, ex, rating)}
    </div>"""


def render_respond(module_id, ex) -> str:
    rating = PROGRESS.get_rating(module_id, ex["id"])
    saved = PROGRESS.get_answer(module_id, ex["id"])
    revealed = "revealed" if (rating or saved) else ""
    answers = ex["a"] if isinstance(ex["a"], list) else [ex["a"]]
    trans = ex.get("a_en") or []
    label = "Model answers (any is fine)" if len(answers) > 1 else "Model answer"

    def model_item(i, a):
        t = trans[i] if i < len(trans) else ""
        en = f"<div class='answer-en'>{esc(t)}</div>" if t else ""
        return f"<div class='model-item'><div class='answer-body'>{esc(a)}</div>{en}</div>"

    model_html = "".join(model_item(i, a) for i, a in enumerate(answers))
    return f"""
    <div class="exercise respond {revealed}" data-type="respond"
         data-module="{esc(module_id)}" data-exercise="{esc(ex['id'])}">
      <div class="tag">PRACTICE</div>
      <div class="prompt">{esc(ex['q'])}</div>
      <textarea class="answer-input" rows="2" placeholder="Type your Korean here...">{esc(saved)}</textarea>
      <div class="answer">
        <div class="answer-label">{label}</div>
        {model_html}
        <p class="compare-note">Compare: did you get the idea across? What phrase could you borrow? A personal answer is never "wrong" for differing from the model.</p>
      </div>
      <button type="button" class="reveal-btn">Reveal model answer</button>
      {_rating_controls(module_id, ex, rating)}
    </div>"""


def render_quiz(module_id, ex) -> str:
    saved = PROGRESS.get_quiz(module_id, ex["id"])
    chosen = saved.get("choice")
    answered = "choice" in saved
    opts = []
    for idx, o in enumerate(ex["options"]):
        state = ""
        if answered:
            if o["correct"]:
                state = "correct"
            elif idx == chosen:
                state = "wrong"
        opts.append(f"""
        <button type="button" class="quiz-opt {state}" data-idx="{idx}"
                data-correct="{'1' if o['correct'] else '0'}">{esc(o['text'])}</button>""")
    feedback = ""
    if answered:
        feedback = ('<div class="quiz-feedback good">Correct</div>' if saved.get("correct")
                    else '<div class="quiz-feedback bad">Not quite — the correct answer is highlighted.</div>')
    done_cls = "answered" if answered else ""
    return f"""
    <div class="exercise quiz {done_cls}" data-type="quiz"
         data-module="{esc(module_id)}" data-exercise="{esc(ex['id'])}">
      <div class="tag">QUIZ</div>
      <div class="prompt">{esc(ex['q'])}</div>
      <div class="quiz-options">{''.join(opts)}</div>
      {feedback}
    </div>"""


def render_element(module_id, el) -> str:
    t = el["type"]
    if t == "md":
        return f'<div class="prose">{el["html"]}</div>'
    if t == "conversation":
        return render_conversation(el["turns"])
    if t == "card":
        return render_card(module_id, el)
    if t == "respond":
        return render_respond(module_id, el)
    if t == "quiz":
        return render_quiz(module_id, el)
    return ""


def render_lesson(module) -> str:
    mid = module["id"]
    meta = module["meta"]
    mp = PROGRESS.module(mid)

    sections_html = []
    for sec in module["sections"]:
        els = "".join(render_element(mid, el) for el in sec["elements"])
        title = esc(sec["title"]) if sec["title"] else ""
        head = f"<h2>{title}</h2>" if title else ""
        sections_html.append(f'<section class="lesson-section">{head}{els}</section>')

    tags = []
    if meta.get("speech_level"):
        tags.append(f'<span class="pill">{esc(meta["speech_level"])} speech</span>')
    if meta.get("relationship"):
        tags.append(f'<span class="pill">{esc(str(meta["relationship"]).replace("_"," "))}</span>')
    tags.append(f'<span class="pill diff">difficulty {esc(meta.get("difficulty","?"))}</span>')
    tags.append(f'<span class="pill mastery" id="mastery-pill">{mp["mastery"]}% mastery</span>')

    header = f"""
    <div class="lesson-head" data-module="{esc(mid)}">
      <a class="back" href="/">← Dashboard</a>
      <h1>{esc(meta.get('title', mid))}</h1>
      <div class="lesson-tags">{''.join(tags)}</div>
    </div>"""

    return header + "".join(sections_html)


# --------------------------------------------------------------------------
# Review session
# --------------------------------------------------------------------------

def _answer_html(ex) -> str:
    """Inner model-answer HTML (Korean primary, optional English gloss)."""
    if ex["type"] == "card":
        en = f'<div class="answer-en">{esc(ex.get("a_en"))}</div>' if ex.get("a_en") else ""
        return f'<div class="answer-label">Answer</div><div class="answer-body">{esc(ex["a"])}</div>{en}'
    answers = ex["a"] if isinstance(ex["a"], list) else [ex["a"]]
    trans = ex.get("a_en") or []
    label = "Model answers (any is fine)" if len(answers) > 1 else "Model answer"

    def one(i, a):
        t = trans[i] if i < len(trans) else ""
        en = f'<div class="answer-en">{esc(t)}</div>' if t else ""
        return f'<div class="model-item"><div class="answer-body">{esc(a)}</div>{en}</div>'

    body = "".join(one(i, a) for i, a in enumerate(answers))
    return f'<div class="answer-label">{label}</div>{body}'


KIND_TAG = {"recall": "RECALL", "production": "PRODUCE", "transfer": "TRANSFER", "teachback": "TEACH-BACK"}


def _teachback_reveal(module) -> str:
    context = ""
    for sec in module["sections"]:
        if sec["title"].startswith("A"):
            context = "".join(el.get("html", "") for el in sec["elements"] if el["type"] == "md")
            break
    vocab = module["meta"].get("vocabulary") or []
    vocab_html = ""
    if vocab:
        vocab_html = "<div class='answer-label'>Key words to weave in</div><ul>" + \
            "".join(f"<li>{esc(v)}</li>" for v in vocab) + "</ul>"
    return f"<div class='answer-label'>What this conversation was about</div>{context}{vocab_html}"


def render_review_item(index, item) -> str:
    mid = item["module"]
    module = COURSE.get(mid)
    rating = item.get("rating", "")
    revealed = "revealed" if rating else ""
    tag = KIND_TAG.get(item["kind"], "REVIEW")
    src = module["meta"].get("title", mid) if module else mid

    if item["kind"] == "teachback":
        prompt = "Without looking back, explain in English what this conversation was about — then say two Korean sentences you still remember."
        answer_inner = _teachback_reveal(module) if module else ""
        reveal_label = "Reveal checklist"
        needs_input = False
        ex_for_input = None
    else:
        ex = module["exercises"].get(item["exercise"]) if module else None
        if not ex:
            return ""
        prompt = ex["q"]
        answer_inner = _answer_html(ex)
        reveal_label = "Reveal answer" if ex["type"] == "card" else "Reveal model answer"
        needs_input = ex["type"] != "card"
        ex_for_input = ex

    input_html = ""
    if needs_input:
        input_html = '<textarea class="answer-input" rows="2" placeholder="Type your Korean here..."></textarea>'

    def rbtn(val, label):
        cls = "rate-btn" + (" chosen" if rating == val else "")
        return f'<button type="button" class="{cls}" data-rate="{val}">{label}</button>'

    return f"""
    <div class="exercise review-item {revealed}" data-index="{index}">
      <div class="tag">{tag} · <span class="review-src">from {esc(src)}</span></div>
      <div class="prompt">{esc(prompt)}</div>
      {input_html}
      <div class="answer">{answer_inner}</div>
      <button type="button" class="reveal-btn">{esc(reveal_label)}</button>
      <div class="rating review-rating" data-index="{index}">
        <span class="rate-label">Self-rate:</span>
        {rbtn('got', 'Got it')}{rbtn('mostly', 'Mostly')}{rbtn('missed', 'Missed')}
      </div>
    </div>"""


def render_review() -> str:
    with LOCK:
        session = reviewbank.build_session(COURSE, PROGRESS, today())
    if not session:
        return """
    <h1>Review</h1>
    <div class="review-empty">
      <p>Nothing is due right now. Reviews appear here after you complete a conversation, on a spaced schedule (1, 3, 7, 14, 30, 60 days).</p>
      <a class="cta" href="/">← Back to dashboard</a>
    </div>"""

    total = len(session["items"])
    answered = sum(1 for it in session["items"] if it["rating"])
    items_html = "".join(render_review_item(i, it) for i, it in enumerate(session["items"]))
    all_done = answered == total
    complete_cls = "" if not all_done else " done"
    return f"""
    <div class="review-head">
      <h1>Review session</h1>
      <p class="muted">Real questions from conversations you've completed. Try first, then reveal and self-rate.</p>
      <div class="review-progress"><span id="review-count">{answered}</span> / {total} answered</div>
    </div>
    <div class="review-list">{items_html}</div>
    <div class="review-complete{complete_cls}" id="review-complete">
      <p>Session complete — nicely done. Your next reviews are rescheduled automatically.</p>
      <a class="cta" href="/">← Back to dashboard</a>
    </div>"""


# --------------------------------------------------------------------------
# Error log
# --------------------------------------------------------------------------

def render_errors() -> str:
    rows = PROGRESS.all_errors()
    if not rows:
        return """
    <h1>Error Log</h1>
    <p class="muted">Nothing logged yet. When you rate an exercise "Missed", it lands here so you can revisit it.</p>"""
    items = []
    for r in rows:
        mid = r.get("module_id", "")
        module = COURSE.get(mid)
        title = module["meta"].get("title", mid) if module else mid
        items.append(f"""
      <div class="error-row">
        <div class="error-top">
          <span class="pill">{esc(r.get('type','conversation'))}</span>
          <span class="freq">missed ×{esc(r.get('frequency',1))}</span>
          <a class="revisit" href="/lesson/{esc(mid)}">Revisit → {esc(title)}</a>
        </div>
        <div class="error-prompt">{esc(r.get('prompt',''))}</div>
        <div class="error-answers">
          <div><span class="mini-label">Your answer</span> {esc(r.get('learner_answer','') or '—')}</div>
          <div><span class="mini-label">Model</span> {esc(r.get('model_answer','') or '—')}</div>
        </div>
        {(f'<div class="error-note">Note: {esc(r["note"])}</div>' if r.get('note') else '')}
      </div>""")
    return f'<h1>Error Log</h1><div class="error-list">{"".join(items)}</div>'


# --------------------------------------------------------------------------
# Completion / mastery helper
# --------------------------------------------------------------------------

def _refresh_mastery(module) -> dict:
    mid = module["id"]
    recall = engine.Course.recall_ids(module)
    quiz = engine.Course.quiz_ids(module)
    mastery = PROGRESS.recompute_mastery(mid, {"recall": recall, "quiz": quiz})
    mp = PROGRESS.module(mid)
    quiz_all_answered = all(qid in mp["quiz"] for qid in quiz) if quiz else True
    completed = mastery >= MASTERY_THRESHOLD and quiz_all_answered
    if mp["completed"] != completed:
        mp["completed"] = completed
        PROGRESS.save()
    if completed:
        # first completion schedules the first spaced-repetition review (idempotent)
        reviewbank.on_completed(PROGRESS, mid, today())
    return {"mastery": mastery, "completed": completed}


# --------------------------------------------------------------------------
# HTTP handler
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "KCL/0.1"

    def log_message(self, *args):  # keep the console quiet
        pass

    # ---- helpers ----
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def _serve_static(self, rel):
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            return self._send(404, "not found", "text/plain")
        ctype = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
        }.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    # ---- GET ----
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            return self._send(200, page("Dashboard", render_dashboard(), "dashboard"))

        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/"):])

        if path == "/review":
            return self._send(200, page("Review", render_review(), "review"))

        if path == "/errors":
            return self._send(200, page("Error Log", render_errors(), "errors"))

        if path.startswith("/lesson/"):
            mid = path[len("/lesson/"):]
            module = COURSE.get(mid)
            if not module:
                return self._send(404, page("Not found", "<h1>Conversation not found</h1><a href='/'>← Dashboard</a>"))
            with LOCK:
                PROGRESS.mark_opened(mid)
            return self._send(200, page(module["meta"].get("title", mid), render_lesson(module), ""))

        return self._send(404, page("Not found", "<h1>404</h1><a href='/'>← Dashboard</a>"))

    def do_HEAD(self):
        self.do_GET()

    # ---- POST (JSON API) ----
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or "{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"ok": False, "error": "bad json"})

        with LOCK:
            if path == "/api/answer":
                return self._api_answer(payload)
            if path == "/api/rating":
                return self._api_rating(payload)
            if path == "/api/quiz":
                return self._api_quiz(payload)
            if path == "/api/review-rate":
                return self._api_review_rate(payload)
        return self._json(404, {"ok": False, "error": "unknown endpoint"})

    # ---- API impls (called under LOCK) ----
    def _api_answer(self, p):
        mid, ex = p.get("module"), p.get("exercise")
        if not COURSE.get(mid):
            return self._json(404, {"ok": False, "error": "no module"})
        PROGRESS.set_answer(mid, ex, p.get("answer", ""))
        return self._json(200, {"ok": True})

    def _api_rating(self, p):
        mid, ex, rating = p.get("module"), p.get("exercise"), p.get("rating", "")
        module = COURSE.get(mid)
        if not module:
            return self._json(404, {"ok": False, "error": "no module"})
        try:
            PROGRESS.set_rating(mid, ex, rating)
        except ValueError as e:
            return self._json(400, {"ok": False, "error": str(e)})

        # Log an error entry only on "missed". log_error dedups by (source, prompt),
        # so revisiting / replaying never creates duplicate rows.
        if rating == "missed":
            PROGRESS.log_error(mid, {
                "type": p.get("kind", "production"),
                "source": ex,
                "prompt": p.get("prompt", ""),
                "learner_answer": p.get("answer", ""),
                "model_answer": p.get("model", ""),
            })

        res = _refresh_mastery(module)
        return self._json(200, {"ok": True, **res})

    def _api_quiz(self, p):
        mid, ex, choice = p.get("module"), p.get("exercise"), p.get("choice")
        module = COURSE.get(mid)
        if not module:
            return self._json(404, {"ok": False, "error": "no module"})
        qex = module["exercises"].get(ex)
        if not qex or qex["type"] != "quiz":
            return self._json(404, {"ok": False, "error": "no quiz"})
        try:
            choice = int(choice)
        except (TypeError, ValueError):
            return self._json(400, {"ok": False, "error": "bad choice"})
        correct = 0 <= choice < len(qex["options"]) and qex["options"][choice]["correct"]
        PROGRESS.set_quiz(mid, ex, choice, correct)
        res = _refresh_mastery(module)
        return self._json(200, {"ok": True, "correct": bool(correct), "answer": qex["answer"], **res})

    def _api_review_rate(self, p):
        try:
            index = int(p.get("index"))
        except (TypeError, ValueError):
            return self._json(400, {"ok": False, "error": "bad index"})
        res = reviewbank.record_rating(COURSE, PROGRESS, today(), index, p.get("rating", ""))
        code = 200 if res.get("ok") else 400
        return self._json(code, res)


def main():
    problems = engine.validate(COURSE)
    if problems:
        print("Content validation problems:")
        for p in problems:
            print("  -", p)
    print(f"Loaded {len(COURSE.modules)} conversation(s) from {CONTENT_DIR}")
    print(f"Progress file: {PROGRESS.path}")

    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    local_url = f"http://127.0.0.1:{PORT}/"
    print(f"Korean Conversation Lab listening on {HOST}:{PORT}")
    if not ON_SERVER:
        print(f"Open {local_url}")
    print("Press Ctrl+C to stop.")
    if not ON_SERVER and "--no-browser" not in sys.argv:
        def _open():
            try:
                webbrowser.open(local_url)
            except Exception:
                pass
        threading.Timer(0.6, _open).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
