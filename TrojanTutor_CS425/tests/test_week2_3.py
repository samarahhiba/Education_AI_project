"""Week 2-3 acceptance tests: streaming, equations, session context, ingestion & permissions,
embeddings, citations/grounding, optional LLM engine, assignments, evaluation floors."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

import pytest

from app import engine, grounding, llm
from app.exercises import EXERCISES, homework_match, uncovered_topic, practice_for
from app.ingest import check_manifest, load_manifest, split_exercises
from app.pedagogical_retrieval import retrieve_evidence, rank_ids
from app.retrieval import CARDS, CHUNKS, CARD_BY_ID, card_sources
from app.sessions import SessionStore
from app.tutor import answer, guard

ROOT = Path(__file__).resolve().parents[1]


# ---------------- Week 2: streaming ----------------
def test_stream_event_order_and_text_matches_final_answer():
    evs = list(engine.respond_stream('how does dijkstra work', 'Shortest Paths', []))
    names = [e for e, _ in evs]
    assert names[0] == 'meta' and names[-1] == 'done' and 'delta' in names
    streamed = ''.join(d['text'] for e, d in evs if e == 'delta')
    assert streamed == evs[-1][1]['answer']
    assert evs[0][1]['concept_id'] == 'dijkstra'


def test_engine_validation_and_unconfigured_llm_notice():
    with pytest.raises(ValueError):
        list(engine.respond_stream('x', 'Shortest Paths', [], engine='gpt'))
    r = engine.respond('what is dijkstra', 'Shortest Paths', [], engine='llm')
    assert r['engine'] == 'cards' and r['notices']


# ---------------- Week 2: equations ----------------
def test_formulas_shown_on_screen_but_not_spoken():
    r = answer('what is a feasible potential', 'Shortest Paths', [])
    assert '$$' in r['answer'] and 'y_v + c_{vw}' in r['answer']
    assert '$' not in r['spoken'] and 'formal statement is on screen' in r['spoken']


def test_formula_refs_point_at_slides_in_the_cards_unit():
    for c in CARDS:
        f = c.get('formula')
        if f:
            assert f['tex'].count('{') == f['tex'].count('}'), c['id']
            assert any(ch['unit'] == c['unit'] and ch['page_start'] <= f['ref'] <= ch['page_end'] for ch in CHUNKS), c['id']


def test_katex_is_vendored_for_offline_math():
    for p in ('katex.min.js', 'katex.min.css', 'contrib/auto-render.min.js'):
        assert (ROOT / 'static/vendor/katex' / p).exists()


# ---------------- Week 2: session context ----------------
def test_sessions_persist_context_across_unit_switch(tmp_path):
    db = tmp_path / 's.sqlite3'
    st = SessionStore(str(db))
    sid = st.create('Minimum Spanning Trees')
    r = answer('how does kruskal work', 'Minimum Spanning Trees', st.history(sid))
    st.append(sid, 'how does kruskal work', r, 'Minimum Spanning Trees')
    st.set_unit(sid, 'Shortest Paths')
    st2 = SessionStore(str(db))                       # "server restart"
    assert st2.get(sid)['unit'] == 'Shortest Paths'
    h = st2.history(sid)
    assert h[-1]['concept'] == 'kruskal'
    follow = answer('why?', 'Shortest Paths', h)       # follow-up still resolves against the previous concept
    assert follow['concept_id'] == 'kruskal'
    s = st2.summary(sid)
    assert s['concepts_covered'] == ['kruskal'] and s['grounding_counts'] == {'lecture-grounded': 1}
    assert st2.delete(sid) and st2.get(sid) is None


# ---------------- Week 3: ingestion & permission boundary ----------------
def test_manifest_hashes_verify_and_tampering_is_refused(tmp_path):
    ok, problems = check_manifest()
    assert len(ok) == 11 and not problems
    mat = tmp_path / 'm'
    shutil.copytree(ROOT / 'course_materials', mat)
    with open(mat / '2.1 Minimum Spanning Trees (1).pdf', 'ab') as f:
        f.write(b'tampered')
    (mat / 'unknown.pdf').write_bytes(b'%PDF-1.4')
    _, problems = check_manifest(mat)
    assert any('HASH MISMATCH' in p for p in problems) and any('UNLISTED' in p for p in problems)


def test_every_chunk_carries_permission_status():
    assert CHUNKS and all(c['permission'] in ('approved', 'pending') for c in CHUNKS)


def test_shared_deployment_excludes_unapproved_material():
    code = ('from app.retrieval import CHUNKS; from app.tutor import answer;'
            'r = answer("how does kruskal work", "Minimum Spanning Trees", []);'
            'print(len(CHUNKS), len(r["sources"]))')
    env = {**os.environ, 'TROJANTUTOR_DEPLOYMENT': 'shared', 'TROJANTUTOR_SESSION_DB': ':memory:'}
    out = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    assert out.stdout.split() == ['0', '0']            # nothing is approved yet, so nothing is quotable


def test_course_pdfs_are_not_under_the_static_mount():
    assert not list((ROOT / 'static').rglob('*.pdf'))


# ---------------- Week 3: embeddings & retrieval modes ----------------
@pytest.mark.parametrize('mode', ['bm25', 'dense', 'hybrid', 'pedagogical'])
def test_all_retrieval_modes_return_unit_scoped_provenance(mode):
    r = retrieve_evidence('why does kruskal reject an edge that closes a cycle', 'Minimum Spanning Trees',
                          concept='kruskal', student_explanation='a spanning tree needs a cycle', mode=mode)
    assert r['sources'] and all(s['unit'] == 'Minimum Spanning Trees' and 'pages' in s for s in r['sources'])


def test_dense_index_is_local_lsa_and_does_not_invent_matches():
    order, backend = rank_ids('max flow min cut theorem', 'dense', 'Maximum Flow')
    assert backend == 'lsa' and order
    assert rank_ids('zzzxxyyyqqq', 'hybrid')[0] == []


# ---------------- Week 3: citations & grounding ----------------
def test_citation_checker_flags_invalid_and_unsupported_citations():
    srcs = card_sources(CARD_BY_ID['dijkstra'], 'dijkstra running time')
    good = 'If all costs are nonnegative, Dijkstra scans the unscanned node with minimum y [1]. Why does that make y final?'
    assert grounding.for_generated(good, srcs)['status'] == 'lecture-grounded'
    bad = 'Dijkstra was invented by Edsger in a cafe in Amsterdam in 1956 [1]. It also handles negative cycles [7].'
    g = grounding.for_generated(bad, srcs)
    assert g['status'] == 'partially-grounded' and g['invalid_citations'] == [7] and g['weak_citations']
    assert grounding.for_generated('No citations at all here, just a claim about flows.', srcs)['status'] == 'not-grounded'


def test_every_card_answer_has_a_grounding_label():
    for q, u in [('what is an mst', 'Minimum Spanning Trees'), ('qwerty asdf', 'Maximum Flow'),
                 ('the photosynthesis of graphs', 'Shortest Paths')]:
        g = answer(q, u, [])['grounding']
        assert g['status'] in ('lecture-grounded', 'retrieved-only', 'not-grounded', 'partially-grounded') and g['label']


# ---------------- optional LLM engine (fake transports, no network) ----------------
def _anthropic_sse(text):
    yield 'event: message_start'
    yield 'data: {"type":"message_start"}'
    for w in re.findall(r'\S+\s*', text):
        yield 'data: ' + json.dumps({'type': 'content_block_delta', 'index': 0,
                                     'delta': {'type': 'text_delta', 'text': w}})
    yield 'data: {"type":"message_stop"}'


def test_llm_engine_streams_validates_citations_and_speaks_clean_text():
    captured = {}
    reply = ('A cut capacity bounds every flow because all flow from $r$ to $s$ must cross the cut [1]. '
             '$$f_x(s) \\le u(\\delta(R))$$ What happens when a flow saturates every arc of some cut?')

    def transport(url, headers, body):
        captured.update(body)
        return _anthropic_sse(reply)
    evs = list(engine.respond_stream('why is a cut an upper bound on flow', 'Maximum Flow', [], 'llm', transport=transport))
    done = evs[-1][1]
    assert done['engine'] == 'llm' and done['answer'] == reply.strip()
    assert done['grounding']['citations'] and not done['grounding']['invalid_citations']
    assert '[1]' not in done['spoken'] and '$$' not in done['spoken']
    prompt = captured['messages'][-1]['content']
    assert 'LECTURE SOURCES' in prompt and '[1]' in prompt and 'Only' in captured['system'].replace('ONLY', 'Only')


def test_llm_openai_format_parses():
    cfg = {'provider': 'openai', 'url': 'test://', 'key': '', 'model': 'm'}
    lines = ['data: ' + json.dumps({'choices': [{'delta': {'content': t}}]}) for t in ('Hel', 'lo')] + ['data: [DONE]']
    assert ''.join(llm.stream('s', [{'role': 'user', 'content': 'q'}], transport=lambda *a: lines, cfg=cfg)) == 'Hello'


def test_llm_failure_falls_back_to_cards():
    def broken(*a):
        raise llm.LLMUnavailable('HTTPError 529')
        yield
    evs = list(engine.respond_stream('how does prim work', 'Minimum Spanning Trees', [], 'llm', transport=broken))
    assert ('replace' in [e for e, _ in evs]) and evs[-1][1]['engine'] == 'cards (llm-fallback)'


def test_llm_never_sees_homework_or_uncovered_requests():
    def boom(*a):
        raise AssertionError('LLM must not be called')
    hw = next(e for e in EXERCISES if e['id'] == 'A4.E5')['text']
    for q in (hw, 'explain the blossom algorithm'):
        r = engine.respond(q, 'Maximum Flow', [], 'llm', transport=boom)
        assert r['engine'] == 'cards'


def test_llm_disabled_by_default():
    assert llm.config() is None


# ---------------- assignments: integrity guard, coverage, practice ----------------
def test_exercise_parser_and_index():
    assert len(EXERCISES) >= 45
    ex = {e['id']: e for e in EXERCISES}
    assert ex['A4.E1']['points'] == 10 and 'Trinity' in ex['A4.E1']['text']
    assert ex['A4.E6']['optional'] and not ex['A4.E1']['optional']
    assert ex['A1.E3']['has_figure']
    sample = 'Exercise 1 . . . . . . . . 5 points\nDo X.\nOptional exercises\nExercise 2 . . . . . . 0 points\nDo Y.'
    a, b = split_exercises(sample, 'A9')
    assert (a['id'], a['optional'], b['optional']) == ('A9.E1', False, True) and 'Optional' not in a['text']


def test_homework_guard_gives_hints_not_solutions():
    hw = next(e for e in EXERCISES if e['id'] == 'A2.E3')['text']
    r = answer(hw, 'Minimum Spanning Trees', [])
    assert r['intent'] == 'homework-hint' and r['homework_match'] == 'A2.E3'
    assert "won't write out a solution" in r['answer'] and 'Exercise 3' in r['answer']
    assert homework_match('how does kruskal work') is None
    # a paraphrase of A2.E3 is still that exercise ...
    assert homework_match('why is every MST also a minimum bottleneck spanning tree, is the converse true?')['exercise']['id'] == 'A2.E3'
    # ... but a conceptual question about the same topic is not
    assert homework_match('why does a minimum spanning tree never contain a cycle when all edge costs are positive') is None


def test_coverage_gap_declines_instead_of_teaching_euclidean_matching():
    r = answer('can you explain the tutte berge formula for matchings', 'Maximum Flow', [])
    assert r['intent'] == 'coverage-gap' and r['concept_id'] is None and r['grounding']['status'] == 'not-covered'
    slides = ' '.join(c['text'].lower() for c in CHUNKS)
    for term in json.loads((ROOT / 'data/coverage.json').read_text())['terms']:
        assert term not in slides, f'{term} is now in the slides; remove it from data/coverage.json'


def test_practice_poses_a_related_exercise_and_does_not_repeat():
    r1 = answer('give me a practice problem on max flow min cut', 'Maximum Flow', [])
    assert r1['intent'] == 'practice' and r1['exercise']
    h = [{'role': 'assistant', 'content': r1['answer'], 'concept': r1['concept_id'], 'exercise': r1['exercise']}]
    r2 = answer('give me another practice problem', 'Maximum Flow', h)
    assert r2['exercise'] != r1['exercise']
    assert practice_for('kruskal')['id'].startswith('A')


def test_student_solutions_are_not_ingested():
    files = [s['file'] for s in load_manifest()['sources']]
    assert not any('solution' in f.lower() or 'summary' in f.lower() for f in files)


# ---------------- evaluation floors (regression guards, not research claims) ----------------
def test_retrieval_and_concept_floors():
    from eval.run_eval import evaluate_retrieval, evaluate_concepts, evaluate_heldout
    r = evaluate_retrieval(modes=('bm25', 'hybrid'))
    assert r['bm25']['recall@5'] >= 0.95 and r['bm25']['mrr@10'] >= 0.78
    assert r['hybrid']['recall@5'] >= 0.93
    assert evaluate_concepts()['top1_accuracy'] >= 0.9
    h = evaluate_heldout()
    assert h['covered_top1'] >= 0.65 and h['guard_false_positives'] == 0 and h['guard_recall'] >= 0.85
