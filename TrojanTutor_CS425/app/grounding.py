"""Source-grounding labels and a lexical citation check.

Every tutor response carries `grounding`:
  status   lecture-grounded | partially-grounded | retrieved-only | not-grounded
  label    one line the UI shows to the student
  method   how the status was decided (always stated, so nobody mistakes it for entailment)

For generated (LLM) answers, `check_citations` verifies that every [n] points at a source that
was actually supplied, and scores each cited sentence by content-word overlap with that source.
This is a cheap screen for fabricated or mis-attributed citations — NOT proof of entailment.
"""
import re

from .retrieval import tokenize

CITE = re.compile(r'\[(\d{1,2})\]')
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z$\[(])')
MIN_SUPPORT = 0.34           # fraction of a sentence's content words found in its cited slide


def _sentences(text):
    text = re.sub(r'\$\$.*?\$\$', ' ', text, flags=re.S)
    return [s.strip() for p in text.split('\n') for s in SENT.split(p) if len(s.strip()) > 2]


def support(sentence, source_text):
    words = set(tokenize(CITE.sub('', sentence)))
    if not words:
        return 1.0
    return len(words & set(tokenize(source_text))) / len(words)


def check_citations(text, sources):
    cites, invalid, uncited = [], [], []
    for s in _sentences(text):
        nums = [int(n) for n in CITE.findall(s)]
        if not nums:
            # Socratic questions and short connective sentences need no citation.
            if not s.rstrip().endswith('?') and len(tokenize(s)) >= 6:
                uncited.append(s)
            continue
        for n in nums:
            if not 1 <= n <= len(sources):
                invalid.append(n)
                continue
            src = sources[n - 1]
            cites.append({'n': n, 'source_id': src.get('id'), 'pages': src.get('pages'),
                          'support': round(support(s, src.get('text', '') + ' ' + src.get('title', '')), 2),
                          'sentence': s[:200]})
    weak = [c for c in cites if c['support'] < MIN_SUPPORT]
    return {'citations': cites, 'invalid_citations': sorted(set(invalid)),
            'weak_citations': weak, 'uncited_sentences': uncited}


def for_generated(text, sources):
    chk = check_citations(text, sources)
    if not sources or not chk['citations']:
        status, label = 'not-grounded', 'Not source-grounded: no lecture citation supports this answer.'
    elif chk['invalid_citations'] or chk['weak_citations'] or len(chk['uncited_sentences']) > 1:
        status, label = 'partially-grounded', 'Partly grounded: some statements are uncited or weakly supported. Check the slides.'
    else:
        status, label = 'lecture-grounded', 'Grounded in the cited lecture slides (lexical check, not proof).'
    return {'status': status, 'label': label, 'method': 'citation-index + lexical-support check', **chk}


def for_card(card, sources):
    if card and sources:
        pages = ', '.join(s['pages'] for s in sources)
        return {'status': 'lecture-grounded', 'method': 'authored lesson card linked to slide refs',
                'label': f'From an authored lesson card tied to lecture slides {pages}.'}
    if card:
        return {'status': 'partially-grounded', 'method': 'authored lesson card, no slide matched',
                'label': 'Authored lesson card; no matching slide was found.'}
    return not_grounded()


def for_retrieval(sources):
    if sources:
        return {'status': 'retrieved-only', 'method': 'BM25 slide match, no lesson card',
                'label': 'Closest lecture slide shown; this is not a full lesson.'}
    return not_grounded()


def not_grounded():
    return {'status': 'not-grounded', 'method': 'no matching source',
            'label': 'Not source-grounded: nothing in the lecture materials matched.'}
