"""Research-oriented evidence retrieval with explicit provenance.

Modes (all share the same chunk set, filters and output schema, so they can be compared):
  bm25         original stemmed BM25 + synonyms — the evaluation baseline, unchanged.
  dense        local embeddings only (LSA by default; MiniLM if TROJANTUTOR_ENABLE_DENSE=1).
  hybrid       BM25 + dense fused with reciprocal rank fusion (RRF).
  pedagogical  hybrid, with the query enriched by the concept card ONLY when the conservative
               rule-based feedback recognises a misconception/partial answer.

No generative grading happens here. Misconception labels are tentative. A returned source is a
candidate, not verified entailment; app/grounding.py scores support separately.
"""
from .retrieval import CHUNKS, CHUNK_IDX, tokenize, best_bullets, CARD_BY_ID
from .feedback import assess
from .embeddings import dense_rank

MODES = ('bm25', 'dense', 'hybrid', 'pedagogical')


def _rrf(ranked_lists, k=60):
    scores = {}
    for ranked in ranked_lists:
        for rank, idx in enumerate(ranked, 1):
            scores[idx] = scores.get(idx, 0) + 1 / (k + rank)
    return sorted(scores, key=lambda idx: (-scores[idx], idx))


def rank_ids(query, mode='hybrid', unit=None, lecture=None):
    """Return (ranked chunk indices, backend name). Shared by the API and the offline evaluation."""
    terms = tokenize(query)
    eligible = [i for i, c in enumerate(CHUNKS)
                if (not unit or c['unit'] == unit)
                and (not lecture or lecture.lower() in (c.get('file', '') + ' ' + c.get('title', '')).lower())]
    if not eligible:
        return [], 'none'
    lexical = []
    if terms:
        scored = [(CHUNK_IDX.score(i, terms), i) for i in eligible]
        lexical = [i for s, i in sorted(scored, key=lambda z: (-z[0], z[1])) if s > 0]
    if mode == 'bm25':
        return lexical, 'bm25'
    backend, dense = dense_rank(query, eligible)
    if backend is None:
        return lexical, 'bm25-fallback'
    if mode == 'dense':
        return dense, backend
    if not lexical:                      # no lexical evidence at all: do not let dense invent relevance
        return [], f'bm25+{backend}'
    return _rrf([lexical, dense[:max(20, len(lexical))]]), f'bm25+{backend}'


def retrieve_evidence(query, unit=None, concept=None, student_explanation=None,
                      mode='hybrid', limit=5, lecture=None):
    if mode not in MODES:
        raise ValueError('mode must be one of ' + ', '.join(MODES))
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
    order, backend = rank_ids(enriched, 'hybrid' if mode == 'pedagogical' else mode, unit, lecture)
    if not tokenize(enriched) or not order:
        return {'sources': [], 'retrieval_mode': backend, 'dense_available': '+' in backend or backend in ('lsa', 'minilm'),
                'diagnosis': label, 'sufficiency': 'insufficient'}
    terms = tokenize(enriched)
    sources = []
    for idx in order[:limit]:
        c = CHUNKS[idx]
        sources.append({**c, 'score': round(CHUNK_IDX.score(idx, terms), 3),
                        'excerpt': best_bullets(c['text'], query, title=c['title'])})
    return {'sources': sources, 'retrieval_mode': backend,
            'dense_available': '+' in backend or backend in ('lsa', 'minilm'),
            'diagnosis': label, 'sufficiency': 'candidate-evidence',
            'note': 'Candidate evidence requires verification; presence of a citation does not prove entailment.'}
