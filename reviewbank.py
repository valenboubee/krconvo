"""
reviewbank.py — spaced-repetition review (spec §19).

Principles kept from the reference system:
  * A review session asks REAL questions drawn from stored content, never
    "go review conversation X".
  * Only COMPLETED conversations are reviewed. Cross-conversation questions use
    only other completed conversations.
  * Previously-missed items are ranked first, then never-reviewed, then
    least-recently reviewed.
  * A session is built server-side and persisted, so it survives a refresh and
    is never silently regenerated. Computing the due count never creates one.
  * A conversation's whole review recipe stays in one session (never split).
  * Sessions are capped at ~20 questions.

The module stays UI-free: it returns data; app.py renders it.
"""

from __future__ import annotations

from datetime import date, timedelta

SR_OFFSETS = [1, 3, 7, 14, 30, 60]
SESSION_CAP = 20

# Each stage's recipe is a list of (kind, scope) slots.
#   kind:  recall | production | transfer | teachback
#   scope: same (this conversation) | cross (another completed one, same theme)
RECIPES = {
    0: [("recall", "same"), ("recall", "same"), ("recall", "same")],
    1: [("recall", "same"), ("recall", "same"), ("production", "same")],
    2: [("recall", "same"), ("recall", "cross"), ("recall", "cross")],
    3: [("production", "same"), ("transfer", "same")],
    4: [("recall", "same"), ("production", "same"), ("transfer", "same")],
    5: [("transfer", "same"), ("teachback", "same")],
}
LAST_STAGE = len(SR_OFFSETS) - 1


# --------------------------------------------------------------------------
# Scheduling helpers
# --------------------------------------------------------------------------

def _iso(d: date) -> str:
    return d.isoformat()


def schedule_days(today: date, stage: int) -> str:
    stage = max(0, min(stage, LAST_STAGE))
    return _iso(today + timedelta(days=SR_OFFSETS[stage]))


def on_completed(progress, module_id: str, today: date) -> None:
    """When a conversation is first completed, schedule its first review.
    Idempotent: does nothing if already scheduled."""
    m = progress.module(module_id)
    if m["completed"] and not m["next_review"]:
        progress.set_next_review(module_id, schedule_days(today, 0), sr_index=0)


# --------------------------------------------------------------------------
# Exercise pools + ranking
# --------------------------------------------------------------------------

def _exercises(module, predicate):
    return [ex["id"] for ex in module["exercises"].values() if predicate(ex)]


def get_pool(module, kind: str) -> list[str]:
    """Return candidate exercise ids in `module` for a review kind, with
    graceful fallbacks so a slot is never empty when any material exists."""
    def cards():
        return _exercises(module, lambda e: e["type"] == "card")

    def responds_in(sections):
        return _exercises(module, lambda e: e["type"] == "respond" and e.get("section") in sections)

    def any_respond():
        return _exercises(module, lambda e: e["type"] == "respond")

    if kind == "recall":
        return cards() or responds_in({"C"}) or any_respond()
    if kind == "production":
        return responds_in({"D", "E"}) or any_respond() or cards()
    if kind == "transfer":
        return responds_in({"G"}) or responds_in({"D", "E"}) or any_respond()
    return []


def _is_missed(progress, module_id: str, exercise_id: str) -> bool:
    if progress.get_rating(module_id, exercise_id) == "missed":
        return True
    if progress.review_meta(module_id, exercise_id).get("last_rating") == "missed":
        return True
    return False


def rank_pool(progress, module_id: str, ex_ids: list[str]) -> list[str]:
    """Missed first, then never-reviewed, then least-recently reviewed (§19)."""
    def key(exid):
        meta = progress.review_meta(module_id, exid)
        missed = 0 if _is_missed(progress, module_id, exid) else 1
        never = 0 if meta.get("count", 0) == 0 else 1
        last = meta.get("last", "")  # empty sorts first (least recently)
        return (missed, never, last)
    return sorted(ex_ids, key=key)


# --------------------------------------------------------------------------
# Planning (pure — never persists)
# --------------------------------------------------------------------------

def due_module_ids(course, progress, today: date) -> list[str]:
    """Completed modules whose next_review is on/before today, most overdue
    first. Never returns incomplete modules."""
    today_iso = _iso(today)
    due = []
    for mid, module in course.modules.items():
        mp = progress.module(mid)
        if mp["completed"] and mp["next_review"] and mp["next_review"] <= today_iso:
            due.append((mp["next_review"], mid))
    due.sort()  # earliest next_review (most overdue) first
    return [mid for _, mid in due]


def _completed_ids(course, progress) -> list[str]:
    return [mid for mid, m in course.modules.items() if progress.module(mid)["completed"]]


def _cross_candidate(course, progress, base_id: str):
    """Another completed module sharing a theme with base (fallback: any other
    completed module). Returns a module dict or None."""
    base = course.get(base_id)
    base_themes = set(base["meta"].get("themes") or [])
    others = [mid for mid in _completed_ids(course, progress) if mid != base_id]
    themed = [mid for mid in others if base_themes & set(course.get(mid)["meta"].get("themes") or [])]
    pick = (themed or others)
    return course.get(pick[0]) if pick else None


