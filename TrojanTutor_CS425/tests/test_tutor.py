from app.retrieval import retrieve,SLIDES
from app.tutor import answer
from app.algorithms import kruskal,dijkstra,DEMO_NODES,DEMO_MST,DEMO_PATH
import pytest

def test_index_loaded():assert 100<len(SLIDES)<200   # 265 raw pages merged into ~137 slides

def test_mst_retrieval():
    x=retrieve('Kruskal minimum spanning tree cycle',unit='Minimum Spanning Trees');assert x and all(s['unit']=='Minimum Spanning Trees' for s in x)
def test_flow_retrieval():assert retrieve('flow cut capacity',unit='Maximum Flow')
def test_no_match():assert retrieve('zzzxxyyyqqq')==[]
def test_mst():
    x=kruskal(DEMO_NODES,DEMO_MST);assert x['spanning'] and x['total']==10 and len(x['edges'])==4
def test_shortest_paths():
    x=dijkstra(DEMO_NODES,DEMO_PATH,'A');assert x['distances']['E']==10 and x['distances']['B']==3
def test_negative_rejected():
    with pytest.raises(ValueError,match='nonnegative'):dijkstra(['A','B'],[['A','B',-2]],'A')
def test_offline():
    x=answer('Why does Kruskal avoid cycles?','Minimum Spanning Trees',[]);assert x['sources'] and x['mode']=='concept-cards+bm25'


def test_exact_student_cycle_answer_succeeds():
    from fastapi.testclient import TestClient
    from app.main import app
    c=TestClient(app)
    r=c.post('/api/session', params={'unit':'Minimum Spanning Trees'})
    assert r.status_code == 200
    r=c.post('/api/ask',json={'session_id':r.json()['session_id'], 'question':"the treat when the tree becomes a cycle it's no longer possible for it to be an MST"})
    assert r.status_code==200, r.text
    assert isinstance(r.json()['answer'],str)

def test_unexpected_errors_are_json():
    from fastapi.testclient import TestClient
    from app.main import app
    # exercise generic exception handler using a temporary test-only route
    from fastapi import APIRouter
    route_path='/api/_test_server_fault'
    async def raise_fault(): raise RuntimeError('Test-only internal error')
    from fastapi.routing import APIRoute
    route=APIRoute(route_path,raise_fault,methods=['GET'])
    app.router.routes.append(route)
    try:
        c=TestClient(app,raise_server_exceptions=False)
        r=c.get(route_path)
        assert r.status_code==500
        assert r.headers['content-type'].startswith('application/json')
        assert 'detail' in r.json()
        assert 'Test-only' not in r.text
    finally:
        app.router.routes.remove(route)


# ---------- v0.7 RAG / teaching tests ----------
from app.retrieval import find_concepts, CHUNKS, CARDS
from app.tutor import detect_intent, narrate_kruskal, narrate_dijkstra


def _chat(unit, qs):
    h = []; outs = []
    for q in qs:
        r = answer(q, unit, h)
        h += [{'role': 'user', 'content': q}, {'role': 'assistant', 'content': r['answer'], 'concept': r.get('concept_id'), 'intent': r.get('intent')}]
        outs.append(r)
    return outs


def test_animation_frames_are_merged():
    import json, pathlib
    raw = json.loads((pathlib.Path(__file__).resolve().parents[1] / 'data' / 'slides.json').read_text())
    assert len(CHUNKS) < 0.6 * len(raw)
    kr = [c for c in CHUNKS if c['title'].startswith('Kruskal') and c['page_start'] == 23]
    assert kr and kr[0]['page_end'] >= 29


def test_every_card_has_valid_slide_refs_and_fields():
    from app.retrieval import card_sources
    for c in CARDS:
        for k in ('simple', 'analogy', 'example', 'why', 'trap', 'check', 'refs'):
            assert c[k], (c['id'], k)
        assert card_sources(c, c['title']), c['id']


def test_course_terminology_residual_maps_to_auxiliary_digraph():
    assert find_concepts('what is a residual network', 'Maximum Flow')[0]['card']['id'] == 'auxiliary_digraph'


def test_mst_question_returns_definition_not_prim_duplicates():
    r = answer('What is a minimum spanning tree?', 'Minimum Spanning Trees', [])
    assert r['concept_id'] == 'mst'
    assert len({s['id'] for s in r['sources']}) == len(r['sources'])


