"""Offline evaluation of retrieval and concept resolution against the draft gold sets.

  python -m eval.run_eval               # print a table, write eval/results/latest.json + .md
  python -m eval.run_eval --no-unit     # retrieval without the unit filter (harder setting)

Retrieval metrics (per mode): Recall@1/3/5 (= hit rate: at least one relevant chunk in top-k),
MRR@10, nDCG@5 with binary relevance. A chunk is relevant if its page range intersects the
item's relevant_pages within the same unit.

Concept resolution: top-1 accuracy of the tutor's concept matcher (alias + BM25), which decides
which lesson card is taught. Gold labels are UNREVIEWED drafts; treat numbers as engineering
regression checks, not research results.
"""
from pathlib import Path
import argparse, json, math, time

from app.retrieval import CHUNKS, find_concepts
from app.pedagogical_retrieval import rank_ids

HERE = Path(__file__).resolve().parent
MODES = ('bm25', 'dense', 'hybrid')


def _relevant(chunk, item):
    if chunk['unit'] != item['unit']:
        return False
    return any(chunk['page_start'] <= p <= chunk['page_end'] for p in item['relevant_pages'])


def evaluate_retrieval(modes=MODES, unit_filter=True, gold=HERE / 'retrieval_gold.json'):
    items = json.loads(Path(gold).read_text())['items']
    out = {}
    from app.embeddings import get_index
    get_index()                       # build embeddings once, outside the timed loop
    for mode in modes:
        agg = {'recall@1': 0, 'recall@3': 0, 'recall@5': 0, 'mrr@10': 0.0, 'ndcg@5': 0.0}
        misses, backend, t0 = [], None, time.perf_counter()
        for it in items:
            order, backend = rank_ids(it['query'], mode, it['unit'] if unit_filter else None)
            rel = [_relevant(CHUNKS[i], it) for i in order[:10]]
            first = next((k for k, r in enumerate(rel) if r), None)
            for k in (1, 3, 5):
                agg[f'recall@{k}'] += first is not None and first < k
            agg['mrr@10'] += 1 / (first + 1) if first is not None else 0
            n_rel = sum(_relevant(c, it) for c in CHUNKS)
            dcg = sum(1 / math.log2(k + 2) for k, r in enumerate(rel[:5]) if r)
            idcg = sum(1 / math.log2(k + 2) for k in range(min(5, n_rel)))
            agg['ndcg@5'] += dcg / idcg if idcg else 0
            if first is None or first >= 5:
                misses.append(it['id'])
        n = len(items)
        out[mode] = {**{k: round(v / n, 3) for k, v in agg.items()}, 'n': n, 'backend': backend,
                     'ms_per_query': round(1000 * (time.perf_counter() - t0) / n, 2), 'misses@5': misses}
    return out


def evaluate_concepts(gold=HERE / 'concept_gold.json'):
    items = json.loads(Path(gold).read_text())['items']
    correct, wrong = 0, []
    for it in items:
        ranked = find_concepts(it['query'], it['unit'], limit=1)
        got = ranked[0]['card']['id'] if ranked else None
        ok = it['expected'] if isinstance(it['expected'], list) else [it['expected']]
        if got in ok:
            correct += 1
        else:
            wrong.append({'id': it['id'], 'query': it['query'], 'expected': it['expected'], 'got': got})
    return {'top1_accuracy': round(correct / len(items), 3), 'n': len(items), 'errors': wrong}


