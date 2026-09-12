# KOREAN CONVERSATION LAB — Build Specification for an Offline Personal Korean Learning App

## 0. Agent mission

You are an AI software engineer and learning-system designer building an **offline, single-user Korean study application** for one learner.

The application is a small local web app written in Python. It runs entirely on the learner's computer, stores progress locally, uses no accounts, and does not require an AI service or an internet connection at runtime.

The purpose of the application is **not** to simulate a Korean conversation partner.

The learner does NOT want an open-ended chatbot.

The learner wants to study **pre-written, fixed conversations** and use those conversations as the central material for learning Korean. The system should make the learner actively retrieve, produce, compare, and reuse Korean rather than passively read explanations.

The core goal is:

> Take a learner who can understand basic real-life Korean conversations but struggles with intermediate conversations, and systematically move them toward comfortable understanding and production of everyday/intermediate Korean through repeated study of realistic fixed dialogues.

The learner is especially interested in Korean used in real life with a native-speaking girlfriend. Useful subject matter includes:

- daily life
- plans and schedules
- food
- restaurants and cafés
- going out
- errands
- family
- personal feelings
- opinions and ways of thinking
- relationships
- memories and past stories
- work and career
- health
- medicine and healthcare
- hobbies
- travel
- explaining reasons
- agreeing/disagreeing
- telling stories
- asking follow-up questions
- describing experiences
- talking about future plans
- casual conversation between people who know each other well

The learner finds traditional grammar-book study boring. Grammar is still important, but it should be **discovered inside conversations and practiced because the learner needs it**, not presented as the main curriculum.

The learner also experiences shyness when speaking a language they are still learning. The system should deliberately create low-stakes situations where they must produce Korean, make imperfect attempts, and then compare against a fixed correct/model answer.

The system must therefore optimize for:

1. comprehension of real conversations
2. useful vocabulary
3. grammar in context
4. Korean sentence patterns
5. active recall
6. written production
7. speaking/shadowing practice
8. answering questions in Korean
9. paraphrasing and expressing the same idea differently
10. gradually increasing conversation difficulty
11. spaced repetition
12. confidence through repeated successful retrieval
13. transfer from studied dialogue to new but realistic situations

Do NOT optimize for:
- memorizing isolated word lists
- completing a grammar textbook
- chatbots
- AI-generated conversation during study
- gamification for its own sake
- career/job readiness
- portfolios/projects unrelated to language
- unnecessarily complex software architecture

The system should feel like a **personal conversation-based Korean course**, not like a generic language-learning SaaS application.

---

# 1. Learner profile

Use this configuration as the initial learner profile.

```yaml
app_name: "Korean Conversation Lab"
exe_name: "KoreanConversationLab"

runtime:
  offline: true
  single_user: true
  local_only: true
  default_port: 5050
  progress_dir: "~/.korean-conversation-lab"

learner:
  native_language: "English"
  target_language: "Korean"

  current_level:
    approximate: "upper-beginner / approaching intermediate"
    can_understand:
      - basic Korean conversations
      - common everyday vocabulary
      - beginner-level sentence patterns
    struggles_with:
      - intermediate conversations
      - longer natural sentences
      - connected speech
      - following several sentences in sequence
      - producing Korean spontaneously
      - confidence when trying to speak
    preference:
      - conversation-first
      - practical
      - active
      - context-heavy
      - low-theory
      - repetitive but varied
      - no chatbot

  learning_goal:
    primary: "Reach comfortable intermediate Korean for everyday conversation."
    secondary:
      - "Understand natural everyday Korean more easily."
      - "Speak about personal life, feelings, opinions, plans, food, family, work and past experiences."
      - "Use Korean more comfortably with a native-speaking girlfriend."
      - "Become less shy about producing imperfect Korean."

  teaching_language: "English"
  explanation_style:
    - simple
    - direct
    - concrete
    - no baby-talk
    - no unnecessary linguistic jargon
    - explain grammar only when useful for understanding or producing the dialogue

pedagogy:
  primary_unit: "conversation"
  ai_during_study: false
  chatbot: false
  fixed_answers: true
  fixed_model_responses: true

spaced_repetition:
  intervals_days: [1, 3, 7, 14, 30, 60]

difficulty:
  target_transition: "beginner -> intermediate"
```

---

# 2. Source material

The first source corpus is the learner's copy of:

**Talk To Me In Korean — Real-Life Korean Conversations For Beginners**

The supplied book contains 40 everyday topics and two dialogue levels for each topic: a shorter/easier dialogue and a longer/more complex dialogue. It explicitly presents everyday situations, vocabulary, grammar points, pronunciation practice, cultural notes, and Korean-only versions of the dialogues.

The app should treat this kind of material as a model for curriculum structure.

Examples of useful source categories from the supplied book include:

