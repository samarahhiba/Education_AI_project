"""Deterministic misconception-driven teaching intervention for CS425.

Research boundary: diagnoses are tentative; student learning is only observed via
answer attempts. Course lesson cards and extracted slide chunks provide evidence.
No model is trained here. Never report mastery from this module.
"""
from .feedback import assess
from .retrieval import CARD_BY_ID
from .pedagogical_retrieval import retrieve_evidence

# Deliberately small, auditable intervention registry, not invented lecture quotations.
INTERVENTIONS = {
    'kruskal': {
        'trigger': 'cycle_connectivity',
        'prerequisite': 'paths and connectivity',
        'counterexample': ('Take vertices A, B, C and edges A–B of weight 2, B–C of weight 3, '
                           'and A–C of weight 8. The first two edges already connect all three vertices. '
                           'Adding A–C creates a cycle and increases the total from 5 to 13 without connecting any new vertex.'),
        'challenge': ('Suppose Kruskal has already accepted A–B (2) and B–C (3). '
                      'It now examines A–C (8). Explain whether it accepts A–C, '
                      'using connectivity rather than only saying "trees have no cycles".'),
        'expected': ('A and C are already connected by A–B–C, so A–C adds no connectivity; '
                     'Kruskal rejects it because it would create a cycle.'),
        'retrieval_query': 'Kruskal cycle property spanning tree connectivity path reject edge',
    },
    'dijkstra': {
        'trigger': 'negative_edges_greedy_invariant',
        'prerequisite': 'edge relaxation and settled distances',
        'counterexample': ('Take directed arcs S→A cost 2, S→B cost 5, and B→A cost −4. '
                           'Dijkstra may settle A at distance 2 before exploring B, '
                           'but the route S→B→A costs 1. This is why the nonnegative-weight assumption matters.'),
        'challenge': ('For S→A (2), S→B (5), B→A (−4), what is the true shortest '
                      'distance from S to A, and which Dijkstra assumption fails?'),
        'expected': ('The distance is 1 by S→B→A. Dijkstra assumes all edge costs '
                     'are nonnegative so a settled distance cannot later improve.'),
        'retrieval_query': 'Dijkstra correctness nonnegative arc costs settled distance relaxation Ford Bellman',
    },
}


def intervene(concept_id, explanation, *, mode='pedagogical', limit=3):
    """Build a contrastive teaching intervention without assuming understanding.

    Unknown concepts or unrecognized statements abstain, rather than hallucinating
    an individualized misconception diagnosis.
    """
    if concept_id not in CARD_BY_ID:
        raise ValueError('unknown concept')
    if not explanation or not explanation.strip():
        raise ValueError('student explanation is required')
    if len(explanation) > 3000:
        raise ValueError('student explanation exceeds 3000 characters')
    card = CARD_BY_ID[concept_id]
    label, feedback = assess(concept_id, explanation)
    strategy = INTERVENTIONS.get(concept_id)
    retrieval_query = (strategy['retrieval_query'] if strategy and label in ('misconception', 'partial')
                       else card['title'] + ' ' + card['why'])
    evidence = retrieve_evidence(retrieval_query, unit=card['unit'], concept=concept_id,
                                 student_explanation=explanation, mode=mode, limit=limit)
    targeted = bool(strategy and label in ('misconception', 'partial'))
    return {
        'concept_id': concept_id,
        'concept_title': card['title'],
        'diagnosis': label,
        'diagnosis_confidence': 'rule-match-only' if label != 'ungraded' else 'abstained',
        'feedback': feedback,
        'instructional_action': 'counterexample-and-transfer' if targeted else 'compare-with-reference',
        'prerequisite': strategy['prerequisite'] if targeted else None,
        'counterexample': strategy['counterexample'] if targeted else None,
        'transfer_question': strategy['challenge'] if targeted else card['check'],
        'reference_reasoning': strategy['expected'] if targeted else card['why'],
        'reassessment_status': 'not_attempted',
        'evidence': evidence['sources'],
        'retrieval_mode': evidence['retrieval_mode'],
        'evidence_status': evidence['sufficiency'],
        'limitations': ('This is tentative rule-based diagnosis, not semantic grading. '
                        'Counterexamples are authored and should be reviewed by a course instructor. '
                        'Retrieved slides are supporting candidates, not automatically verified entailment.'),
    }


def reassess(concept_id, explanation):
    if concept_id not in CARD_BY_ID:
        raise ValueError('unknown concept')
    if not explanation or not explanation.strip():
        raise ValueError('student explanation is required')
    if len(explanation) > 3000:
        raise ValueError('student explanation exceeds 3000 characters')
    label, feedback = assess(concept_id, explanation)
    return {'concept_id': concept_id, 'label': label, 'feedback': feedback,
            'status': 'rule_assessed' if label != 'ungraded' else 'requires_human_review',
            'mastered': None, 'note': 'No mastery inferred from one attempt.'}
