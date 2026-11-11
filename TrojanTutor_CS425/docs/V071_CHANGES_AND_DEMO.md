# TrojanTutor CS 425 v0.7.1 — fixes and demo

## What changed
- `app/feedback.py` (new): conservative rules for a few high-confidence Kruskal/MST cycle and Dijkstra negative-edge statements. It returns *correct*, *partial*, *misconception* or *ungraded*. This is not a general answer grader or generative model.
- `app/tutor.py`: when an utterance is classified as a student answer, calls the assessment helper rather than blindly congratulating the student and dumping the reference answer. Uncertain answers receive an honest comparison prompt.
- `tests/test_tutor.py`: checks the user's original MST explanation, a deeper correct explanation, an explicit wrong claim, a Dijkstra explanation and an unrelated statement.
- `static/index.html`: clarifies limitations and corrects the version label.
- `app/main.py`: version updated to 0.7.1; existing FastAPI, retrieval, algorithm endpoints, and voice interaction stay intact.

## Presentation demonstration (2 minutes)
1. Select Minimum Spanning Trees and ask, “Why does Kruskal avoid cycles?”
2. Respond: “When a tree becomes a cycle it can no longer be an MST.” The tutor should give **partial** feedback: a tree cannot have cycles, and a cycle-closing edge adds no connectivity.
3. Then respond: “A cycle-closing edge is redundant because its endpoints are already connected.” The tutor should recognize this reasoning, though this is still a narrow rule-based pattern.
4. Respond: “A spanning tree must have a cycle.” The tutor should correct the misconception.
5. Ask an unrelated answer; the tutor should **abstain** from grading rather than invent confidence.
6. Test voice input/output and interruption in Chrome. This must be manually verified in the browser.

## Known limitations
- These are keyword and phrase rules, not semantic understanding. Some paraphrases, negations, and unusual responses may be misclassified. Do not use as a grading system.
- Browser voice recognition and synthesis depend on the user's browser and OS; interruption quality can vary.
- This repository does not fine-tune a pretrained generative LLM. The saved `cs425_model.joblib` is a topic-classification baseline, not a chatbot.
- Instructor authorization is still required for lecture redistribution or formal research use.

## Running
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --reload
```
Visit http://127.0.0.1:8000.
