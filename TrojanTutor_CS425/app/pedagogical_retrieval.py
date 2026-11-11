"""Research-oriented evidence retrieval; preserves original BM25 baseline.

Dense search is OPTIONAL: install sentence-transformers to enable embeddings. Without
it the module reports lexical-only rather than pretending to run semantic search.
No generative student grading is performed here. Misconception labels are tentative.
"""
from functools import lru_cache
import os
from .retrieval import CHUNKS, CHUNK_IDX, tokenize, best_bullets, CARD_BY_ID
from .feedback import assess

@lru_cache(maxsize=1)
def _dense_index():
    if os.getenv("TROJANTUTOR_ENABLE_DENSE", "0") != "1":
        return None
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        texts = [f"{c['title']}\n{c['text']}" for c in CHUNKS]
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return model, vectors
    except (ImportError, OSError, RuntimeError, ValueError):
        return None


def _rrf(ranked_lists, k=60):
    scores = {}
    for ranked in ranked_lists:
        for rank, idx in enumerate(ranked, 1):
            scores[idx] = scores.get(idx, 0) + 1 / (k + rank)
    return sorted(scores, key=lambda idx: (-scores[idx], idx))


def retrieve_evidence(query, unit=None, concept=None, student_explanation=None,
                      mode='hybrid', limit=5, lecture=None):
    """Return slide-grounded evidence and explicit retrieval provenance.

    mode: bm25 | hybrid | pedagogical. The latter enriches the query only when
    conservative feedback identifies an actionable misconception.
    """
    if mode not in ('bm25', 'hybrid', 'pedagogical'):
        raise ValueError('mode must be bm25, hybrid, or pedagogical')
    if not 1 <= limit <= 25:
        raise ValueError('limit must be between 1 and 25')
    if concept is not None and concept not in CARD_BY_ID:
        raise ValueError('unknown concept')
    label = 'ungraded'
    enriched = query
    if mode == 'pedagogical' and concept and student_explanation:
        label, _ = assess(concept, student_explanation)
        if label in ('partial', 'misconception'):
            card = CARD_BY_ID[concept]
            enriched = ' '.join((query, card['title'], card['why'], card['trap']))
    terms = tokenize(enriched)
    eligible = [i for i, c in enumerate(CHUNKS)
                if (not unit or c['unit'] == unit)
                and (not lecture or lecture.lower() in (c.get('source','')+' '+c.get('title','')).lower())]
    if not terms or not eligible:
        return {'sources': [], 'retrieval_mode': 'bm25', 'dense_available': False,
                'diagnosis': label, 'sufficiency': 'insufficient'}
    lexical = sorted(eligible, key=lambda i: (-CHUNK_IDX.score(i, terms), i))
    lexical = [i for i in lexical if CHUNK_IDX.score(i, terms) > 0]
    rankings = [lexical]
    dense_available = False
    if mode != 'bm25':
        index = _dense_index()
        if index is not None:
            model, matrix = index
            vector = model.encode([enriched], normalize_embeddings=True)[0]
            ranked = sorted(eligible, key=lambda i: (-float(matrix[i] @ vector), i))
            rankings.append(ranked)
            dense_available = True
    order = lexical if len(rankings) == 1 else _rrf(rankings)
    # Preserve BM25 behavior when semantic retrieval is unavailable.
    selected = order[:limit]
    sources = []
    for idx in selected:
        c = CHUNKS[idx]
        score = CHUNK_IDX.score(idx, terms)
        sources.append({**c, 'score': round(score, 3),
                        'excerpt': best_bullets(c['text'], query, title=c['title'])})
    sufficiency = 'candidate-evidence' if sources else 'insufficient'
    return {'sources': sources, 'retrieval_mode': mode if dense_available or mode=='bm25' else 'bm25-fallback',
            'dense_available': dense_available, 'diagnosis': label,
            'sufficiency': sufficiency,
            'note': 'Candidate evidence requires verification; presence of a citation does not prove entailment.'}
