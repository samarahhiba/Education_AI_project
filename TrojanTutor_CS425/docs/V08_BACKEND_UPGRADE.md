# TrojanTutor CS 425 backend upgrade (v0.8 research foundation)

## What actually changed

- `app/pedagogical_retrieval.py` (new): BM25 baseline, optional local dense embeddings, reciprocal rank fusion, metadata filters, conservative misconception-conditioned query enrichment, explicit fallback and insufficiency markers.
- `app/main.py` (modified): adds `POST /api/evidence`. Existing `/api/ask`, `/api/search`, `/api/session`, and `/api/algorithm` remain intact.
- `tests/test_pedagogical_retrieval.py` (new): four tests for evidence retrieval, citations, API validation and abstention.

This repository remains a **Python FastAPI service**, not a hosted Base44 deployment. The new endpoint gives a Base44 frontend a stable way to request source evidence; the existing `/api/ask` still uses the reproducible card/BM25 teaching engine. No language model or trained misconception classifier was added.

## Modes

- `bm25`: original local BM25 lexical search, suitable for the evaluation baseline.
- `hybrid`: BM25 + optional MiniLM semantic embeddings and reciprocal rank fusion. If dense is not enabled or unavailable, reports `bm25-fallback`.
- `pedagogical`: same retrieval with targeted query enrichment based on the **existing conservative feedback rules** for Kruskal/Dijkstra. Diagnosis is *tentative*, not general free-form grading.

## Enable dense mode locally

Install normal requirements and optionally:

```bash
pip install sentence-transformers
export TROJANTUTOR_ENABLE_DENSE=1
```

On first use the model may need to download, so internet access and model-cache storage are required. Without the optional dependency/environment variable, requests remain deterministic offline BM25. The first dense query may have a substantial initialization latency. Avoid enabling dense in restricted data environments before reviewing model downloads.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/api/evidence \
  -H 'Content-Type: application/json' \
  -d '{"query":"Why does Kruskal reject this edge?", "unit":"Minimum Spanning Trees", "concept":"kruskal", "student_explanation":"A spanning tree needs a cycle", "mode":"pedagogical"}'
```

The response includes `sources` (original slide/page metadata), `retrieval_mode`, `dense_available`, `diagnosis`, `sufficiency`, and a warning that retrieved content has not been independently entailment-verified. Preserve and show that warning in research settings. For browser calls from a Base44-hosted frontend, configure appropriate CORS on the FastAPI server for the exact Base44 origin; do not add a wildcard origin if sending credentials. Deploy FastAPI separately at an HTTPS URL reachable by the frontend. A localhost address on a student's device is **not** a publicly hosted backend.

## Architecture

```text
Base44 UI (separate deployment)
      | REST HTTPS
      v
FastAPI: /api/session /api/ask /api/algorithm /api/evidence
      |                  |                 |
  session state     original tutor      retrieval variants
                      |                 | BM25 + optional MiniLM + RRF
                 concept cards          | tentative misconception guidance
                      |                 v
                   CS 425 slides + original page citations
```

## Research evaluation plan

Use a fixed, instructor-reviewed corpus of student questions and manually labeled relevant slides. For each query run the same corpus and filters with modes `bm25`, `hybrid`, `pedagogical`. Score Recall@5, MRR@10 and nDCG@5 against slide-level relevance labels; compare retrieval latency and whether citations actually entail the answer with independent annotation. For misconception classification, use independently human-labeled student responses and report accuracy and macro-F1; rule-based abstentions must be reported separately. Evaluate follow-up question correctness and student understanding with randomized controlled student sessions only if consent and appropriate university review/permissions are in place. No experimental measurements have been fabricated.

## Boundaries

The v0.8 module does not supply trained generative dialogue, real-time audio streaming, persistent accounts, automatic diagram reading, full graph-aware dialogue, a cross-encoder reranker, guaranteed citation faithfulness, or an end-to-end research dashboard. These require additional engineering and evaluation. Existing voice controls and animations remain in `static/index.html`, not reimplemented here. Course PDFs may have instructor distribution restrictions.

## Demo to a professor

1. Start FastAPI and show `/api/health`.
2. Ask `/api/ask` why Kruskal avoids cycles; note the original evidence/citations.
3. Run `/api/evidence` in `bm25` mode, then `pedagogical` mode with a student misconception; compare returned pages and explicit diagnosis/fallback metadata.
4. Open the original interface, run Kruskal step by step and demonstrate the existing voice controls.
5. Emphasize the difference between working deterministic components, conditional semantic retrieval, and planned experiments.
