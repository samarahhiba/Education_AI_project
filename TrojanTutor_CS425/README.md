# TrojanTutor CS 425 v0.7 — concept-lesson RAG + voice-first teaching

Offline, course-specific tutor for **UW-Madison CS 425** (Prof. Michini's slides). **No API key.**
Goal: teach the course's concepts better than a general-purpose voice AI by being *lecture-exact*,
*checkable*, and *adaptive*, instead of merely fluent.

## What changed in v0.7 (the RAG fix)

| Problem in v0.6.1 | Fix in v0.7 |
|---|---|
| "What is an MST?" returned 3 near-identical Prim animation frames, never the definition | `app/ingest.py` merges animation frames: 265 pages -> 137 slides with page ranges (`data/chunks.json`) |
| Answers were a canned sentence + a raw 300-char slide dump (titles, pseudo-code, symbols) | Answers are composed from **28 authored concept lessons** (`data/concepts.json`): plain words -> analogy -> worked example -> check question. Slide excerpts are cleaned and shown as evidence |
| A 55%-accurate classifier gated every answer; pickle failed to load across scikit-learn versions | Classifier removed from the answer path. Matching = alias phrases + stemmed BM25 + synonyms (`app/retrieval.py`) |
| Students say "residual network"; slides say "auxiliary digraph" | Synonym map + alias lists; the lesson teaches both names |
| Wrong-unit questions hit a dead end | Cross-unit answers with a note ("that is covered in the Shortest Paths unit") |
| Static mini-lecture paragraph | Guided lesson: "Start the lesson" -> concept -> say "next" |
| Same text on repeat questions | Second ask switches angle (one-sentence summary, demo, common mistake) |

## How it teaches (`app/tutor.py`)

Intents: explain, simplify, why, example/walk-through, compare, quiz, next/start, and **answer**
(student states something in their own words -> compared with the lecture's reasoning).
Follow-ups ("explain it more simply", "why?", "difference between that and Prim") resolve against the
previous concept. Kruskal and Dijkstra walkthroughs are narrated from the **tested code** in
`app/algorithms.py`, not generated. The API returns `answer` (screen: full text + slide quote) and
`spoken` (voice: concise, no quote); the UI speaks `spoken`.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.ingest          # only needed if data/slides.json changes
python -m uvicorn app.main:app --reload     # http://127.0.0.1:8000
python -m pytest -q
```

## Adding a concept
Append a card to `data/concepts.json` (fields: id, unit, title, aliases, simple, analogy, example, why,
trap, check, refs = slide page numbers, optional contrast/demo). `tests/test_tutor.py` verifies every card
has all fields and resolvable slide refs.

## Honest limitations
- Not generative: it cannot answer questions outside the 28 lessons (it says so and lists what it can explain,
  with the closest slide).
- It cannot grade a free-form answer; "answer" mode shows the reference reasoning for the student to compare.
- Lessons are authored from the slides; **have the instructor/TA review them** before classroom use.
- Slide text extraction can't read diagrams. UW slides need instructor permission before redistribution.
- `app/train_model.py`, `app/local_model.py`, `models/` are the old classifier, kept for the research record and
  no longer used by `/api/ask`.
- Next step for open-ended dialogue: a generative model *constrained to* retrieved cards + slides (card text as the
  only allowed evidence) with an offline fallback to this engine.

### v0.7.1 feedback patch

This release adds **conservative pattern-based answer feedback** for a small subset of MST/Kruskal and Dijkstra reasoning. It does not make the tutor a generative language model or a dependable free-form grader. When there is not enough evidence to judge an answer, it explicitly abstains. See `docs/V071_CHANGES_AND_DEMO.md` for the file-by-file changes and presentation script.

## v0.9 research extension: Misconception Lab

The original Python interface now includes **Misconception Lab**, a deterministic cycle of tentative misconception diagnosis, targeted authored counterexample, lecture-evidence candidates, and a follow-up transfer question. It is currently implemented for Kruskal's cycle reasoning and Dijkstra's nonnegative-weight assumption. It is **not** a trained generative tutor and does not assert student mastery. See `docs/V09_MISCONCEPTION_LAB.md` for a demo, endpoints, limitations, and a research evaluation plan.
