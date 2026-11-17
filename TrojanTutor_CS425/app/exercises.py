"""Assignment exercises: practice prompts, homework-integrity guard, coverage gaps.

Three uses of the course assignments (data/exercises.json, built by `python -m app.ingest --from-pdfs`):

  practice_for(card_id)   pick a related exercise to pose as practice (prefers optional, figure-free ones)
  homework_match(text)    does the student's message reproduce a graded exercise? -> hints-only mode
  uncovered_topic(text)   does it name a topic assignments use but no ingested lecture covers?

Assignments are NOT added to slide retrieval: problem statements are not evidence for claims.
"""
from pathlib import Path
import json, re

from .retrieval import tokenize, norm_phrase, CHUNKS

ROOT = Path(__file__).resolve().parents[1]


def _load(name, default):
    p = ROOT / 'data' / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


EXERCISES = _load('exercises.json', [])
COVERAGE = _load('coverage.json', {'terms': {}})['terms']
_EX_TOKENS = [set(tokenize(e['text'])) for e in EXERCISES]


def _idf():
    """Course vocabulary ("tree", "cost", "minimum") is shared by every exercise and slide; only words
    that are distinctive for an exercise should make a message look like that exercise."""
    import math
    from collections import Counter
    docs = _EX_TOKENS + [set(tokenize(c['text'])) for c in CHUNKS]
    df = Counter(t for d in docs for t in d)
    n = len(docs) or 1
    return lambda t: math.log((n + 1) / (df[t] + 1)) + 0.1


IDF = _idf()

MATCH_MIN_TOKENS = 8         # shorter messages are ordinary questions, not pasted exercises
MATCH_CONTAINMENT = 0.6      # IDF-weighted share of the message's words that come from one exercise
MATCH_COVERAGE = 0.25        # IDF-weighted share of the exercise's words present in the message


def homework_match(text):
    """Return {'exercise', 'containment', 'coverage'} if the message looks like a pasted exercise."""
    q = set(tokenize(text))
    if len(q) < MATCH_MIN_TOKENS or not EXERCISES:
        return None
    best = None
    for ex, toks in zip(EXERCISES, _EX_TOKENS):
        if not toks:
            continue
        shared = q & toks
        containment = sum(map(IDF, shared)) / sum(map(IDF, q))
        coverage = sum(map(IDF, shared)) / sum(map(IDF, toks))
        if containment >= MATCH_CONTAINMENT and coverage >= MATCH_COVERAGE:
            if best is None or containment + coverage > best['containment'] + best['coverage']:
                best = {'exercise': ex, 'containment': round(containment, 2), 'coverage': round(coverage, 2)}
    return best


def uncovered_topic(text):
    words = ' ' + norm_phrase(text) + ' '
    for term, desc in COVERAGE.items():
        if f' {norm_phrase(term)} ' in words:
            return {'term': term, 'description': desc}
    return None


def practice_for(card_id, exclude=()):
    pool = [e for e in EXERCISES if card_id in (e.get('concepts') or []) and e['id'] not in exclude]
    pool.sort(key=lambda e: (e['has_figure'], not e['optional'], (e.get('concepts') or []).index(card_id), e['id']))
    return pool[0] if pool else None


def clean_statement(ex, limit=900):
    """Problem text without figure debris (lines of stray labels and numbers)."""
    keep = [ln for ln in ex['text'].split('\n') if len(re.findall(r'[A-Za-z]{3,}', ln)) >= 3]
    text = ' '.join(keep)
    return text if len(text) <= limit else text[:limit].rsplit(' ', 1)[0] + ' …'