- introductions
- friends
- invitations
- family
- shopping
- dates
- work
- school
- food
- health
- transportation

Do not build a web scraper for the book.

Do not require internet access.

Instead, design the curriculum system so that **local Markdown content files** are the canonical course content. The learner can later add more conversation sets, including material from an intermediate book, other personally owned material, or original conversations written specifically for the course.

IMPORTANT COPYRIGHT/CONTENT RULE:

Do not silently reproduce large amounts of copyrighted source material into newly generated source files unless that text has been explicitly supplied to the application by the learner. Build the engine so supplied dialogue text can be imported and studied. When creating new course dialogues, write original dialogues rather than copying published ones.

Keep a `docs/SOURCES.md` documenting where each conversation came from:
- supplied source
- learner-authored
- original course content
- adapted from a supplied source

---

# 3. Course philosophy

The course is conversation-first.

A conversation is not merely an example attached to a grammar lesson.

A conversation IS the lesson.

Grammar, vocabulary, pronunciation, and sentence patterns are extracted from the conversation because the learner needs them to understand and reproduce the conversation.

The learner should repeatedly encounter each conversation in different modes:

1. read with English support
2. read Korean only
3. recall vocabulary/pattern meaning
4. answer questions about the conversation
5. reconstruct lines
6. produce missing lines
7. answer personal questions using the target structures
8. paraphrase lines
9. practice saying lines aloud
10. revisit the conversation later through spaced repetition
11. transfer the useful patterns to a new fixed situation

The app must never require AI to judge free-form Korean answers.

Every production exercise must have one or more stored acceptable/model answers.

The learner compares their own response with the model answer and self-rates it.

---

# 4. Course structure

Use two clearly separated passes.

## Turn 1 — Understand

Goal:

> "I can follow this conversation and understand how it works."

Turn 1 should focus on:

- context
- comprehension
- vocabulary
- core grammar/patterns
- sentence meaning
- basic production
- confidence

Typical conversation unit:

1. Context
2. Full conversation with translation
3. Vocabulary/patterns
4. Line-by-line understanding
5. Active recall
6. Fixed-answer production exercises
7. Short quiz
8. Speaking/shadowing
9. personal-response practice
10. completion check

## Turn 2 — Use

Goal:

> "I can produce and manipulate the language used in this conversation."

Turn 2 should revisit the same themes and language at a higher difficulty.

Focus on:

- Korean-only comprehension
- natural phrasing
- omitted subjects/context dependence
- connective endings
- tense/aspect changes
- reasons and explanations
- opinions
- emotional nuance
- paraphrasing
- changing formality
- responding to follow-up questions
- telling a short version of the story
- producing similar sentences about the learner's own life

Turn 2 should deliberately interleave older conversations and structures.

---

# 5. Topic progression

Do NOT make a standalone "Grammar" topic.

Grammar should live inside conversations.

Use conversation themes as the dashboard structure.

Suggested progression:

## Phase 1 — Everyday Korean
- greetings and checking in
- plans
- daily routines
- coming home
- waking up
- food and dinner
- cafés
- restaurants
- shopping
- errands

## Phase 2 — People and relationships
- friends
- invitations
- dating
- family
- meeting someone's family
- relationships
- making plans together
- talking about someone's personality

## Phase 3 — Experiences and stories
- what happened today
- weekend stories
- past experiences
- travel stories
- embarrassing/funny moments
- memories
- explaining what happened and why

## Phase 4 — Feelings and opinions
- being tired
- being happy/sad/stressed
- preferences
- likes/dislikes
- agreeing
- disagreeing
- giving opinions
- explaining reasons
- discussing ways of thinking

## Phase 5 — Work, study and health
- workdays
- schedules
- career
- workplace situations
- studying
- healthcare
- hospitals
- medicine
- talking about being sick
- explaining symptoms and experiences

## Phase 6 — Intermediate everyday conversation
- longer conversations
- indirect answers
- follow-up questions
- storytelling
- nuanced opinions
- hypothetical situations
- comparing possibilities
- making suggestions
- expressing uncertainty
- correcting yourself
- reacting naturally

Do not force every learner through every topic in a rigid order.

The dashboard should provide a recommended order while keeping all content accessible.

---

# 6. Conversation unit format

Each conversation is a Markdown module.

Example frontmatter:

```yaml
---
id: feelings-03
title: "I’ve been feeling a little stressed lately"
phase: 4
turn: 1
minutes: 30
kind: conversation
difficulty: 2
source: original
themes:
  - feelings
  - daily_life
  - relationships
grammar:
  - -는 것 같다
  - -아서/어서
  - 그래서
vocabulary:
  - 스트레스
  - 요즘
  - 신경 쓰이다
---
```

A conversation module must contain these sections:

```markdown
## A. Context

## B. Conversation

## C. Understand the Conversation

## D. Language You Need

## E. Active Production

## F. Speaking Practice

## G. Transfer

## Quiz Check

## Mastery Check
```

