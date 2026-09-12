/* Korean Conversation Lab — client interactions.
   Reveal-before-answer, self-rating, quiz grading, answer persistence, and
   conversation display modes. All state persists server-side, so a refresh
   restores everything and never duplicates error-log entries. */

(function () {
  "use strict";

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); }).catch(function () { return { ok: false }; });
  }

  function setMastery(res) {
    if (res && typeof res.mastery === "number") {
      var pill = document.getElementById("mastery-pill");
      if (pill) pill.textContent = res.mastery + "% mastery";
    }
  }

  // ---- Reveal buttons ----
  document.querySelectorAll(".reveal-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      btn.closest(".exercise").classList.add("revealed");
    });
  });

  // ---- Self-rating (cards + responds) ----
  document.querySelectorAll(".rating:not(.review-rating)").forEach(function (rating) {
    var exercise = rating.closest(".exercise");
    rating.querySelectorAll(".rate-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var val = btn.getAttribute("data-rate");
        rating.querySelectorAll(".rate-btn").forEach(function (b) { b.classList.remove("chosen"); });
        btn.classList.add("chosen");

        var input = exercise.querySelector(".answer-input");
        post("/api/rating", {
          module: rating.getAttribute("data-module"),
          exercise: rating.getAttribute("data-exercise"),
          rating: val,
          kind: exercise.getAttribute("data-type") === "card" ? "comprehension" : "production",
          prompt: rating.getAttribute("data-prompt"),
          model: rating.getAttribute("data-model"),
          answer: input ? input.value : "",
        }).then(setMastery);
      });
    });
  });

  // ---- Persist typed answers (respond) on blur ----
  document.querySelectorAll(".exercise.respond").forEach(function (ex) {
    var input = ex.querySelector(".answer-input");
    if (!input) return;
    input.addEventListener("blur", function () {
      var val = input.value.trim();
      if (val === input.getAttribute("data-last")) return;
      input.setAttribute("data-last", val);
      post("/api/answer", {
        module: ex.getAttribute("data-module"),
        exercise: ex.getAttribute("data-exercise"),
        answer: val,
      });
    });
  });

  // ---- Quiz ----
  document.querySelectorAll(".exercise.quiz").forEach(function (quiz) {
    if (quiz.classList.contains("answered")) return;
    quiz.querySelectorAll(".quiz-opt").forEach(function (opt) {
      opt.addEventListener("click", function () {
        if (quiz.classList.contains("answered")) return;
        var idx = parseInt(opt.getAttribute("data-idx"), 10);
        post("/api/quiz", {
          module: quiz.getAttribute("data-module"),
          exercise: quiz.getAttribute("data-exercise"),
          choice: idx,
        }).then(function (res) {
          quiz.classList.add("answered");
          var opts = quiz.querySelectorAll(".quiz-opt");
          opts.forEach(function (o, i) {
            if (o.getAttribute("data-correct") === "1") o.classList.add("correct");
            else if (i === idx) o.classList.add("wrong");
          });
          var fb = document.createElement("div");
          fb.className = "quiz-feedback " + (res.correct ? "good" : "bad");
          fb.textContent = res.correct ? "Correct" : "Not quite — the correct answer is highlighted.";
          quiz.appendChild(fb);
          setMastery(res);
        });
      });
    });
  });

  // ---- Review session ratings ----
  function updateReviewProgress() {
    var items = document.querySelectorAll(".review-item");
    var done = [].filter.call(items, function (i) { return i.querySelector(".rate-btn.chosen"); }).length;
    var c = document.getElementById("review-count");
    if (c) c.textContent = done;
  }
  document.querySelectorAll(".review-rating").forEach(function (rating) {
    rating.querySelectorAll(".rate-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var val = btn.getAttribute("data-rate");
        rating.querySelectorAll(".rate-btn").forEach(function (b) { b.classList.remove("chosen"); });
        btn.classList.add("chosen");
        post("/api/review-rate", {
          index: parseInt(rating.getAttribute("data-index"), 10),
          rating: val,
        }).then(function (res) {
          updateReviewProgress();
          if (res && res.completed) {
            var done = document.getElementById("review-complete");
            if (done) { done.classList.add("done"); done.scrollIntoView({ behavior: "smooth" }); }
          }
        });
      });
    });
  });

  // ---- Conversation display modes ----
  document.querySelectorAll(".conversation-block").forEach(function (block) {
    var convo = block.querySelector(".conversation");
    var buttons = block.querySelectorAll(".mode-btn");
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-mode");
        buttons.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        convo.className = "conversation mode-" + mode;
        // reset any per-line reveals when leaving cover mode
        convo.querySelectorAll(".lines.revealed").forEach(function (l) { l.classList.remove("revealed"); });
      });
    });
    // cover mode: tap a line to reveal just that line
    convo.querySelectorAll(".lines").forEach(function (lines) {
      lines.addEventListener("click", function () {
        if (convo.classList.contains("mode-cover")) lines.classList.toggle("revealed");
      });
    });
  });
})();