def evaluate_heldout():
    """Held-out: real assignment exercises (labelled in data/exercise_map.json before evaluation).
    covered exercises  -> is the top concept card one of the acceptable cards?
    uncovered (A5/A6 matching, TSP approximation; A0 logic) -> does the tutor decline instead of teaching a card?
    integrity guard    -> recall on full exercise text; false positives on ordinary gold questions."""
    from app.exercises import EXERCISES, homework_match, uncovered_topic, clean_statement
    from app.retrieval import CARD_BY_ID
    from app.tutor import MIN_BM25_ONLY
    cov_ok = cov_n = unc_ok = unc_n = 0
    errors = []
    for ex in EXERCISES:
        text = clean_statement(ex, limit=2000)
        if ex['concepts']:
            cov_n += 1
            unit = CARD_BY_ID[ex['concepts'][0]]['unit']
            r = find_concepts(text, unit, limit=1)
            got = r[0]['card']['id'] if r else None
            if got in ex['concepts']:
                cov_ok += 1
            else:
                errors.append({'id': ex['id'], 'expected': ex['concepts'], 'got': got})
        elif not ex['id'].startswith('A0.'):
            unc_n += 1
            r = find_concepts(text, None, limit=1)
            declined = uncovered_topic(text) is not None or not r or (not r[0]['alias_hit'] and r[0]['score'] < MIN_BM25_ONLY)
            unc_ok += declined
            if not declined:
                errors.append({'id': ex['id'], 'expected': 'decline (not covered)', 'got': r[0]['card']['id']})
    guard_hits = sum(homework_match(ex['text']) is not None for ex in EXERCISES)
    ordinary = [it['query'] for g in ('retrieval_gold.json', 'concept_gold.json')
                for it in json.loads((HERE / g).read_text())['items']]
    fp = [q for q in ordinary if homework_match(q)]
    return {'covered_top1': round(cov_ok / max(1, cov_n), 3), 'n_covered': cov_n,
            'uncovered_declined': round(unc_ok / max(1, unc_n), 3), 'n_uncovered': unc_n,
            'guard_recall': round(guard_hits / max(1, len(EXERCISES)), 3), 'n_exercises': len(EXERCISES),
            'guard_false_positives': len(fp), 'n_ordinary_questions': len(ordinary), 'errors': errors}


def to_markdown(report):
    lines = ['# Retrieval & concept-resolution evaluation', '',
             f"Chunks: {report['n_chunks']} · gold: draft, **unreviewed** · unit filter: {report['unit_filter']}", '',
             '| mode | backend | R@1 | R@3 | R@5 | MRR@10 | nDCG@5 | ms/query |', '|---|---|---|---|---|---|---|---|']
    for m, r in report['retrieval'].items():
        lines.append(f"| {m} | {r['backend']} | {r['recall@1']} | {r['recall@3']} | {r['recall@5']} | "
                     f"{r['mrr@10']} | {r['ndcg@5']} | {r['ms_per_query']} |")
    h = report.get('heldout')
    if h:
        lines += ['', '## Held-out: assignment exercises (labels fixed before evaluation)', '',
                  f"- Covered exercises, correct lesson card top-1: **{h['covered_top1']}** (n={h['n_covered']})",
                  f"- Uncovered exercises (A5/A6 topics with no lecture deck), tutor declines: **{h['uncovered_declined']}** (n={h['n_uncovered']})",
                  f"- Homework guard recall on full exercise text: **{h['guard_recall']}** (n={h['n_exercises']}); "
                  f"false positives on {h['n_ordinary_questions']} ordinary questions: **{h['guard_false_positives']}**"]
        if h['errors']:
            lines += ['', 'Held-out errors:'] + [f"- {e['id']}: expected {e['expected']}, got `{e['got']}`" for e in h['errors']]
    c = report['concepts']
    lines += ['', f"Concept resolution top-1 accuracy (dev set, used while tuning): **{c['top1_accuracy']}** (n={c['n']})"]
    if c['errors']:
        lines += ['', 'Errors:'] + [f"- `{e['query']}` → expected `{e['expected']}`, got `{e['got']}`" for e in c['errors']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-unit', action='store_true')
    ap.add_argument('--out', default=str(HERE / 'results'))
    a = ap.parse_args(argv)
    report = {'n_chunks': len(CHUNKS), 'unit_filter': not a.no_unit,
              'retrieval': evaluate_retrieval(unit_filter=not a.no_unit), 'concepts': evaluate_concepts(),
              'heldout': evaluate_heldout()}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = 'latest' if not a.no_unit else 'latest_no_unit'
    (out / f'{tag}.json').write_text(json.dumps(report, indent=1))
    (out / f'{tag}.md').write_text(to_markdown(report))
    print(to_markdown(report))


if __name__ == '__main__':
    main()