---

# 7. Section A — Context

Keep this short.

Explain:

- who is talking
- their relationship
- where they are
- what is happening
- what the learner should listen/read for

Do not give a grammar lecture.

Example:

> Two people who are dating are talking after work. One person seems tired and explains why their day was stressful.

---

# 8. Section B — Conversation

Display the complete fixed dialogue.

The conversation must support at least four modes:

### Mode 1 — Korean + English

Useful for first exposure.

### Mode 2 — Korean only

Translation hidden.

### Mode 3 — Line recall

Show one speaker's line and ask the learner to reconstruct the other line.

### Mode 4 — Listening/speaking mode

If a local audio file exists, provide audio controls.

If no local audio exists, provide a clean "Speak aloud" practice mode that asks the learner to read/reproduce the line aloud.

Do NOT use speech recognition or AI.

The application must remain functional without audio.

---

# 9. Section C — Understand the Conversation

This replaces generic textbook comprehension questions.

Use fixed-answer retrieval.

Include:

### C1. Meaning checks

Questions such as:

- Why is X doing Y?
- What happened before this?
- What does X mean by this?
- What are they planning?
- How does X feel?

Answers are fixed and revealable.

### C2. Line reconstruction

Give:

> 오늘 일이 좀 __________.

The learner types the missing Korean.

Then they reveal the model answer.

### C3. Korean-to-English meaning

Show a Korean line and ask the learner to explain what it means.

They write their interpretation and compare it to the fixed explanation.

### C4. English-to-Korean retrieval

Give a natural English prompt and require the learner to produce the target Korean line or a stored acceptable variant.

Do not automatically grade open Korean.

Use self-rating.

---

# 10. Section D — Language You Need

This is where grammar and vocabulary live.

Do NOT create generic textbook chapters.

Every item must answer:

> "Why does the learner need this to understand or use this conversation?"

For each important structure:

```markdown
### Pattern

**Meaning:** simple English explanation.

**Used here:**

> 실제 Korean example

**Basic shape:**

> Korean form

**What changes:**
- simple explanation

**Try it:**

[[respond]]
Q: Produce the Korean sentence for this situation.
A: fixed model answer
[[/respond]]
```

Grammar explanations should be short.

Prefer:

> "-는 것 같아 is useful when you want to say something seems/is probably a certain way."

over:

> "This is a nominalized adnominal clause followed by the bound noun 것..."

The latter can be included only when necessary.

---

# 11. Section E — Active Production

This is one of the most important parts of the system.

The learner must PRODUCE Korean.

Every exercise has a fixed answer or fixed model answer.

No AI evaluation.

Use several exercise types:

## Type 1 — Complete the sentence

```markdown
[[respond]]
Q: "I think it's going to rain."
A: 비가 올 것 같아.
[[/respond]]
```

## Type 2 — Translate meaning into Korean

Give a natural English situation.

Learner writes Korean.

Reveal model answer.

## Type 3 — Answer a question

Example:

> 주말에 뭐 할 거야?

The learner writes their own answer.

Then show:
- one natural model answer
- optionally 2–3 acceptable variants

The learner self-rates:
- Got it
- Mostly got it
- Missed it

## Type 4 — Change the sentence

Example:

> Change this from polite speech to casual speech.

Fixed answer.

## Type 5 — Change the time

Example:

> Say the same thing about yesterday.

Fixed answer.

## Type 6 — Say it another way

Show an original line and one fixed alternative formulation.

## Type 7 — React naturally

Example:

> Someone tells you they had a terrible day. What could you say?

Provide 2–3 stored natural model responses.

The learner chooses one or writes their own.

The system never claims their answer is correct automatically.

---

# 12. Personal-response practice

The learner explicitly wants practice that forces them to think and pushes them outside the shyness that comes with not knowing a language.

Therefore every substantial conversation should contain a small number of personal-response prompts.

These are NOT chatbot interactions.

The app simply asks the question and waits for the learner to type or speak aloud.

Examples:

- 오늘 하루 어땠어?
- 요즘 뭐가 제일 신경 쓰여?
- 이번 주말에 뭐 하고 싶어?
- 어렸을 때 어떤 사람이었어?
- 가족이랑 자주 뭐 해?
- 어떤 음식이 제일 좋아?
- 요즘 일하면서 뭐가 제일 힘들어?
- 사람을 볼 때 어떤 점을 중요하게 생각해?

The app then shows a fixed model answer.

Important:

The model answer is **not supposed to be "the learner's correct answer."**

It is a natural example response.

The learner compares:

> Did I communicate the idea?
> Could I make the sentence more natural?
> What useful phrase did the model use?

The UI must explicitly distinguish:

- "Answer check"
- "Model answer"
- "Personal answer"

Never mark a personal answer wrong simply because it differs from the model.

