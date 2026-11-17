"""Dual-Coding Canvas: scenes must be faithful to the tested algorithms, and interruptions must
answer about the step on the board."""
import itertools, random

import pytest

from app import tts
from app.algorithms import (kruskal, prim, dijkstra, max_flow, DEMO_NODES, DEMO_MST, DEMO_PATH,
                            DEMO_FLOW_NODES, DEMO_FLOW)
from app.retrieval import CARDS
from app.scenes import build_scene, answer_interruption, SCENE_OF


@pytest.mark.parametrize('card', CARDS, ids=lambda c: c['id'])
def test_every_concept_has_a_well_formed_scene(card):
    sc = build_scene(card['id'])
    assert sc['steps'] and sc['steps'][-1]['say'].startswith('Check yourself')
    edge_ids = {e['id'] for e in (sc['graph'] or {}).get('edges', [])}
    node_ids = {n['id'] for n in (sc['graph'] or {}).get('nodes', [])}
    for st in sc['steps']:
        assert st['say'].strip() and st['why'].strip()
        for w in st['write']:
            assert w['kind'] in ('title', 'line', 'math', 'ok', 'bad', 'note', 'question')
            if w['kind'] == 'math':
                assert w['text'].count('{') == w['text'].count('}')
        for op in st['draw']:
            for i in [op.get('id')] + list(op.get('ids', [])) + list(op.get('nodes', [])):
                if i is not None:
                    assert i in edge_ids | node_ids, (card['id'], op)


def test_kruskal_scene_matches_the_algorithm_and_shows_the_real_cycle():
    sc = build_scene('kruskal')
    res = kruskal(DEMO_NODES, DEMO_MST)
    assert f"Total cost {res['total']}" in ' '.join(s['say'] for s in sc['steps'])
    accepted = set()
    for st in sc['steps']:
        for op in st['draw']:
            if op['op'] == 'edge' and op['state'] == 'accept':
                accepted.add(op['id'])
            if op['op'] == 'path' and op['style'] == 'cycle':
                assert set(op['ids']) <= accepted          # the cycle shown uses only edges already taken
                skipped = next(o['id'] for o in st['draw'] if o['op'] == 'edge' and o['state'] == 'skip')
                ends = {n for i in op['ids'] for n in i.split('-')}
                assert set(skipped.split('-')) <= ends
    assert accepted == {f'{u}-{v}' for u, v, _ in res['edges']}


def test_dijkstra_scene_final_labels_match():
    sc = build_scene('dijkstra')
    labels = {}
    for st in sc['steps']:
        for op in st['draw']:
            if op['op'] == 'label':
                labels[op['id']] = op['text']
    assert labels == {k: f'y={v}' for k, v in dijkstra(DEMO_NODES, DEMO_PATH, 'A')['distances'].items()}


def test_maxflow_scene_ends_with_equal_flow_and_cut():
    sc = build_scene('maxflow_mincut')
    res = max_flow(DEMO_FLOW_NODES, DEMO_FLOW, 'r', 's')
    text = ' '.join(s['say'] for s in sc['steps'])
    assert res['value'] == res['cut_capacity'] == 5 and 'exactly the flow value 5' in text


def _brute_min_cut(nodes, arcs, s, t):
    mids = [n for n in nodes if n not in (s, t)]
    return min(sum(c for u, v, c in arcs if u in R and v not in R)
               for k in range(len(mids) + 1) for S in itertools.combinations(mids, k) for R in [{s, *S}])


def test_max_flow_equals_brute_force_min_cut_on_random_graphs():
    rnd = random.Random(425)
    for _ in range(150):
        nodes = ['s', 'a', 'b', 'c', 'd', 't'][:rnd.randint(3, 6)]
        nodes[-1] = 't'
        arcs = [[u, v, rnd.randint(0, 6)] for u, v in itertools.permutations(nodes, 2)
                if rnd.random() < 0.45 and u != 't' and v != 's']
        r = max_flow(nodes, arcs, 's', 't')
        assert r['value'] == r['cut_capacity'] == _brute_min_cut(nodes, arcs, 's', 't')


