# TrojanTutor v0.9 — Course-grounded Misconception Lab

## Why this is a research direction

The hypothesis is not that a more fluent chatbot is a better tutor. It is that **misconception-conditioned evidence selection plus a contrastive intervention and an immediate transfer probe** may improve correction of mistaken reasoning compared with a standard explanatory RAG response. This release provides an auditable prototype of that pipeline; it does **not** show evidence of learning gains yet.

## Working implementation

- Original 4 course PDFs, 265 source pages, 137 de-duplicated chunks and 28 authored lessons preserved.
- Original offline card tutor, browser microphone/TTS and Kruskal/Dijkstra simulations remain available.
- New `app/interventions.py` evaluates student explanations conservatively, constructs targeted Kruskal or Dijkstra counterexamples for recognized partial/mistaken reasoning, and emits a transfer probe.
- `/api/intervene` returns diagnosis, conservative feedback, prerequisite, authored counterexample, transfer question, reference reasoning and lecture-source candidates.
- `/api/reassess` checks a follow-up answer with existing conservative feedback, explicitly leaves `mastered: null`, and abstains on unfamiliar answers.
- Original `static/index.html` has a new Misconception Lab section that uses those APIs. No Base44 service or API key is required.
- `app/feedback.py` now catches both 'need a cycle' and 'needs a cycle'.
- 39 automated tests pass in the supplied test environment; tests do not require FastAPI TestClient or the `httpx2` package.

## Start (macOS)

```bash
cd TrojanTutor_CS425
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 . Do **not** paste `# http://127.0.0.1:8000` after a `uvicorn` command when launching; your shell may pass it as command arguments.

If `data/slides.json` is changed, re-run `python -m app.ingest`; otherwise the included `data/chunks.json` works immediately.

### Try a deterministic demonstration

1. Choose **Kruskal: cycle avoidance** in the Misconception Lab.
2. Enter: `A spanning tree needs a cycle`.
3. Observe tentative misconception diagnosis, small 3-edge contrastive graph, and cited lecture candidates.
4. Answer the transfer question: `A and C are already connected by A-B-C. The new edge adds no connectivity and creates a cycle, so Kruskal skips it.`
5. Observe the conservative rule-based follow-up. It does not declare mastery.
6. Repeat with Dijkstra: `Negative weights break Dijkstra`.

### JSON API

```bash
curl -s http://127.0.0.1:8000/api/intervene -H 'Content-Type: application/json' -d '{"concept_id":"kruskal","student_explanation":"A spanning tree needs a cycle"}'
curl -s http://127.0.0.1:8000/api/reassess -H 'Content-Type: application/json' -d '{"concept_id":"kruskal","student_explanation":"A and C are already connected, so reject the cycle-closing edge"}'
```

## Scope of actual novelty

**Implemented:** a transparent misconception-to-intervention-to-transfer-test workflow, limited to two concepts, with lecture evidence candidates. **Not implemented:** training a new LLM on PDFs, semantic student-knowledge tracking, reliable free-form correctness grading, personalization over time, robust PDF diagrams, citation entailment verification, or measured gains in retention. The existing `models/cs425_model.joblib` is a legacy classifier **not used** to provide generative tutoring. The original BM25 mode is preserved for experimental baselines. Optional embedding retrieval from v0.8 remains opt-in via `sentence-transformers` and `TROJANTUTOR_ENABLE_DENSE=1`.

## What to study next

In a study, create a fixed, instructor-reviewed set of misconceptions and transfer problems for Kruskal, Dijkstra, Bellman-Ford, and max-flow. Randomize students or sessions between (A) BM25 + standard explanation, (B) hybrid evidence + standard explanation, and (C) misconception-adaptive retrieval + counterexample + probe. Use pretests and **different** immediate and delayed transfer items. Report answer quality, misconception identification accuracy with abstention, retrieval Recall@5/MRR, time-on-task, and delayed correctness. Consent and institutional approval are required before collecting research participant data. Do not interpret an unverified pattern match as a valid mastery outcome.

## Files changed/new

- New: `app/interventions.py`, `tests/test_interventions.py`, `docs/V09_MISCONCEPTION_LAB.md`
- Modified: `app/main.py`, `app/feedback.py`, `static/index.html`, `tests/test_pedagogical_retrieval.py`, `README.md`