---

# 13. Section F — Speaking Practice

The learner wants confidence and active speaking.

Do not build automatic pronunciation scoring.

Instead build a low-friction speaking routine.

For each important conversation:

### F1. Shadow

Show the Korean line.

Optional audio if local audio exists.

Button:

> "Reveal translation"

### F2. Recall

Hide the Korean line.

Show the English meaning/context.

The learner says the Korean aloud.

Then click:

> "Reveal Korean"

### F3. Role practice

Show:

> Partner: 오늘 뭐 먹고 싶어?

The learner answers aloud.

Then show 2–3 natural model answers.

### F4. Full conversation

Let the learner hide:
- English
- Korean
- both

and work through the dialogue from memory.

Do not require a microphone.

---

# 14. Section G — Transfer

Transfer means:

> "Can I use the useful language from this fixed conversation somewhere else?"

Do NOT create a chatbot.

Write another fixed mini-situation using the same target structures.

Example:

Study dialogue:
> talking about being stressed at work

Transfer situation:
> talking to your girlfriend about being tired after a difficult week

The learner must produce one or more fixed-answer/model-answer responses.

Transfer exercises may be:

- complete the sentence
- answer a question
- change tense
- change subject
- change formality
- explain a reason
- express a similar feeling
- respond to a statement
- reconstruct a short mini-dialogue

---

# 15. Quiz Check

Every conversation has a short quiz.

Recommended:
- 4 questions
- mix of comprehension, vocabulary and grammar-in-context
- correct answer positions randomized

Do not make quizzes trivia tests.

Good:

> Why does 민지 say "그래서"?

Bad:

> What page was this conversation on?

---

# 16. Mastery and completion

Do not require perfect performance.

A conversation is complete when the learner has demonstrated active engagement with it.

Recommended lesson gate:

1. conversation has been opened
2. at least the required core recall items have been rated
3. quiz completed
4. active production completed
5. at least one personal-response exercise completed
6. speaking practice acknowledged
7. mastery score meets threshold

Use:

```yaml
mastery_threshold: 80
```

Mastery score should combine:

- recall
- quiz
- production self-rating

Do not treat personal free-form answers as automatically correct/incorrect.

Completion means:

> "I engaged with this material and can retrieve most of the important language."

Not:

> "I am fluent in this conversation."

Access should never be hard-gated.

A learner may open any lesson at any time.

Use soft prerequisite cues only.

---

# 17. Active recall mechanics

Use the original system's strongest idea:

> The learner should retrieve before seeing the answer.

For every `[[card]]` and `[[respond]]`:

1. show prompt
2. give answer field
3. learner submits or writes
4. reveal fixed answer/model answer
5. learner self-rates
6. persist the result

Use:

```text
GOT
MOSTLY
MISSED
```

Do not automatically judge Korean free-response text.

Ratings should persist across refreshes.

Replaying persisted ratings must not create duplicate error-log entries.

---

# 18. Error Log

Create `/errors`.

This is a language-learning error log.

When the learner marks something missed, record:

```yaml
type: vocabulary | grammar | production | comprehension | pronunciation | conversation
source: lesson-id
prompt: ...
learner_answer: ...
model_answer: ...
note: ...
frequency: 1
```

The error-log page should show:

- what the learner struggled with
- how often
- the model answer
- relevant conversation
- a button to revisit the original exercise

Do not try to diagnose arbitrary Korean automatically.

Allow the learner to add a manual note.

Example:

> "I keep forgetting that 아쉽다 is often used for a feeling of disappointment/regret."

---

# 19. Spaced repetition

Keep the original system's philosophy:

> A review session must ASK REAL QUESTIONS.

Never say:

> "Review the conversation you studied 3 days ago."

Instead generate an actual review session from the course's stored content.

Use:

```python
SR_OFFSETS = [1, 3, 7, 14, 30, 60]
```

Recommended review progression:

| Stage | Day | Content |
|---|---:|---|
| 0 | 1 | 3 recall questions from the same conversation |
| 1 | 3 | 2 recall + 1 production |
| 2 | 7 | 1 recall + 2 questions from another completed conversation in the same theme |
| 3 | 14 | 1 production + 1 transfer question |
| 4 | 30 | mixed recall + production + transfer |
| 5 | 60 | transfer + teach-back / story reconstruction |

A review session should never ask about material the learner has not completed.

Cross-conversation questions may only use completed conversations.

Rank review items:

1. previously missed
2. never reviewed
3. least recently reviewed

Cap sessions at approximately 20 questions.

Do not split one conversation's required review recipe across multiple unfinished sessions.

The review session must be server-side and refresh-safe.

---

# 20. Teach-back

Replace the original technical Feynman exercise with a language-learning version.

The learner gets prompts such as:

> "Without looking back, explain in English what this Korean expression is used for."

or:

