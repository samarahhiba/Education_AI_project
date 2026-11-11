"""Hybrid course retrieval.

Two indexes, one query path:
  1. CONCEPT CARDS (data/concepts.json): plain-language lessons whose `refs` point at
     verified slide pages. Matched by alias phrases + BM25 over the card text.
  2. SLIDE CHUNKS (data/chunks.json): lecture slides with animation frames collapsed
     (see app/ingest.py). Matched by BM25 with stemming, title boost and synonyms.

Public API (kept compatible with the earlier version):
  retrieve(query, unit=None, limit=4) -> list of slide sources with 'excerpt'
  find_concepts(query, unit=None, limit=3) -> ranked concept cards with scores
"""
from pathlib import Path
from collections import Counter
import json, math, re

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = json.loads((ROOT / 'data' / 'chunks.json').read_text(encoding='utf-8'))
CARDS = json.loads((ROOT / 'data' / 'concepts.json').read_text(encoding='utf-8'))
SLIDES = CHUNKS  # backwards-compatible name used by tests

STOP = set('a an the or and of to in for on as is are be with by from we this that at it do does can how why what which when i you your if have has its will not use using there then me my explain tell about mean means please give simply simple plain words like really exactly'.split())
# Students say "residual network", "vertex", "weight"; the lectures say other words.
SYNONYMS = {'vertex': 'node', 'vertices': 'node', 'weight': 'cost', 'weights': 'cost', 'length': 'cost',
            'residual': 'auxiliary', 'cycle': 'circuit', 'cycles': 'circuit', 'edge': 'arc', 'edges': 'arc',
            'relax': 'correct', 'relaxation': 'correct', 'relaxing': 'correct', 'greedy': 'cheapest',
            'dag': 'acyclic', 'mst': 'minimum spanning tree', 'tsp': 'traveling salesman',
            'maxflow': 'maximum flow', 'mincut': 'minimum cut', 'bfs': 'breadth first search',
            'dijkstras': 'dijkstra', 'kruskals': 'kruskal', 'prims': 'prim', 'distance': 'cost'}


def stem(w):
    for suf in ('ations', 'ation', 'ings', 'ing', 'edly', 'ed', 'ies', 'es', 's'):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)] + ('y' if suf == 'ies' else '')
    return w


def tokenize(s, expand=True):
    out = []
    for w in re.findall(r'[a-z0-9]+', s.lower().replace('\u2019', "'")):
        if w in STOP or len(w) < 2:
            continue
        for part in (SYNONYMS.get(w, w).split() if expand else [w]):
            out.append(stem(part))
    return out


def norm_phrase(s):
    return ' '.join(re.findall(r'[a-z0-9]+', s.lower().replace('\u2019', '')))


class BM25:
    def __init__(self, docs):
        self.bags = [Counter(d) for d in docs]
        self.N = len(docs)
        self.df = Counter(k for b in self.bags for k in b)
        self.avg = sum(sum(b.values()) for b in self.bags) / max(1, self.N)

    def score(self, i, terms):
        bag, dl, s = self.bags[i], sum(self.bags[i].values()), 0.0
        for t in set(terms):
            tf = bag[t]
            if tf:
                idf = math.log(1 + (self.N - self.df[t] + .5) / (self.df[t] + .5))
                s += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * dl / self.avg))
        return s


def _chunk_doc(c):
    return tokenize(c['text']) + tokenize(c['title']) * 2     # title boost


def _card_doc(c):
    return tokenize(' '.join([c['title'], c['simple'], c['why'], c['example']]))


CHUNK_IDX = BM25([_chunk_doc(c) for c in CHUNKS])
CARD_IDX = BM25([_card_doc(c) for c in CARDS])
ALIAS = [[norm_phrase(a) for a in c['aliases'] + [c['title']]] for c in CARDS]
CARD_BY_ID = {c['id']: c for c in CARDS}


def find_concepts(query, unit=None, limit=3):
    """Rank concept cards. Alias phrase hits dominate; BM25 breaks ties.
    Cards in the selected unit get a boost but other units are NOT excluded, so a
    cross-unit question can be answered (and the tutor can say where it is covered)."""
    q = norm_phrase(query)
    padded = f' {q} '
    terms = tokenize(query)
    results = []
    for i, c in enumerate(CARDS):
        alias_hits = 0.0
        for a in ALIAS[i]:
            if a and f' {a} ' in padded:
                alias_hits = max(alias_hits, 2.0 + 0.6 * len(a.split()))     # longer phrase = more specific
        bm = CARD_IDX.score(i, terms) if terms else 0.0
        score = alias_hits * 3 + bm
        if score <= 0:
            continue
        if unit and c['unit'] == unit:
            score *= 1.35
        results.append({'card': c, 'score': round(score, 3), 'alias_hit': alias_hits > 0})
    results.sort(key=lambda r: -r['score'])
    return results[:limit]


def _ratio(p):
    return sum(ch.isalpha() or ch == ' ' for ch in p) / max(1, len(p))


def best_bullets(text, query, n=2, maxlen=330, title=''):
    """Pick the bullets/sentences of a slide that best match the query (cleaner than a raw dump):
    drops the repeated slide title, numbered pseudo-code steps and symbol-heavy fragments."""
    terms = set(tokenize(query))
    if title and text.startswith(title):
        text = text[len(title):]
    raw = [p.strip(' \u2022\n') for p in re.split(r'\n\u2022|\n|(?<=[.!?])\s+', text) if len(p.strip()) > 20]
    parts = [p for p in raw if _ratio(p) >= 0.4] or raw
    if not parts:
        return text[:maxlen]
    scored = sorted(range(len(parts)), key=lambda i: (-len(terms & set(tokenize(parts[i]))), -round(_ratio(parts[i]), 1), i))[:n]
    out = ' \u2026 '.join(parts[i] for i in sorted(scored))
    return out[:maxlen].rstrip()


def retrieve(query, unit=None, limit=4, restrict_pages=None):
    terms = tokenize(query)
    if not terms:
        return []
    scored = []
    for i, c in enumerate(CHUNKS):
        if unit and c['unit'] != unit:
            continue
        s = CHUNK_IDX.score(i, terms)
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda z: -z[0])
    out = []
    for s, c in scored[:limit]:
        out.append({**c, 'score': round(s, 3), 'excerpt': best_bullets(c['text'], query, title=c['title'])})
    return out


def card_sources(card, query):
    """Verified slide evidence for a concept card: the slides the card's refs point at."""
    out = []
    for p in card['refs']:
        for c in CHUNKS:
            if c['unit'] == card['unit'] and c['page_start'] <= p <= c['page_end']:
                if all(o['id'] != c['id'] for o in out):
                    out.append({**c, 'score': 99.0, 'excerpt': best_bullets(c['text'], query + ' ' + card['title'], title=c['title'])})
                break
    return out
