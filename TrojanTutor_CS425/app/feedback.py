"""Conservative, interpretable feedback on a few CS425 misconceptions.

This is NOT semantic grading: only high-precision patterns receive a correctness
judgment. Everything else gets an explicit ungraded comparison prompt.
"""
import re


def _normalize(s):
    return re.sub(r"[^a-z0-9\s]", " ", s.lower()).replace('  ', ' ')


def assess(concept_id, student_text):
    """Return (label, feedback) where label is correct/partial/misconception/ungraded."""
    s = _normalize(student_text)
    cycle = bool(re.search(r'\b(cycle|cycles|loop|loops)\b', s))
    avoids = bool(re.search(r'\b(no|not|never|avoid|avoiding|skip|skips|reject|remove|removing|cannot|can t|without)\b', s))
    connects = bool(re.search(r'\b(connect|connected|connectivity|component|components|reachable)\b', s))
    redundant = bool(re.search(r'\b(redundant|unnecessary|extra|adds? nothing|doesn t help|does not help)\b', s))
    already = bool(re.search(r'\balready\b', s))
    cost = bool(re.search(r'\b(cost|weight|expensive|minimum|cheapest)\b', s))
    if concept_id in ('kruskal', 'mst') and cycle:
        # Check recognizable false claims before the broad partial-credit rule.
        if re.search(r'\b(must|needs?|requires?|should)\b.{0,40}\b(cycle|loop)\b', s) and not avoids:
            return 'misconception', ('Not quite. A spanning tree cannot contain a cycle. '
                   'A cycle-closing edge can be removed without disconnecting the graph. '
                   'What does that tell us about its cost?')
        if re.search(r'\b(cycle|loop)\b.{0,35}\b(is|are)\b.{0,15}\b(required|necessary|needed|good)\b', s):
            return 'misconception', ('A cycle is not required in a spanning tree. '
                   'If an edge joins vertices already connected by a path, what new connectivity does it add?')
        if (connects and (already or redundant or avoids)) or (redundant and cost):
            return 'correct', ('Exactly—the cycle-closing edge adds no new connectivity. '
                   'Removing it preserves a connected graph and, for positive edge costs, lowers the cost. '
                   'How does Kruskal detect that the endpoints are already connected?')
        if avoids or re.search(r'\b(tree|mst)\b', s):
            return 'partial', ('Yes, a spanning tree must have no cycles. That is the definition, '
                   'but there is a deeper reason: an edge closing a cycle connects no new vertices. '
                   'Removing it preserves connectivity and, for positive edge costs, reduces the total cost. '
                   'Why does Kruskal check whether two endpoints are already connected?')
    if concept_id == 'dijkstra':
        neg = bool(re.search(r'\b(negative|minus|below zero)\b', s))
        finalized = bool(re.search(r'\b(final|finalized|settled|scanned|finished|locked|visited)\b', s))
        improved = bool(re.search(r'\b(improve|shorter|lower|reduce|cheaper|decrease|update)\b', s))
        if neg and finalized and improved:
            return 'correct', ('Exactly. A negative arc can reveal a shorter route to a node '
                   'after Dijkstra has settled it. That breaks its greedy correctness argument. '
                   'Would Ford–Bellman make the same assumption?')
        if neg:
            return 'partial', ('You identified the key condition: nonnegative arc costs. '
                   'More precisely, a negative arc can improve a distance after a node is settled. '
                   'Why does settling a node normally make its distance final?')
    return 'ungraded', ('I cannot reliably grade that answer with the current rule-based baseline. '
            'Here is the lecture reasoning to compare against your response:')