> "Without looking back at the dialogue, summarize what happened."

or:

> "Say three Korean sentences using the pattern."

Then reveal a fixed model or checklist.

The goal is retrieval, not grading linguistic perfection.

---

# 21. Conversation reconstruction

Add a dedicated exercise type that is particularly important for this course.

The system should store a conversation as ordered turns:

```yaml
speaker: A
korean: ...
english: ...
```

Then generate deterministic reconstruction exercises:

### Missing line

Show surrounding lines and ask for the missing line.

### Missing phrase

Blank out a key phrase.

### Speaker recall

Show the English meaning and ask for the Korean line.

### Conversation skeleton

Show only:
- situation
- speakers
- key vocabulary

The learner reconstructs as much as possible.

Then reveal the original dialogue.

Do not use AI to grade the reconstruction.

---

# 22. Pattern bank

Build a reusable bank of high-value Korean expressions discovered from conversations.

Examples:

- 그런데
- 그래서
- 사실
- 약간
- 아직
- ~것 같아
- ~려고 하다
- ~아/어야 하다
- ~잖아
- ~는데
- ~더라고
- ~거든
- ~았/었으면 좋겠다

Do not dump grammar lists on the learner.

The pattern bank is primarily used by:
- search
- review
- lesson cross-links
- error log
- transfer exercises

Each pattern page should point back to the conversations where it appeared.

---

# 23. Vocabulary system

Vocabulary should be conversation-linked.

Do not create a giant isolated dictionary as the primary learning method.

Each vocabulary item should store:

```yaml
korean: ...
meaning: ...
part_of_speech: ...
conversation_ids: [...]
example_sentences: [...]
notes: ...
```

A word's primary example should come from a studied conversation whenever possible.

Support:
- search
- "where did I see this?"
- review
- missed words
- related conversations

---

# 24. Difficulty system

Every conversation has a difficulty from 1–5.

Use difficulty based on actual language demands, not arbitrary vocabulary counts.

Consider:

- sentence length
- amount of implied context
- grammar complexity
- connective endings
- vocabulary familiarity
- speech level
- number of turns
- natural contractions
- ambiguity
- storytelling
- emotional nuance
- number of ideas carried in one sentence

Suggested meaning:

1 = very basic
2 = basic everyday conversation
3 = upper-beginner / bridge to intermediate
4 = intermediate everyday conversation
5 = challenging natural conversation

The learner's first objective is to move steadily from roughly 2 → 3 → 4.

Do NOT suddenly jump from beginner dialogues to difficult native-level material.

---

# 25. Progress dashboard

Create a simple dashboard.

Show:

### Current progress
- conversations completed
- current recommended conversation
- review questions due
- current mastery
- active streak only if it is useful; do not gamify excessively

### Learning map
Show the phases and themes.

### Review
Show:
- due today
- overdue
- upcoming

### Weak points
Show:
- frequently missed vocabulary
- frequently missed patterns
- conversations needing review

### Recent practice
Show latest sessions.

### Confidence
Optionally let the learner self-rate:
- "I understood this conversation"
- "I could produce parts of it"
- "I could say similar things"

This is a reflection tool, not part of automated correctness.

---

# 26. "Today's study" mode

Add a single clear entry point:

> STUDY TODAY

It should select a useful small session.

Priority:

1. overdue spaced-repetition
2. due new conversation
3. unfinished active-production exercises
4. one speaking session
5. optional transfer

Do not create a huge daily curriculum.

A useful study session should feel manageable.

Target approximately:

20–40 minutes.

---

# 27. No AI at study time

This is a hard requirement.

The application must NOT call an AI API.

There is no:
- chatbot
- AI conversation partner
- AI grading
- AI correction
- AI-generated response
- online service dependency

All answers, model responses, exercise prompts, and explanations are authored/stored in the course content.

The learner can generate or edit course content outside the study runtime if desired, but the app itself must be deterministic and offline.

---

# 28. File structure

Keep the architecture small.

Suggested:

```text
korean-conversation-lab/
│
├── app.py
├── engine.py
├── progress.py
├── reviewbank.py
├── content_parser.py
├── course.json
│
├── content/
│   ├── everyday/
│   │   ├── 01_plans.md
│   │   ├── 02_dinner.md
│   │   └── ...
│   ├── relationships/
│   ├── stories/
│   ├── feelings/
│   ├── work_health/
│   ├── intermediate/
│   └── bank/
│
├── static/
│   ├── style.css
│   └── app.js
│
├── data/
│   └── vocabulary.json
│
├── docs/
│   ├── DESIGN.md
│   ├── SOURCES.md
│   ├── TOC-mapping.md
│   └── AUDIT.md
│
└── tests/
    ├── test_parser.py
    ├── test_progress.py
    ├── test_review.py
    └── test_content.py
```

Do not add a database unless the simple JSON architecture genuinely cannot support the required data.

