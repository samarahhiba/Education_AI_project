# TrojanTutor CS 425 v0.12: the whole course, spoken, written and drawn

**New in v0.12:** every slide of the four CS 425 decks is taught as one of **32 lessons** (246 steps,
33 check questions). The tutor talks, writes each explanation out in the conversation, and draws the
slide's own figure (redrawn) in sync. It waits for your answers, and you can interrupt any time by typing,
speaking or clicking an edge. Voice input repairs course vocabulary ("crystals" → Kruskal) and shows what
it heard. Details: **`docs/V012_COURSE.md`**.

### v0.11.1: a tutor that talks, writes and draws

**New in v0.11: the Dual-Coding Canvas.** Lessons are spoken, written on a whiteboard and drawn on a graph
at the same time, step by step, from runs of tested algorithm code (Kruskal, Prim, cut property, Dijkstra,
max flow / min cut) or from the lesson cards. Interrupt by typing, speaking or clicking an edge: the lesson
pauses and answers about exactly what is on the board, then resumes. Better voice selection, sentence-by-sentence
speech, live captions, optional neural voice. Details: **`docs/V011_CANVAS.md`**.

### v0.10: streamed, source-grounded tutoring with session memory

Course-specific tutor for **UW-Madison ISyE/Math/CS 425** (Prof. Michini's slides). Runs fully offline with
**no API key**. An optional generative engine is restricted to the lecture slides and its citations are checked.

**New in v0.10 (roadmap Weeks 2–3):** streamed answers · LaTeX equations (KaTeX, offline) · persistent sessions
that survive restarts and unit switches · rebuilt chat UI with grounding badges and clickable citations ·
graph-drawing algorithm lab · PDF ingestion from a hash-verified permission manifest · local embeddings and
hybrid retrieval · citation checker · assignment exercises for practice, a homework hints-only guard and
coverage-gap detection · a retrieval/concept evaluation harness with a held-out set.
Full details and numbers: **`docs/V010_WEEK2_3.md`**.

## Run (macOS / Linux)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m eval.run_eval
python -m uvicorn app.main:app --reload
```
Then open http://127.0.0.1:8000 (uvicorn keeps running; stop it with Ctrl+C). Expect about 160 tests to pass;
`eval.run_eval` writes `eval/results/latest.md`. Paste commands without trailing `# comments`: zsh passes them as arguments.
Rebuild course data after adding a PDF (add it to `course_materials/manifest.json` first):
```bash
python -m app.ingest --check
python -m app.ingest --from-pdfs
```
`--check` verifies hashes and permission status; `--from-pdfs` rebuilds slides → chunks and assignments → exercises.

### Course materials and Git

The source PDFs, assignments, and derived course datasets are kept local and excluded from Git because the
manifest currently marks the supplied materials as pending permission. The permission metadata in
`course_materials/manifest.json` remains included. To run the app or tests from a fresh clone, provide authorized
course files and locally generated data before starting them; do not redistribute the source materials without
written permission.

Optional: `brew install poppler` gives the cleanest PDF text; without it ingestion falls back to pdfplumber/pypdf.

| Env var | Default | Purpose |
|---|---|---|
| `TROJANTUTOR_DEPLOYMENT` | `local` | `shared` = serve only instructor-**approved** material |
| `TROJANTUTOR_SESSION_DB` | `data/sessions.sqlite3` | session + action log |
| `TROJANTUTOR_LLM` | `off` | `anthropic` or `openai` to enable the grounded LLM engine (see docs) |
| `TROJANTUTOR_TTS` | `off` | `openai` = neural voice via an OpenAI-compatible speech endpoint (see docs/V011_CANVAS.md) |
| `TROJANTUTOR_ENABLE_DENSE` | `0` | `1` = MiniLM embeddings instead of local LSA (needs `sentence-transformers`) |

---

## Earlier releases

### v0.7 — concept-lesson RAG + voice-first teaching

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
python -m pytest -q
python -m uvicorn app.main:app --reload
```
(Superseded by the v0.10 instructions at the top.)

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
- `app/train_model.py` and `app/local_model.py` are legacy classifier code and are no longer used by `/api/ask`.
  Generated model artifacts and evaluation reports are excluded from version control.
- Next step for open-ended dialogue: a generative model *constrained to* retrieved cards + slides (card text as the
  only allowed evidence) with an offline fallback to this engine.

### v0.7.1 feedback patch

This release adds **conservative pattern-based answer feedback** for a small subset of MST/Kruskal and Dijkstra reasoning. It does not make the tutor a generative language model or a dependable free-form grader. When there is not enough evidence to judge an answer, it explicitly abstains. See `docs/V071_CHANGES_AND_DEMO.md` for the file-by-file changes and presentation script.

## v0.9 research extension: Misconception Lab

The original Python interface now includes **Misconception Lab**, a deterministic cycle of tentative misconception diagnosis, targeted authored counterexample, lecture-evidence candidates, and a follow-up transfer question. It is currently implemented for Kruskal's cycle reasoning and Dijkstra's nonnegative-weight assumption. It is **not** a trained generative tutor and does not assert student mastery. See `docs/V09_MISCONCEPTION_LAB.md` for a demo, endpoints, limitations, and a research evaluation plan.
