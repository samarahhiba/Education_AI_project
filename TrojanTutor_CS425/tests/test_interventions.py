from app.main import intervention, intervention_reassessment, InterventionRequest, ReassessmentRequest
from fastapi import HTTPException
import pytest
from app.interventions import intervene, reassess


def test_misconception_prompts_transfer_question_with_lecture_evidence():
    r=intervene('kruskal', 'A spanning tree needs a cycle')
    assert r['diagnosis']=='misconception'
    assert r['instructional_action']=='counterexample-and-transfer'
    assert 'connect' in r['transfer_question'].lower()
    assert r['evidence']
    assert all('pages' in x for x in r['evidence'])


def test_dijkstra_negative_edge_counterexample():
    r=intervene('dijkstra', 'Negative weights can break Dijkstra')
    assert r['instructional_action']=='counterexample-and-transfer'
    assert '−4' in r['counterexample']
    assert r['reassessment_status']=='not_attempted'


def test_unknown_or_unguarded_claim_abstains():
    r=intervene('kruskal','Purple bananas are running')
    assert r['diagnosis']=='ungraded'
    assert r['counterexample'] is None
    assert reassess('kruskal','Purple bananas are running')['mastered'] is None


def test_intervention_api_and_validation():
    r=intervention(InterventionRequest(concept_id='kruskal',student_explanation='A spanning tree needs a cycle'))
    assert r['evidence']
    with pytest.raises(HTTPException) as exc:
        intervention(InterventionRequest(concept_id='missing',student_explanation='wrong'))
    assert exc.value.status_code==400
    r=intervention_reassessment(ReassessmentRequest(concept_id='kruskal',student_explanation='Cycles are necessary'))
    assert r['mastered'] is None
