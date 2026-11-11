> **v0.7 note:** the topic classifier described below is no longer in the answer path. See README.md for the concept-lesson + hybrid retrieval design (`app/ingest.py`, `app/retrieval.py`, `app/tutor.py`, `data/concepts.json`).

> **Updated for v0.6:** The earlier v0.5 walkthrough below describes an optional hosted LLM, which has now been removed. For the current trained-model architecture and correct demonstration, use `docs/TRAINING_AND_DEMO.md` and the README.

# TrojanTutor CS 425: file-by-file presentation guide

## Opening script (45 seconds)

"I built a small, running, lecture-grounded tutoring system for UW CS 425. It is deliberately scoped to graph optimization. A learner can ask about the four uploaded units, inspect source slide evidence, interrupt the spoken response, and step through real Kruskal or Dijkstra calculations. The dialogue layer can use an API-hosted model, but I have not trained a new model. My goal this week is a reproducible application baseline so we can later test misconception detection and instructional decisions."

## Walkthrough, in repo order

**`app/main.py` — FastAPI orchestration (60 seconds).** Show `/api/session`, `/api/ask`, `/api/search`, `/api/algorithm`. A session chooses a unit and has a short chat history. Changing units creates a fresh session. All state is in memory. Explain that the server routes questions through the retrieval+teaching layer, while numerical algorithms run separately.

**`app/retrieval.py` — transparent slide search (60 seconds).** The application loads `data/slides.json` and tokenizes page text. The weighted term-frequency ranking is BM25-like. The search returns page number, file, unit, and excerpt, suppressing adjacent near-duplicate animation pages. This is retrieval, not fine-tuning or semantic vector search. Demo: `Kruskal cycle minimum spanning tree`.

**`app/tutor.py` — tutoring decision path (90 seconds).** Show `PROMPT` and `answer()`. With `OPENAI_API_KEY` the server supplies retrieved slide excerpts and recent turns to an API model, requesting a scoped, Socratic answer and numbered citations. Without it, `fallback_answer()` returns direct evidence and one question. Emphasize that citations are *provided evidence*, not mathematical proof and not a guarantee of generation faithfulness. The backend is responsible for keeping the API key out of the browser.

**`app/algorithms.py` — computational verification (90 seconds).** Kruskal uses disjoint-set union, sorted edges, and cycle checks; each iteration records chosen edges and current weight. Dijkstra uses a priority queue, directed arcs, and relaxation; negative costs explicitly raise an error. Step through the UI. Separate deterministic execution from fluent teaching is a key architecture decision.

**`static/index.html` — learner interaction and voice (90 seconds).** The UI renders chat, citations, search, and algorithm steps. `SpeechRecognition` captures spoken text; `SpeechSynthesisUtterance` speaks the answer. `onspeechstart` cancels audio for barge-in before the final transcript arrives. Recognized final transcript is sent to `/api/ask`; 'resume' restarts the paused full explanation. Caveat: resume restarts the text rather than resuming at the exact phoneme, and browser echo suppression is imperfect. Text input works without voice support.

**`data/slides.json` — course evidence (30 seconds).** A build-time extraction of 265 substantial pages from the four supplied PDFs. Each object retains its origin filename, page number, unit, and text. Formulae/figures may be partly omitted by text extraction.

**`course_materials/*.pdf` — original lecture documents (30 seconds).** The exact four slidesets supplied for the prototype. Explain content provenance and permissions. Slide-specific excerpts are used rather than pretending to have trained a domain model.

**`tests/test_tutor.py` — verification (30 seconds).** Run `python -m pytest -q`. Tests ensure index loads, filtering works, unrelated search can abstain, Kruskal cost is 10 on demo graph, Dijkstra returns B=3/E=10, and negative Dijkstra edges are rejected. Tests do not prove teaching quality or voice latency.

**`docs/RESEARCH_SCOPE.md` — scientific framing (30 seconds).** The initial misconception set contrasts MST with shortest paths, cycle rejection, negative costs, and max-flow/min-cut reasoning. This is a proposed evaluation target, not measured student behavior.

**`requirements.txt` + `README.md` — reproducibility (20 seconds).** Install and run commands, API key configuration, browser notes, and limitations. Four PDFs remain in the repo for demonstration; avoid sharing without permission.

## Live demo script (4–6 minutes)

1. Start `python -m uvicorn app.main:app --reload`; open `http://127.0.0.1:8000`.
2. Select **Minimum Spanning Trees**; click **Start mini-lecture**.
3. Turn on microphone. While speaking, say **“Wait, why does Kruskal skip an edge when it forms a cycle?”** Observe early audio cancellation; read answer and evidence.
4. Type **“Does that mean minimum spanning trees are shortest path trees?”** If API is enabled, discuss session context; if offline, point out the evidence-only fallback.
5. Search **“Kruskal cycle”** and point to file and page citations.
6. Run **Kruskal**, click Next several times; explain why the next edge is accepted or rejected.
7. Switch to **Dijkstra**; walk through distance improvements. State the nonnegative-arc-cost precondition.
8. Finish with the tests and the research question: *Does diagnosing a misconception and choosing targeted instruction improve unaided transfer relative to fixed prompts?*

## Q&A preparation

**Did you train an AI on the lectures?** No. The current model is an externally hosted general LLM, optionally prompted with slide evidence. This is retrieval augmentation, not training. Fine-tuning would need a curated dataset, permission, evaluation, and a defensible reason to prefer it.

**What is genuinely novel?** Not the chat or voice alone. The planned experimental contribution is instrumenting technical misconceptions and comparing policy choices and delayed student performance. That part remains future work.

**Does interruption work perfectly?** No. The browser tries to stop speech when it hears student speech; it can be sensitive to browser/OS permissions and feedback. Resume currently restarts the interrupted explanation rather than continuing at the exact word.

**Can the model prove correctness?** Not reliably. The executable algorithm lab supports specific computed tasks; proofs and arbitrary claims still require reference checks and expert review.

**Is this already suitable for research with students?** No. Obtain permission and institutional review/determination as appropriate before collecting human-subject outcomes, and address vendor speech/API privacy.
