"""Full-course mode: every slide is taught, diagrams are consistent, and the numbers match the slides."""
import json, math
from pathlib import Path

import pytest

from app.course import course, outline, check_answer, SKIPPED
from app.algorithms import (brute_force_tsp, nearest_neighbor_tour, ford_sequence, bfs, kruskal, prim, max_flow,
                            min_weight_pairing, augment_path, check_flow)
from app.course import u1, u2, u3, u4
from app.speech import normalize, best_alternative

ROOT = Path(__file__).resolve().parents[1]
C = course()


def test_every_slide_chunk_is_taught_or_explicitly_skipped():
    chunks = json.loads((ROOT / 'data/chunks.json').read_text())
    covered = {c for l in C['lessons'] for c in l['covers']}
    missing = [ch['id'] for ch in chunks if ch['id'] not in covered and ch['id'] not in SKIPPED]
    assert not missing, f'slide chunks not taught: {missing}'
    assert not covered & set(SKIPPED)
    assert len(C['lessons']) >= 30 and sum(len(l['steps']) for l in C['lessons']) >= 200


@pytest.mark.parametrize('les', C['lessons'], ids=lambda l: l['id'])
def test_lesson_steps_are_well_formed_and_draw_valid_ids(les):
    assert les['steps'][0]['draw'][0]['op'] == 'figure' or les['unit'] == 'Problems and Algorithms'
    ids = set()
    for st in les['steps']:
        assert st['say'].strip() and st['text'].strip()
        assert '$' not in st['say'], 'spoken text must not contain math markup'
        for op in st['draw']:
            if op['op'] == 'figure':
                ids = {n['id'] for n in op['figure']['nodes']} | {e['id'] for e in op['figure']['edges']}
                continue
            refs = [op.get('id')] if op['op'] in ('edge', 'node', 'label', 'elabel') else []
            refs += list(op.get('ids', [])) if op['op'] in ('reveal', 'show', 'hide', 'path') else []
            refs += list(op.get('nodes', [])) + list(op.get('to', [])) + ([op['from']] if 'from' in op else [])
            refs += [x for p in op.get('pairs', []) for x in p]
            if op['op'] == 'tour':
                refs += op['ids']
            for r in refs:
                assert r in ids, f"{les['id']}: {op} references {r!r} not in the current figure"
        if 'ask' in st:
            assert st['ask']['expect'] and st['ask']['answer']
        assert all(isinstance(p, int) for p in st['slides'])


def test_outline_and_questions():
    o = outline()
    assert sum(x['questions'] for x in o) >= 30
    assert [x['unit'] for x in o][0] == 'Problems and Algorithms' and o[-1]['unit'] == 'Maximum Flow'


def test_check_answer_verdicts():
    ask = C['by_id']['u2-kruskal']['steps'][4]['ask']
    assert check_answer(ask, 'no, h and k are already connected, it would make a cycle')['verdict'] == 'correct'
    assert check_answer(ask, 'no')['verdict'] == 'partial'
    assert check_answer(ask, 'bananas')['verdict'] == 'unsure'
    assert check_answer(ask, "I don't know")['verdict'] == 'revealed'
    assert 'Yes, exactly' not in check_answer(ask, 'bananas')['feedback']


# ---------- the numbers in the lessons match the slides ----------
def test_unit1_numbers():
    assert round(math.factorial(22) / 2 * 1e-9 / (3600 * 24 * 365.25 * 100)) == 178          # slide 9
    bf = brute_force_tsp(u1.PTS, 'H')
    assert bf['tours_checked'] == math.factorial(len(u1.PTS) - 1) // 2
    assert nearest_neighbor_tour(u1.PTS, 'H')['length'] > 1.2 * bf['length']
    deg = {}
    for a, b in u1.CIRC_E:
        deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
    assert sum(1 for d in deg.values() if d % 2) % 2 == 0


def test_mst_lessons_match_slide_graphs():
    assert kruskal(list(u2.KG), [list(e) for e in u2.KG_E])['total'] == 108                     # red tree, slide 29
    assert prim(list(u2.KG), [list(e) for e in u2.KG_E], 'a')['total'] == 108
    assert kruskal(list(u2.EX), [list(e) for e in u2.EX_E])['total'] == 51
    red = {frozenset(e) for e in [('a', 'b'), ('a', 'd'), ('d', 'g'), ('h', 'g'), ('g', 'k'), ('a', 'f')]}
    assert {frozenset(e[:2]) for e in kruskal(list(u2.KG), [list(e) for e in u2.KG_E])['edges']} == red


