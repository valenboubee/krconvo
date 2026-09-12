"""
progress.py — local, single-user progress persistence.

Progress lives OUTSIDE the source bundle so rebuilding the app never erases
learning data (spec §28):

    ~/.korean-conversation-lab/progress.json

Writes are atomic (write temp + os.replace) so a crash mid-write can never
corrupt the file. Loads are corruption-safe: a broken file is backed up and a
fresh default structure is returned instead of throwing.

Data model (spec §47), human-readable JSON:

    {
      "modules": {
        "<id>": {
          "completed": false,
          "mastery": 0,
          "sr_index": 0,
          "next_review": null,
          "answers": { "<exercise_id>": {"answer": str, "updated": iso} },
          "ratings": { "<exercise_id>": {"rating": "got|mostly|missed", "updated": iso} },
          "quiz":    { "<exercise_id>": {"choice": int, "correct": bool, "updated": iso} },
          "errors":  [ {error entry}, ... ],
          "opened":  false
        }
      },
      "review": { "sessions": {} }
    }
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

RATINGS = ("got", "mostly", "missed")


def default_progress_dir() -> Path:
    override = os.environ.get("KCL_PROGRESS_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".korean-conversation-lab"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return date.today().isoformat()


def _default_data() -> dict:
    return {"modules": {}, "review": {"sessions": {}}}


def _default_module() -> dict:
    return {
        "completed": False,
        "mastery": 0,
        "sr_index": 0,
        "next_review": None,        # ISO date (YYYY-MM-DD) when this module is next due
        "answers": {},
        "ratings": {},
        "quiz": {},
        "errors": [],
        "opened": False,
        "review_meta": {},          # {exercise_id: {"count", "last", "last_rating"}}
    }


class Progress:
    """Loads/saves the single progress file. One instance per process is fine;
    each mutating call persists atomically so state survives a crash or refresh."""

    def __init__(self, directory: Path | None = None):
        self.dir = Path(directory) if directory else default_progress_dir()
        self.path = self.dir / "progress.json"
        self.data = self._load()

    # ---- load / save -----------------------------------------------------

    def _load(self) -> dict:
        if not self.path.exists():
            return _default_data()
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "modules" not in data:
                raise ValueError("unexpected shape")
            data.setdefault("review", {"sessions": {}})
            data.setdefault("modules", {})
            return data
        except (json.JSONDecodeError, ValueError, OSError):
            # Corrupt file: preserve it for inspection, start clean.
            try:
                backup = self.path.with_suffix(".corrupt.json")
                self.path.replace(backup)
            except OSError:
                pass
            return _default_data()

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".progress-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)  # atomic on same filesystem
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    # ---- module access ---------------------------------------------------

    def module(self, module_id: str) -> dict:
        mods = self.data["modules"]
        if module_id not in mods:
            mods[module_id] = _default_module()
        else:
            # heal older/partial records
            base = _default_module()
            base.update(mods[module_id])
            mods[module_id] = base
        return mods[module_id]

    def mark_opened(self, module_id: str) -> None:
        m = self.module(module_id)
        if not m["opened"]:
            m["opened"] = True
            self.save()

    # ---- spaced-repetition scheduling ------------------------------------

    def set_next_review(self, module_id: str, iso_date, sr_index: int | None = None) -> None:
        m = self.module(module_id)
        m["next_review"] = iso_date
        if sr_index is not None:
            m["sr_index"] = sr_index
        self.save()

    def note_review(self, module_id: str, exercise_id: str, rating: str) -> None:
        """Record that an exercise was reviewed (for missed-first ranking)."""
        m = self.module(module_id)
        meta = m["review_meta"].get(exercise_id, {"count": 0})
        meta["count"] = meta.get("count", 0) + 1
        meta["last"] = _now_iso()
        meta["last_rating"] = rating
        m["review_meta"][exercise_id] = meta
        self.save()

    def review_meta(self, module_id: str, exercise_id: str) -> dict:
        return self.module(module_id)["review_meta"].get(exercise_id, {})

    # ---- answers ---------------------------------------------------------

    def set_answer(self, module_id: str, exercise_id: str, answer: str) -> None:
        m = self.module(module_id)
        m["answers"][exercise_id] = {"answer": answer, "updated": _now_iso()}
        self.save()

    def get_answer(self, module_id: str, exercise_id: str) -> str:
        return self.module(module_id)["answers"].get(exercise_id, {}).get("answer", "")

    # ---- self-ratings ----------------------------------------------------

    def set_rating(self, module_id: str, exercise_id: str, rating: str) -> None:
        rating = rating.lower()
        if rating not in RATINGS:
            raise ValueError(f"invalid rating: {rating!r}")
        m = self.module(module_id)
        m["ratings"][exercise_id] = {"rating": rating, "updated": _now_iso()}
        self.save()

    def get_rating(self, module_id: str, exercise_id: str) -> str:
        return self.module(module_id)["ratings"].get(exercise_id, {}).get("rating", "")

    # ---- quiz ------------------------------------------------------------

    def set_quiz(self, module_id: str, exercise_id: str, choice: int, correct: bool) -> None:
        m = self.module(module_id)
        m["quiz"][exercise_id] = {"choice": choice, "correct": bool(correct), "updated": _now_iso()}
        self.save()

    def get_quiz(self, module_id: str, exercise_id: str) -> dict:
        return self.module(module_id)["quiz"].get(exercise_id, {})

    # ---- error log (dedup-safe; spec §17, §18) ---------------------------

    def log_error(self, module_id: str, entry: dict) -> None:
        """Append or increment an error-log entry. Re-marking the same exercise
        missed increments frequency instead of creating a duplicate row, so
        replaying persisted ratings after a refresh never duplicates entries."""
        m = self.module(module_id)
        key_source = entry.get("source")
        key_prompt = entry.get("prompt")
        for e in m["errors"]:
            if e.get("source") == key_source and e.get("prompt") == key_prompt:
                e["frequency"] = e.get("frequency", 1) + 1
                e["updated"] = _now_iso()
                # keep newest learner/model answer + note
                for field in ("learner_answer", "model_answer", "type"):
                    if entry.get(field):
                        e[field] = entry[field]
                self.save()
                return
        entry = dict(entry)
        entry.setdefault("frequency", 1)
        entry.setdefault("note", "")
        entry["updated"] = _now_iso()
        m["errors"].append(entry)
        self.save()

    def clear_error_if_recovered(self, module_id: str, source: str, prompt: str) -> None:
        """When a previously-missed item is later rated got/mostly, we leave the
        error row (it is still useful history) but this hook exists for callers
        that want to prune. Currently a no-op placeholder for future tuning."""
        return

    def add_error_note(self, module_id: str, index: int, note: str) -> None:
        m = self.module(module_id)
        if 0 <= index < len(m["errors"]):
            m["errors"][index]["note"] = note
            self.save()

    def all_errors(self) -> list[dict]:
        rows = []
        for mid, m in self.data["modules"].items():
            for e in m.get("errors", []):
                row = dict(e)
                row["module_id"] = mid
                rows.append(row)
        rows.sort(key=lambda r: (-r.get("frequency", 1), r.get("updated", "")))
        return rows

    # ---- mastery ---------------------------------------------------------

    def recompute_mastery(self, module_id: str, exercise_ids: dict) -> int:
        """Mastery combines recall self-ratings + quiz correctness (spec §16).
        exercise_ids: {"recall": [...], "quiz": [...]}. Personal free-form
        answers are NOT scored for correctness."""
        m = self.module(module_id)

        recall_ids = exercise_ids.get("recall", [])
        quiz_ids = exercise_ids.get("quiz", [])

        recall_score = None
        if recall_ids:
            weights = {"got": 1.0, "mostly": 0.6, "missed": 0.0}
            got = [weights.get(m["ratings"].get(i, {}).get("rating", ""), 0.0)
                   for i in recall_ids if i in m["ratings"]]
            recall_score = (sum(got) / len(recall_ids)) if recall_ids else None

        quiz_score = None
        if quiz_ids:
            correct = sum(1 for i in quiz_ids if m["quiz"].get(i, {}).get("correct"))
            answered = sum(1 for i in quiz_ids if i in m["quiz"])
            quiz_score = (correct / len(quiz_ids)) if answered else 0.0

        parts = [p for p in (recall_score, quiz_score) if p is not None]
        mastery = round(100 * sum(parts) / len(parts)) if parts else 0
        m["mastery"] = mastery
        self.save()
        return mastery