Use a JSON progress file outside the source bundle:

```text
~/.korean-conversation-lab/progress.json
```

Rebuilding the application must never erase learning progress.

---

# 29. Technical architecture

Use:

- Python
- standard library wherever practical
- `http.server`
- hand-written HTML rendering
- Markdown source files

Do NOT use:
- Flask
- Django
- React
- Node
- npm
- external hosted services
- CDNs
- browser extensions
- AI APIs

A small Markdown parser dependency is acceptable if truly useful, but the simplest implementation should be preferred.

The app must run with:

```bash
python3 app.py
```

and should open in the browser automatically if practical.

Do not package a Windows `.exe` until the local application works.

Packaging is optional and should be a later step.

---

# 30. Content block syntax

Use a simple parser compatible with Markdown.

## Recall card

```markdown
[[card]]
Q: What does 아직 mean in this conversation?
A: It means "still / yet", depending on context.
[[/card]]
```

## Production response

```markdown
[[respond]]
Q: Say "I'm still at work."
A: 아직 회사에 있어.
[[/respond]]
```

## Multiple acceptable model answers

Support:

```markdown
[[respond]]
Q: What could you say if your girlfriend says she is tired?
A:
- 많이 피곤해?
- 오늘 많이 힘들었어?
- 괜찮아?
[[/respond]]
```

The learner is not judged automatically.

## Quiz

```markdown
[[quiz]]
Q: Why does the speaker say 아직?
- Because they already finished.
* Because they have not finished yet.
- Because they forgot.
- Because they are leaving.
[[/quiz]]
```

---

# 31. Answer storage

Every exercise needs a stable ID.

Example:

```yaml
id: feelings-03-e05
```

Persist:

```json
{
  "answer": "...",
  "rating": "got",
  "updated": "2026-09-11"
}
```

Never overwrite previous answers in a way that loses history unless explicitly needed.

A learner should be able to revisit an exercise and see their previous answer.

---

# 32. Speaking without AI

Speaking is essential, but keep it technically simple.

Do NOT implement:
- speech recognition
- pronunciation scoring
- phoneme comparison
- microphone processing

Instead:

```text
READ
SAY IT
REVEAL
SELF-RATE
```

Optionally support locally stored audio files.

If local audio exists:

```yaml
audio: audio/conversation_03.mp3
```

The app should provide play/pause.

If the audio file is absent, the lesson still works perfectly.

---

# 33. Korean display requirements

Korean must be rendered cleanly.

Prioritize:
- large readable Hangul
- comfortable line spacing
- clear speaker labels
- Korean-first visual hierarchy
- English translation visually secondary

Do NOT put romanization everywhere.

Romanization should be:
- optional
- used sparingly
- hidden by default after the learner has demonstrated Hangul familiarity

The learner is trying to learn Korean, not English transliteration of Korean.

---

# 34. Speech-level awareness

The curriculum must deliberately teach differences among:

- polite speech
- casual speech
- intimate/casual conversation
- speech used with older/unfamiliar people

Every conversation should specify a speech-level context.

Example:

```yaml
speech_level: casual
relationship: romantic_partner
```

Do not teach a phrase as universally correct when its appropriateness depends on context.

When a phrase is especially casual, formal, cute, blunt, soft, awkward, old-fashioned, or context-sensitive, explain that clearly.

---

# 35. Naturalness over literal translation

English prompts should be natural English.

Korean model answers should be natural Korean.

Do not build exercises around word-for-word translation where that produces unnatural Korean.

When a literal translation and natural Korean differ significantly, explain the difference briefly.

Example principle:

> "What would a Korean person naturally say here?"

is more important than

> "How can we translate this English sentence word-for-word?"

---

# 36. Fixed content, not infinite generation

This system is deliberately finite.

The learner should know:

> "Today I am studying Conversation 23."

not:

> "Chat with the AI until you feel better at Korean."

Every conversation should have:
- a title
- a fixed script
- fixed questions
- fixed answers/model answers
- fixed transfer exercises
- fixed review content

The same material is intentionally revisited.

Repetition is a feature, not a bug.

---

# 37. Validation requirements

Build automated validation gates before authoring large amounts of content.

Validate:

1. every module has valid frontmatter
2. unique IDs
3. valid turn
4. valid difficulty
5. balanced `[[card]]` blocks
6. balanced `[[respond]]` blocks
7. balanced `[[quiz]]` blocks
8. every quiz has exactly one correct answer
9. every production exercise has a model answer
10. every conversation has A–G and Quiz sections
11. no empty exercises
12. no missing speaker labels
13. no duplicate IDs
14. valid review-bank references
15. review-bank items never reference incomplete modules
16. progress writes are atomic
17. persisted self-ratings restore correctly
18. refreshing a page never duplicates error-log entries
19. due-count calculation never creates a review session
20. study session survives refresh
21. no study page depends on internet access
22. no AI/network calls exist in runtime code
23. Korean text survives Markdown rendering
24. tables and code-like punctuation are not corrupted by content processing
25. content links resolve correctly