def test_dijkstra_nonnegative_explains_counterexample():
    r = answer('why does dijkstra need nonnegative edges', 'Shortest Paths', [])
    assert r['concept_id'] == 'dijkstra' and r['intent'] == 'why' and 'minus two' in r['answer']


def test_followup_simplify_uses_previous_concept_and_changes_text():
    a, b = _chat('Minimum Spanning Trees', ['What is Kruskal\'s algorithm?', 'explain it more simply'])
    assert b['concept_id'] == 'kruskal' and b['answer'].split('\n\n')[0] != a['answer'].split('\n\n')[0]


def test_compare_resolves_that_to_previous_concept():
    _, b = _chat('Minimum Spanning Trees', ['What is Kruskal\'s algorithm?', 'what is the difference between that and prim'])
    assert b['intent'] == 'compare' and 'forest' in b['answer'].lower()


def test_demo_narration_matches_verified_algorithms():
    assert 'Total cost 10' in narrate_kruskal()
    d = narrate_dijkstra(); assert 'B 3' in d and 'E 10' in d


def test_cross_unit_question_is_answered_with_note():
    r = answer('why does dijkstra need nonnegative edges', 'Minimum Spanning Trees', [])
    assert r['concept_id'] == 'dijkstra' and 'Shortest Paths unit' in r['answer']


def test_off_topic_gets_scope_message_not_a_wrong_lesson():
    r = answer('what is the capital of france', 'Maximum Flow', [])
    assert r['concept_id'] is None and 'Maximum Flow' in r['answer']


def test_guided_lesson_start_then_next():
    a, b = _chat('Shortest Paths', ['Start the lesson', 'next'])
    assert a['concept_id'] == 'shortest_path' and b['concept_id'] == 'feasible_potential'


def test_spoken_text_is_concise_and_has_no_slide_quote():
    r = answer('what is a cut', 'Maximum Flow', [])
    assert 'From the lecture' in r['answer'] and 'From the lecture' not in r['spoken']


def test_intents():
    assert detect_intent('why does it work') == 'why' and detect_intent('quiz me') == 'quiz'
    assert detect_intent("I don't get it") == 'simplify' and detect_intent('walk me through it') == 'example'


def test_student_statement_gets_self_check_not_a_repeat_lecture():
    r = answer("the treat when the tree becomes a cycle it's no longer possible for it to be an MST", 'Minimum Spanning Trees', [])
    assert r['intent'] == 'answer' and 'new vertices' in r['answer']


def test_answering_a_check_question_compares_with_lecture_reasoning():
    a, b = _chat('Shortest Paths', ["what is dijkstra's algorithm", 'it breaks because a negative edge could improve a node already finished'])
    assert b['intent'] == 'answer' and b['concept_id'] == 'dijkstra'


def test_quiz_with_no_context_starts_at_first_concept():
    r = answer('quiz me on this', 'Minimum Spanning Trees', [])
    assert r['concept_id'] == 'graph_basics' and 'Quick check' in r['answer']


def test_cycle_feedback_is_partial_not_generic_praise():
    r = answer("the treat when the tree becomes a cycle it's no longer possible for it to be an MST",
               'Minimum Spanning Trees', [])
    assert r['intent'] == 'answer'
    assert 'Yes, a spanning tree' in r['answer']
    assert 'new vertices' in r['answer']


def test_deeper_cycle_answer_recognized():
    _, r = _chat('Minimum Spanning Trees', [
        'What is Kruskal?',
        'The edge is redundant because the vertices are already connected, so the cycle adds no connectivity and increases cost.'
    ])
    assert 'Exactly' in r['answer']


def test_uncertain_answer_does_not_claim_correct():
    _, r = _chat('Minimum Spanning Trees', ['what is kruskal', 'I like pizza and graphs are interesting today'])
    assert 'cannot reliably grade' in r['answer']


def test_negative_dijkstra_answer_recognized():
    _, r = _chat('Shortest Paths', ["what is dijkstra's algorithm", 
                   'A negative edge could improve a node after its distance was finalized'])
    assert 'Exactly' in r['answer']


def test_wrong_cycle_claim_corrected():
    _, r = _chat('Minimum Spanning Trees', ['what is kruskal', 'A spanning tree must have a cycle'])
    assert 'Not quite' in r['answer']
