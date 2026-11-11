> **v0.7 note:** the topic classifier described below is no longer in the answer path. See README.md for the concept-lesson + hybrid retrieval design (`app/ingest.py`, `app/retrieval.py`, `app/tutor.py`, `data/concepts.json`).

# Training and presentation notes (v0.6)

## What I trained

I trained two small supervised classifiers locally. One maps student questions to 13 lecture concepts; the other identifies the most likely CS 425 lecture unit. Training uses slide text and a limited set of manually prepared example questions. The fitted model is saved as `models/cs425_model.joblib`, so the app makes predictions offline without an API key.

This is **not** a trained generative LLM. The explanation text is written by the developer and selected based on the model's prediction; course evidence is retrieved from PDF slide pages. The model is still weak on unfamiliar phrasings, so it may abstain or pick an incorrect topic. Training results are in `models/training_report.json` and must be shown transparently.

## File-by-file talk track

1. `app/train_model.py`: This is the training pipeline. It turns course slide text and curated questions into labeled training examples; extracts word and bigram TF-IDF features; optimizes linear classification weights; and saves the trained artifact and evaluation report.
2. `models/cs425_model.joblib`: This is the actual learned model. Predictions run locally without cloud credentials.
3. `app/local_model.py`: This performs topic inference, checks confidence and current course unit, then selects a bounded explanation and diagnostic follow-up question.
4. `app/retrieval.py`: This selects supporting slide pages with lexical ranking; it is separate from the classifier and attaches source page numbers.
5. `app/tutor.py`: This orchestrates retrieval, model prediction and short-session context.
6. `app/main.py`: This supplies FastAPI session and tutoring endpoints for the browser.
7. `static/index.html`: This invokes backend endpoints, speaks tutor answers, listens to speech, interrupts ongoing speech and resumes playback.
8. `app/algorithms.py`: This calculates Kruskal and Dijkstra results independently of any ML model, making algorithm steps checkable.
9. `tests/test_tutor.py`: This tests application behavior and deterministic numerical algorithm logic.

## Demo sequence

- With no `OPENAI_API_KEY` defined, launch `python -m uvicorn app.main:app --reload`.
- Show a question about why Kruskal rejects an edge forming a cycle; display its citation and explain why cycle avoidance is essential.
- Try the microphone barge-in while the mini-lecture is speaking; explain that browser voice APIs can be unreliable.
- Change units and ask about Dijkstra's nonnegative-weight restriction.
- Run Kruskal and Dijkstra to show verifiable algorithmic output.
- Run `python -m pytest -q`, then show `models/training_report.json`, including the limitations.

## What needs to happen next

The next research-relevant iteration is **LLM fine-tuning**, if that is the aim. It needs an available pretrained base model, a legally usable instructional dataset of student question–answer–hint dialogs, meaningful evaluation scenarios, and GPU resources. Raw lecture pages by themselves do not train a robust Socratic conversational tutor. Ensure instructor permission for course material use and any later student research.