Also build a content audit that flags likely problems for human review:

- English sounds unnatural
- Korean translation sounds overly literal
- conversation is unnaturally textbook-like
- model answer is too advanced for the lesson
- prompt and answer appear to ask different things
- conversation jumps in logic
- speech level is inconsistent
- grammar explanation does not match the example
- target language is not actually used enough
- exercise is testing recognition rather than production

These cannot all be reliably automated. Flag them rather than pretending they can be solved automatically.

---

# 38. Build phases

Work in phases.

## Phase 0 — Minimal scaffold

Build:

- app.py
- engine.py
- progress.py
- one conversation
- dashboard
- one lesson page
- one quiz
- one recall card
- one response exercise
- local progress persistence

Validate immediately.

Do not author the whole curriculum first.

## Phase 1 — Full lesson interaction

Add:

- active recall
- self-rating
- persistent answer boxes
- quiz grading
- error log
- Korean-only mode
- translation reveal
- conversation reconstruction

## Phase 2 — Spaced repetition

Implement:

- reviewbank.py
- due scheduling
- real review questions
- session state
- refresh-safe review
- ranking previously missed items first

## Phase 3 — Content system

Implement:

- content folders
- course.json
- topic/phase dashboard
- pattern bank
- vocabulary bank
- source tracking

## Phase 4 — Speaking mode

Add:

- shadowing
- line recall
- role practice
- optional local audio
- full-conversation practice

## Phase 5 — Curriculum authoring

Author a small representative batch first.

Recommended initial batch:

- 3 easy everyday conversations
- 3 relationship/daily-life conversations
- 3 feelings/opinions conversations
- 3 story/past-event conversations

Do not author hundreds of modules immediately.

Validate the system on the first batch.

## Phase 6 — Difficulty progression

Add:
- difficulty scoring
- Turn 2 versions
- intermediate conversations
- cross-conversation transfer

## Phase 7 — Audit and polish

Run every validation gate.

Test:
- fresh install
- refresh during exercises
- close/reopen during review
- corrupted/missing progress
- missing optional audio
- empty answer
- repeated missed answers
- repeated review
- completed conversation revisit

Only after this should packaging be considered.

---

# 39. What to preserve from the reference learning system

The original robotics course prompt contains several mechanisms that are deliberately retained here because they are useful independent of subject.

Preserve these ideas:

### Two-pass mastery

The learner sees important material again at a deeper level.

### Active recall

The answer is hidden until after the learner attempts retrieval.

### Real-question spaced repetition

Reviews contain real questions, not reminders to study.

### Self-scoring

Free-form answers are not automatically judged.

### Error logging

Missed items become future review material.

### Soft access

Everything can be opened; nothing is needlessly locked.

### Persisted progress

Refreshes and reopening the app should not erase work.

### Content-driven engine

The curriculum lives in Markdown, separate from the application engine.

### Automated validation

Content errors should be caught before they become hundreds of lessons.

These principles from the original course are intentional design choices, not optional decoration.

---

# 40. What NOT to preserve from the reference robotics system

Do not copy subject-specific machinery that makes sense for robotics but not Korean.

Remove:

- career tracks
- portfolio builds
- GitHub projects
- hardware labs
- code editors
- MATH/CODE toolbar
- programming exercises
- executable project solutions
- robotics phases
- job-readiness layer
- project `[[build]]` blocks
- code syntax highlighting
- hardware checklists

Do not replace these with equally complicated language-learning gimmicks.

Keep the system simple.

---

# 41. UI philosophy

The interface should feel like a serious personal study notebook.

Prefer:

- light background
- strong Korean typography
- clean cards
- restrained color
- clear progress
- large Korean text
- obvious "try first / reveal later" interaction

Avoid:

- excessive gamification
- cartoon language-learning aesthetics
- streak obsession
- hearts/lives
- virtual coins
- noisy animations
- emoji-heavy UI

Useful labels:

- CONVERSATION
- RECALL
- PRACTICE
- SPEAK
- TRANSFER
- REVIEW
- MASTERED
- MISSED
- MODEL ANSWER

---

# 42. Core UX loop

A learner opening a conversation should experience something like:

```text
1. What is happening?
2. Read/listen to the conversation.
3. Understand the important language.
4. Hide the English.
5. Try to remember.
6. Type Korean.
7. Reveal the model answer.
8. Compare.
9. Say it aloud.
10. Answer a personal question.
11. Transfer the pattern to another situation.
12. Complete the lesson.
13. Forget some of it naturally.
14. Get a real review question later.
15. Reuse it.
```

That loop is the heart of the product.

---

