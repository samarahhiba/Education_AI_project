import pytest
from fastapi import HTTPException
from app.pedagogical_retrieval import retrieve_evidence
from app.main import evidence, EvidenceRequest

def test_baseline_retrieval_cites_original_slides():
    response = retrieve_evidence('Kruskal cycle minimum spanning tree', 'Minimum Spanning Trees', mode='bm25')
    assert response['sources']
    assert all(s['unit'] == 'Minimum Spanning Trees' for s in response['sources'])
    assert all('page_start' in s and 'page_end' in s for s in response['sources'])

def test_pedagogical_diagnosis_is_tentative():
    response = retrieve_evidence('Why avoid cycles?', 'Minimum Spanning Trees',
              'kruskal', 'A spanning tree needs a cycle', 'pedagogical')
    assert response['diagnosis'] in ('partial', 'misconception', 'ungraded')
    assert response['sources']

def test_api_evidence_and_invalid_mode():
    result = evidence(EvidenceRequest(query='Dijkstra negative weights',mode='bm25'))
    assert result['sources']
    with pytest.raises(HTTPException) as exc:
        evidence(EvidenceRequest(query='x',mode='invalid'))
    assert exc.value.status_code==400

def test_absent_match_abstains():
    x=retrieve_evidence('zzzxxyyyqqq',mode='bm25')
    assert x['sufficiency']=='insufficient' and not x['sources']