def test_max_flow_uses_reverse_arcs_when_needed():
    # BFS takes s-a-b-t first (the only 3-arc path); the optimum needs flow sent back along a-b.
    nodes = ['s', 'a', 'b', 'c', 'd', 't']
    arcs = [['s', 'a', 1], ['a', 'b', 1], ['b', 't', 1], ['s', 'c', 1], ['c', 'b', 1], ['a', 'd', 1], ['d', 't', 1]]
    r = max_flow(nodes, arcs, 's', 't')
    assert r['value'] == 2 == _brute_min_cut(nodes, arcs, 's', 't')
    assert {'arc': 'a>b', 'direction': 'reverse'} in r['steps'][1]['arcs']


def test_prim_and_kruskal_agree_on_random_graphs():
    rnd = random.Random(7)
    for _ in range(100):
        nodes = list('ABCDEFG')[:rnd.randint(2, 7)]
        edges = [[u, v, rnd.randint(1, 9)] for u, v in itertools.combinations(nodes, 2) if rnd.random() < 0.6]
        edges += [[nodes[i], nodes[i + 1], rnd.randint(1, 9)] for i in range(len(nodes) - 1)]   # connected
        assert prim(nodes, edges, nodes[0])['total'] == kruskal(nodes, edges)['total']


def test_interruptions_answer_about_the_board():
    sc = build_scene('kruskal')
    skip_i = next(i for i, s in enumerate(sc['steps']) if any(o.get('state') == 'skip' for o in s['draw']))
    r = answer_interruption(sc, skip_i + 1, 'wait, why did it skip A-B?')
    assert r['step'] == skip_i and 'already joined' in r['answer'] and r['draw'][0]['ids'] == ['A-B']
    assert 'never had to consider' in answer_interruption(sc, len(sc['steps']) - 1, 'what about C to E?')['answer']
    assert answer_interruption(sc, 4, 'why?')['step'] == 4
    assert answer_interruption(sc, 4, 'how does dijkstra handle negative arcs in general graphs?') is None
    flow = build_scene('maxflow_mincut')
    assert answer_interruption(flow, 6, 'why is a to c full?')['draw'][0]['ids'] == ['a-c']


def test_canvas_api_answers_from_scene_or_falls_back():
    pytest.importorskip('fastapi')
    from app.main import canvas_ask, session, CanvasQuestion, scene, scenes
    sid = session('Minimum Spanning Trees')['session_id']
    r = canvas_ask(CanvasQuestion(session_id=sid, concept_id='kruskal', step=7, question='why did it skip A-B?'))
    assert r['engine'] == 'canvas' and r['grounding']['status'] == 'lecture-grounded'
    r = canvas_ask(CanvasQuestion(session_id=sid, concept_id='kruskal', step=3, question='how does prim work?'))
    assert r['engine'] == 'cards' and r['concept_id'] == 'prim'
    assert len(scenes()['scenes']) == len(CARDS) and scene('dijkstra')['graph']['directed']


def test_scene_kinds_cover_all_three_algorithm_units():
    assert {SCENE_OF[c] for c in ('kruskal', 'dijkstra', 'maxflow_mincut')} == {'kruskal', 'dijkstra', 'maxflow'}


def test_neural_tts_is_off_by_default_and_caches(tmp_path, monkeypatch):
    assert tts.config() is None
    with pytest.raises(tts.TTSUnavailable):
        tts.synthesize('hello')
    monkeypatch.setattr(tts, 'CACHE', tmp_path)
    calls = []
    fake = lambda url, headers, body: calls.append(body) or b'ID3fake'
    assert tts.synthesize('Edge B C costs 1.', transport=fake) == b'ID3fake'
    assert tts.synthesize('Edge B C costs 1.', transport=fake) == b'ID3fake'
    assert len(calls) == 1 and calls[0]['input'] == 'Edge B C costs 1.'