# 43. Initial curriculum content

Do not attempt to generate hundreds of conversations during Phase 0.

Create a small seed curriculum sufficient to prove the engine.

The first seed conversations should intentionally resemble the kinds of situations the learner actually wants to discuss:

1. plans for tonight
2. what to eat
3. what happened today
4. feeling tired
5. weekend plans
6. going somewhere together
7. talking about family
8. something funny that happened
9. explaining why you did something
10. discussing work/study
11. talking about a past trip
12. expressing an opinion

Use simple language initially, but design the conversations so that they can naturally evolve into intermediate material.

Do not make every dialogue sound like a textbook exercise.

People can:
- hesitate
- change topics
- react emotionally
- ask follow-up questions
- say "actually..."
- correct themselves
- soften statements
- use common conversational fillers

But remain comprehensible and pedagogically intentional.

---

# 44. Important distinction: natural does not mean chaotic

The target is:

> natural enough to be useful

not:

> authentic enough to be impossible for a learner.

Do not overload early conversations with:
- slang
- dialect
- unexplained contractions
- rapid ellipsis
- obscure references

Increase naturalness gradually.

---

# 45. Personalization without AI

The learner should be able to personalize prompts manually.

Allow optional learner-specific fields:

```yaml
personal_prompt:
  enabled: true
  note: "Replace the generic answer with something true about your own life."
```

For example:

> 이번 주말에 뭐 할 거야?

The learner can write their own answer.

The stored model answer can be a generic example, not a judgment.

This is enough.

No generative system is necessary.

---

# 46. Content authoring guidance

When writing a conversation:

1. Start with a believable real-life situation.
2. Decide what the learner should learn from it.
3. Write the Korean conversation first.
4. Write a natural English translation.
5. Identify high-value vocabulary.
6. Identify high-value grammar/patterns.
7. Write comprehension questions.
8. Write production exercises.
9. Write personal-response prompts.
10. Write speaking prompts.
11. Write transfer prompts.
12. Assign difficulty.
13. Validate all exercise answers.

Do NOT begin with:

> "Which grammar point can I teach?"

Begin with:

> "What might two real people actually talk about here?"

---

# 47. Course data model

Use a simple structure such as:

```json
{
  "modules": {
    "plans-01": {
      "completed": false,
      "mastery": 0,
      "sr_index": 0,
      "next_review": null,
      "answers": {},
      "ratings": {},
      "quiz": {},
      "errors": []
    }
  },
  "review": {
    "sessions": {}
  }
}
```

Exact structure is up to the implementation, but keep it human-readable.

---

# 48. Privacy

All learner data is local.

Do not:
- upload progress
- send answers externally
- log private conversations to third-party services
- call analytics services

The learner may write personal answers involving relationships, feelings, family, or work.

Treat those answers as private local study data.

---

# 49. Tests

Write tests for:

### Parser
- frontmatter
- block balance
- quiz parsing
- multiple model answers
- dialogue parsing

### Progress
- save/load
- atomic writes
- answer persistence
- rating persistence

### Review
- due dates
- review recipes
- filtering incomplete modules
- ranking missed items
- session resume

### Content
- all modules valid
- IDs unique
- all production exercises have answers
- all quizzes have exactly one correct option
- speech levels valid

Also include at least one test specifically proving:

> refreshing a completed lesson does not reset its recall score.

And one proving:

> revisiting a persisted mistake does not create a duplicate error-log entry.

---

# 50. Definition of success

The project is successful when the learner can sit down for 20–40 minutes and naturally do this:

> "I want to get better at Korean."

Open the app.

Click:

> STUDY TODAY

And receive a sensible mixture of:

- reviewing an old conversation
- learning one new conversation
- retrieving Korean from memory
- answering a question in Korean
- checking a fixed model answer
- speaking Korean aloud
- revisiting a mistake

without needing:
- an AI chatbot
- internet
- a grammar textbook
- complicated setup
- a teacher to run the session

The system should make studying Korean feel like **working with conversations**, not studying a textbook.

---

# 51. Final operating instructions to the coding agent

Before writing large amounts of code:

1. Read this entire specification.
2. Inspect the existing files in the project directory.
3. Build the smallest end-to-end version first.
4. Keep the architecture simple.
5. Validate after every phase.
6. Do not silently introduce AI dependencies.
7. Do not turn the app into a chatbot.
8. Do not add unnecessary frameworks.
9. Do not create hundreds of modules before the interaction loop has been proven.
10. Prefer deterministic, inspectable content over clever generation.
11. Keep the learner's answers local.
12. Make the system easy for one technically capable person to modify.

When a design decision is ambiguous, prefer:

> simple + offline + conversation-centered + active retrieval + fixed answers + easy to edit

over:

> sophisticated + automated + AI-driven + dependency-heavy

The learning system matters more than visual polish.

Build the learning loop first.