def _build_items_for_module(course, progress, base_id: str) -> list[dict]:
    """Materialize one module's recipe into concrete review items, avoiding
    repeats within the module where the pool allows."""
    mp = progress.module(base_id)
    stage = mp["sr_index"]
    recipe = RECIPES.get(stage, RECIPES[LAST_STAGE])
    module = course.get(base_id)

    items: list[dict] = []
    used: set[tuple] = set()

    for kind, scope in recipe:
        if kind == "teachback":
            items.append({"module": base_id, "exercise": None, "kind": "teachback"})
            continue

        target_module, target_id = module, base_id
        if scope == "cross":
            cand = _cross_candidate(course, progress, base_id)
            if cand is not None:
                target_module, target_id = cand, cand["id"]
            # else: degrade to same-module recall below

        pool = rank_pool(progress, target_id, get_pool(target_module, kind))
        pick = next((e for e in pool if (target_id, e) not in used), None)
        if pick is None and pool:
            pick = pool[0]  # allow a repeat rather than an empty slot
        if pick is None:
            continue
        used.add((target_id, pick))
        items.append({"module": target_id, "exercise": pick, "kind": kind})

    return items


def plan(course, progress, today: date) -> list[dict]:
    """Ordered list of {base, stage, items} for today's due modules, applying
    the session cap without splitting any module's recipe. Pure: no writes."""
    out = []
    total = 0
    for base_id in due_module_ids(course, progress, today):
        items = _build_items_for_module(course, progress, base_id)
        if not items:
            continue
        if out and total + len(items) > SESSION_CAP:
            break  # keep the cap; leftover modules stay due for the next session
        out.append({"base": base_id, "stage": progress.module(base_id)["sr_index"], "items": items})
        total += len(items)
    return out


def due_summary(course, progress, today: date) -> dict:
    """{'modules': n, 'questions': n} for the due badge — never creates a
    session (spec gate §19)."""
    p = plan(course, progress, today)
    return {"modules": len(p), "questions": sum(len(x["items"]) for x in p)}


# --------------------------------------------------------------------------
# Session lifecycle (persists)
# --------------------------------------------------------------------------

def _review_root(progress) -> dict:
    root = progress.data.setdefault("review", {})
    root.setdefault("sessions", {})
    root.setdefault("active", None)
    return root


def active_session(progress):
    return _review_root(progress).get("active")


def build_session(course, progress, today: date):
    """Return the current active session, creating one from today's plan if
    none exists. Refresh-safe: calling again returns the same session."""
    root = _review_root(progress)
    if root.get("active"):
        return root["active"]

    plan_out = plan(course, progress, today)
    if not plan_out:
        return None

    items = []
    module_stage = {}
    for entry in plan_out:
        module_stage[entry["base"]] = entry["stage"]
        for it in entry["items"]:
            items.append({**it, "rating": ""})

    sid = "rev-" + today.isoformat() + "-" + str(len(root["sessions"]) + 1)
    session = {
        "id": sid,
        "date": today.isoformat(),
        "base_modules": [e["base"] for e in plan_out],
        "module_stage": module_stage,
        "items": items,
    }
    root["active"] = session
    progress.save()
    return session


def record_rating(course, progress, today: date, index: int, rating: str) -> dict:
    """Rate item `index` in the active session. Logs an error on 'missed',
    records the review for ranking, and completes the session when every item
    is rated. Returns {ok, done, remaining, completed}."""
    root = _review_root(progress)
    session = root.get("active")
    if not session:
        return {"ok": False, "error": "no active session"}
    if not (0 <= index < len(session["items"])):
        return {"ok": False, "error": "bad index"}
    if rating not in ("got", "mostly", "missed"):
        return {"ok": False, "error": "bad rating"}

    item = session["items"][index]
    item["rating"] = rating

    exid = item["exercise"]
    mid = item["module"]
    if exid:
        progress.note_review(mid, exid, rating)
        if rating == "missed":
            module = course.get(mid)
            ex = module["exercises"].get(exid) if module else None
            if ex:
                model = ex["a"] if isinstance(ex["a"], str) else " / ".join(ex["a"])
                progress.log_error(mid, {
                    "type": "review",
                    "source": exid,
                    "prompt": ex["q"],
                    "learner_answer": "",
                    "model_answer": model,
                })
    progress.save()

    remaining = sum(1 for it in session["items"] if not it["rating"])
    completed = False
    if remaining == 0:
        _complete(course, progress, today, session)
        completed = True
    return {"ok": True, "done": True, "remaining": remaining, "completed": completed}


def _complete(course, progress, today: date, session: dict) -> None:
    """Advance each base module's SR stage (hold the stage if any of its items
    were missed) and archive the session."""
    for mid in session["base_modules"]:
        stage = session["module_stage"].get(mid, progress.module(mid)["sr_index"])
        missed = any(it["rating"] == "missed" for it in session["items"] if it["module"] == mid)
        new_stage = stage if missed else min(stage + 1, LAST_STAGE)
        progress.set_next_review(mid, schedule_days(today, new_stage), sr_index=new_stage)

    root = _review_root(progress)
    session["completed_on"] = today.isoformat()
    root["sessions"][session["id"]] = session
    root["active"] = None
    progress.save()


def cancel_active(progress) -> None:
    root = _review_root(progress)
    root["active"] = None
    progress.save()