def test_shortest_path_lessons_match_slides():
    fb = ford_sequence(list(u3.SD), [list(e) for e in u3.SD_E], 'r',
                       [['ad', 'ba', 'ra', 'rb'], ['ba', 'ad', 'rb', 'ra'], ['rb', 'ba', 'ra', 'ad']])   # slide 66
    assert fb['y'] == {'r': 0, 'a': 2, 'b': 1, 'd': 4} and fb['feasible']
    neg = ford_sequence(list(u3.NEG), [list(e) for e in u3.NEG_E], 'r', [['ra', 'ab', 'bc', 'cd', 'da']])
    assert neg['y']['a'] == 4                                                                     # slide 57: y5a = 4
    from app.algorithms import dijkstra
    assert dijkstra(list(u3.DJ), [list(e) for e in u3.DJ_E], 'r')['distances'] == {'r': 0, 'a': 2, 'p': 3, 'b': 4, 'q': 6}
    assert bfs(list(u3.BF), u3.BF_E, '1')['order'] == ['1', '4', '7', '6', '10', '3', '9', '2', '5', '8', '11']   # slide 115
    pos = {v: k for k, v in enumerate(u3.TOPO_ORDER)}
    assert all(pos[a[0]] < pos[a[1]] for a in u3.TOPO_S)                                          # slide 71 order is topological


def test_flow_lessons_match_slides():
    r = max_flow(list(u4.MF), [list(a) for a in u4.MF_A], 'r', 's')
    assert r['value'] == 4 == r['cut_capacity'] and set(r['cut_R']) == {'r', 'q', 'a'}
    x = {'r>p': 1, 'r>q': 3, 'p>a': 0, 'a>p': 1, 'p>b': 2, 'q>a': 2, 'q>b': 1, 'b>q': 0, 'a>s': 1, 'b>s': 3}
    assert check_flow(list(u4.MF), u4.MF_A, x, 'r', 's') == 4                                      # slide 22 flow
    assert max_flow(list(u4.DIA), [list(a) for a in u4.DIA_A], 'r', 's')['value'] == 1            # slide 15
    with pytest.raises(ValueError):
        augment_path(u4.HW_A, {}, ['r', 'b', 'a', 's'])                                            # a-b reverse needs flow
    _, _, res, M_, Cov = u4.konig_data()
    assert len(M_) == len(Cov) == res['value'] == 3
    assert all(p in Cov or q in Cov for p, q in u4.BP_E)                                           # it is a cover


def test_min_weight_pairing_is_optimal_on_small_sets():
    pts = {k: (i * 37 % 101, i * 59 % 97) for i, k in enumerate('abcdef')}
    L, m = min_weight_pairing(pts, list(pts))
    assert len(m) == 3 and sorted(x for p in m for x in p) == sorted(pts)


# ---------- voice interpretability ----------
@pytest.mark.parametrize('heard,fixed', [
    ('how does crystals algorithm work', 'how does Kruskal algorithm work'),
    ('why does dykstra fail with negative costs', 'why does Dijkstra fail with negative costs'),
    ('what is a die path', 'what is a dipath'),
    ('why did it skip edge bee and dee', 'why did it skip edge b and d'),
    ('what about the arc from are to pee', 'what about the arc from r to p'),
    ('explain the max flow mint cut theorem', 'explain the max flow min cut theorem'),
    ('prove conic theorem', 'prove König theorem'),
    ('I see what you mean', 'I see what you mean'),
    ('is this a crystal clear example', 'is this a crystal clear example'),
])
def test_transcript_normalization(heard, fixed):
    assert normalize(heard) == fixed


def test_best_alternative_prefers_course_vocabulary():
    assert best_alternative([('why does dexter fail', 0.9), ('why does dikstra fail', 0.6)])[0] == 'why does Dijkstra fail'


def test_course_api():
    pytest.importorskip('fastapi')
    from app.main import (session, course_outline, course_lesson, course_check, course_ask, course_progress, speech_normalize,
                          slides, CourseAnswer, CourseQuestion, CourseProgress, Transcript)
    sid = session('Shortest Paths')['session_id']
    assert len(course_outline(sid)['lessons']) == len(C['lessons'])
    assert course_lesson('u3-ford')['title'] == "Ford's algorithm"
    ask_i = next(i for i, s in enumerate(C['by_id']['u3-ford']['steps']) if 'ask' in s)
    assert course_check(CourseAnswer(session_id=sid, lesson_id='u3-ford', step=ask_i, answer='a 2, b 1, d 4'))['verdict'] == 'correct'
    r = course_ask(CourseQuestion(session_id=sid, lesson_id='u2-kruskal', step=6, question='why was that skipped'))
    assert r['engine'] == 'course' and 'h and k' in r['answer']
    r = course_ask(CourseQuestion(session_id=sid, lesson_id='u3-dijkstra', step=4, question='why does dykstra need nonnegative costs'))
    assert r['heard'].startswith('why does Dijkstra') and r['engine'] != 'course' and 'say next' not in r['spoken'].lower()
    course_progress(CourseProgress(session_id=sid, lesson_id='u3-ford', step=8, completed=True))
    assert course_outline(sid)['progress']['u3-ford']['completed']
    assert speech_normalize(Transcript(alternatives=[['what is a die graph', 0.9]]))['text'] == 'what is a digraph'
    assert slides('Minimum Spanning Trees', '23,24')['sources'][0]['page_start'] == 23
