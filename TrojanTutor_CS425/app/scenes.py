"""Dual-Coding Canvas scenes: lessons where speech, board writing and drawing happen together.

A scene is a list of steps. Each step is ONE thing the tutor says, and what appears while it is said:

  say    the spoken sentence(s): short, conversational, written for the ear
  write  lines for the whiteboard: {'text', 'kind': title|line|math|ok|bad|note|question}
  draw   graph actions applied as the sentence starts (see OPS)
  why    a ready answer if the student interrupts on this step ("why was that edge skipped?")
  edges  edge ids this step is about (lets an interruption find the right step)

Every number drawn or spoken in an algorithm scene comes from the tested code in app/algorithms.py
(never from a language model). Concept scenes without a graph are built from the authored lesson
card, so they say nothing the card does not.

Draw OPS (applied in order, state persists across steps; the client can rebuild any step):
  reveal   {'ids': [...]}                 make edges/nodes visible (animated draw-in)
  edge     {'id', 'state'}                plain | current | accept | skip | tree | candidate | augment | cut | full
  node     {'id', 'state'}                plain | current | settled | tree | source | sink
  label    {'id', 'text'}                 small label next to a node (distance labels y_v)
  elabel   {'id', 'text'}                 edge label (cost, or flow/capacity "x/u")
  path     {'ids': [...], 'style'}        temporary emphasis: cycle | augment
  shade    {'nodes': [...], 'label'}      shaded region (a cut's side R or U)
  clear    {}                             drop temporary emphasis (current/path/candidate)
"""
from collections import deque

from .algorithms import (kruskal, prim, dijkstra, max_flow, DEMO_NODES, DEMO_MST, DEMO_PATH,
                         DEMO_FLOW_NODES, DEMO_FLOW)
from .retrieval import CARD_BY_ID, card_sources
from .tutor import first_sentence

W, H = 560, 320
POS_MST = {'A': (70, 160), 'B': (220, 60), 'C': (220, 260), 'D': (400, 60), 'E': (470, 230)}
POS_PATH = {'A': (60, 165), 'B': (210, 60), 'C': (210, 270), 'D': (380, 270), 'E': (490, 140)}
POS_FLOW = {'r': (55, 160), 'a': (210, 60), 'b': (210, 260), 'c': (380, 160), 's': (510, 160)}

SCENE_OF = {'kruskal': 'kruskal', 'mst': 'kruskal', 'tree_forest': 'kruskal', 'prim': 'prim',
            'cut': 'cut', 'mst_correctness': 'cut', 'dijkstra': 'dijkstra', 'shortest_path': 'dijkstra',
            'feasible_potential': 'dijkstra', 'flow': 'maxflow', 'augmenting_path': 'maxflow',
            'auxiliary_digraph': 'maxflow', 'shortest_augmenting': 'maxflow', 'maxflow_mincut': 'maxflow',
            'cut_capacity': 'maxflow'}


def _n(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def _graph(nodes, edges, pos, directed, label_fmt):
    return {'width': W, 'height': H, 'directed': directed,
            'nodes': [{'id': n, 'x': pos[n][0], 'y': pos[n][1]} for n in nodes],
            'edges': [{'id': f'{u}-{v}', 'u': u, 'v': v, 'label': label_fmt(w)} for u, v, w in edges]}


def _eid(edges, u, v, directed=False):
    for a, b, _ in edges:
        if (a, b) == (u, v) or (not directed and (a, b) == (v, u)):
            return f'{a}-{b}'
    raise KeyError((u, v))


def _forest_path(chosen, u, v):
    """Path u..v using already-chosen edges (the reason Kruskal rejects an edge)."""
    adj = {}
    for a, b, _ in chosen:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    prev, q = {u: None}, deque([u])
    while q:
        x = q.popleft()
        for y in adj.get(x, []):
            if y not in prev:
                prev[y] = x
                q.append(y)
    if v not in prev:
        return None
    path = [v]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    return path[::-1]


def _step(say, write=(), draw=(), why=None, edges=()):
    return {'say': say, 'write': [w if isinstance(w, dict) else {'text': w, 'kind': 'line'} for w in write],
            'draw': list(draw), 'why': why or say, 'edges': list(edges)}


def _closing(card, steps):
    f = card.get('formula')
    if f:
        steps.append(_step('Here is how the slides write it.',
                           [{'text': f['tex'], 'kind': 'math'}, {'text': f'slide {f["ref"]}', 'kind': 'note'}],
                           why=card['why']))
    steps.append(_step('Check yourself. ' + card['check'], [{'text': card['check'], 'kind': 'question'}],
                       [{'op': 'clear'}], why=card['why']))


# ---------------- Kruskal ----------------
def scene_kruskal(card):
    nodes, edges = DEMO_NODES, DEMO_MST
    res = kruskal(nodes, edges)
    order = sorted(edges, key=lambda e: (e[2], str(e[0]), str(e[1])))
    steps = [
        _step("Here's a small network: five places, A through E, and a cost on every possible link. "
              "We want to connect all of them as cheaply as possible.",
              [{'text': "Kruskal's algorithm", 'kind': 'title'}, 'Goal: connect A to E at minimum total cost'],
              [{'op': 'reveal', 'ids': [n for n in nodes] + [f'{u}-{v}' for u, v, _ in edges]}]),
        _step("Kruskal's idea is greedy. Sort the edges from cheapest to most expensive, then walk down the list.",
              ['1. Sort: ' + ', '.join(f'{u}{v} {_n(w)}' for u, v, w in order)]),
        _step("There's one rule. Take an edge only if its two ends are not connected yet. "
              "If they already are, the edge would close a cycle, so we skip it.",
              ['2. Take an edge only if its ends are in different pieces']),
    ]
    chosen, accepted = [], 0
    for st in res['steps']:
        u, v, w = st['edge']
        eid = _eid(edges, u, v)
        if st['decision'] == 'accept':
            accepted += 1
            chosen.append((u, v, w))
            say = (f"{u} {v} costs {_n(w)}. {u} and {v} aren't connected yet, so we take it. "
                   f"Running total: {_n(st['total'])}.")
            steps.append(_step(say, [{'text': f'✓ {u}–{v} ({_n(w)})   total {_n(st["total"])}', 'kind': 'ok'}],
                               [{'op': 'clear'}, {'op': 'edge', 'id': eid, 'state': 'current'},
                                {'op': 'edge', 'id': eid, 'state': 'accept'}],
                               why=f"Before this step, {u} and {v} were in different pieces of the forest, so the edge "
                                   f"{u} {v} joins two pieces without creating a cycle, and it was the cheapest edge left.",
                               edges=[eid]))
        else:
            p = _forest_path(chosen, u, v)
            cyc_ids = [_eid(edges, p[i], p[i + 1]) for i in range(len(p) - 1)]
            route = ', '.join(p)
            say = (f"{u} {v} costs {_n(w)}. But {u} and {v} are already connected: {route}. "
                   f"Adding {u} {v} would close the cycle {route}, {u}. So we skip it.")
            steps.append(_step(say, [{'text': f'✗ {u}–{v} ({_n(w)}): cycle {"–".join(p + [u])}', 'kind': 'bad'}],
                               [{'op': 'clear'}, {'op': 'path', 'ids': cyc_ids, 'style': 'cycle'},
                                {'op': 'edge', 'id': eid, 'state': 'skip'}],
                               why=(f"{u} and {v} are already joined by the path {route} using edges we took earlier. "
                                    f"So {u} {v} connects nothing new. It would only close a cycle, and a tree has no cycles. "
                                    f"Removing any edge of a cycle keeps everything connected and lowers the cost."),
                               edges=[eid]))
        if accepted == len(nodes) - 1:
            break
    notes = {}
    for u, v, w in edges:
        eid = _eid(edges, u, v)
        if not any(eid in st_['edges'] for st_ in steps):
            p = _forest_path(chosen, u, v)
            notes[eid] = (f"Kruskal never had to consider {u} {v}. By the time it came up in the sorted list the tree was "
                          f"already complete, and {u} and {v} were joined by {', '.join(p)}, so {u} {v} would only close a cycle.")
    steps.append(_step(f"That's {accepted} edges for {len(nodes)} places, so the tree is complete. "
                       f"Total cost {_n(res['total'])}. Every edge we haven't looked at would only close a cycle.",
                       [{'text': f'MST: {accepted} edges, total cost {_n(res["total"])}', 'kind': 'title'}],
                       [{'op': 'clear'}]))
    _closing(card, steps)
    g = _graph(nodes, edges, POS_MST, False, _n)
    g['notes'] = notes
    return g, steps


# ---------------- Prim ----------------
def scene_prim(card):
    nodes, edges, root = DEMO_NODES, DEMO_MST, 'A'
    res = prim(nodes, edges, root)
    steps = [
        _step("Same network, different strategy. Prim grows one tree, starting from a single place. We'll start at A.",
              [{'text': "Prim's algorithm", 'kind': 'title'}, 'Start: tree = {A}'],
              [{'op': 'reveal', 'ids': list(nodes) + [f'{u}-{v}' for u, v, _ in edges]},
               {'op': 'node', 'id': root, 'state': 'tree'}, {'op': 'shade', 'nodes': [root], 'label': 'tree'}]),
        _step('At every step, look only at edges with exactly one end in the tree, and add the cheapest one.',
              ['Rule: cheapest edge leaving the tree'])]
    for st in res['steps']:
        u, v, w = st['edge']
        eid = _eid(edges, u, v)
        cand = [_eid(edges, a, b) for a, b, _ in st['crossing']]
        options = ', '.join(f'{a} {b} at {_n(c)}' for a, b, c in st['crossing'][:4])
        say = (f"Edges leaving the tree: {options}. The cheapest is {u} {v}, so we add it, and {st['added_node']} joins the tree. "
               f"Total: {_n(st['total'])}.")
        steps.append(_step(say, [{'text': f'+ {u}–{v} ({_n(w)}) → tree {{{", ".join(st["tree_nodes"])}}}', 'kind': 'ok'}],
                           [{'op': 'clear'}] + [{'op': 'edge', 'id': c, 'state': 'candidate'} for c in cand] +
                           [{'op': 'edge', 'id': eid, 'state': 'accept'}, {'op': 'node', 'id': st['added_node'], 'state': 'tree'},
                            {'op': 'shade', 'nodes': st['tree_nodes'], 'label': 'tree'}],
                           why=f"{u} {v} was the cheapest of the edges crossing from the tree to the rest of the graph, "
                               "and the cheapest edge across any cut can always be part of a minimum spanning tree.",
                           edges=[eid] + cand))
    steps.append(_step(f"Every place is in the tree. Total cost {_n(res['total'])}, the same as Kruskal found.",
                       [{'text': f'MST total {_n(res["total"])}', 'kind': 'title'}], [{'op': 'clear'}]))
    _closing(card, steps)
    return _graph(nodes, edges, POS_MST, False, _n), steps


# ---------------- cut property ----------------
def scene_cut(card):
    nodes, edges = DEMO_NODES, DEMO_MST
    U = ['A', 'B']
    crossing = [(u, v, w) for u, v, w in edges if (u in U) != (v in U)]
    cheapest = min(crossing, key=lambda e: e[2])
    cid = _eid(edges, cheapest[0], cheapest[1])
    total = kruskal(nodes, edges)
    in_mst = any({cheapest[0], cheapest[1]} == {a, b} for a, b, _ in total['edges'])
    steps = [
        _step('Take our network and split the places into two groups: U, which is A and B, and everything else.',
              [{'text': 'Cuts', 'kind': 'title'}, 'U = {A, B}'],
              [{'op': 'reveal', 'ids': list(nodes) + [f'{u}-{v}' for u, v, _ in edges]}, {'op': 'shade', 'nodes': U, 'label': 'U'}]),
        _step('The edges with one end inside U and one end outside form the cut, delta of U.',
              [{'text': r'\delta(U) = \{\, e = uv \in E : u \in U,\ v \notin U \,\}', 'kind': 'math'},
               'δ(U) = ' + ', '.join(f'{u}{v}' for u, v, _ in crossing)],
              [{'op': 'edge', 'id': _eid(edges, u, v), 'state': 'candidate'} for u, v, _ in crossing],
              edges=[_eid(edges, u, v) for u, v, _ in crossing]),
        _step('Any spanning tree has to use at least one of these edges. Otherwise the two groups would never be connected.',
              ['Every spanning tree crosses every cut']),
        _step(f"The cheapest crossing edge is {cheapest[0]} {cheapest[1]}, at {_n(cheapest[2])}. "
              "An edge that is cheapest across some cut can always go into a minimum spanning tree. "
              "That exchange argument is what makes both Kruskal and Prim correct."
              + (' And indeed, it is in the tree Kruskal found.' if in_mst else ''),
              [{'text': f'cheapest crossing edge: {cheapest[0]}{cheapest[1]} ({_n(cheapest[2])})', 'kind': 'ok'}],
              [{'op': 'edge', 'id': cid, 'state': 'accept'}],
              why=card['why'], edges=[cid]),
    ]
    _closing(card, steps)
    return _graph(nodes, edges, POS_MST, False, _n), steps


# ---------------- Dijkstra ----------------
def scene_dijkstra(card):
    nodes, edges, src = DEMO_NODES, DEMO_PATH, 'A'
    res = dijkstra(nodes, edges, src)
    inf = '∞'
    steps = [
        _step("Now directed roads, one way each, with a cost on every arc. We want the cheapest route from A to every other place.",
              [{'text': "Dijkstra's algorithm", 'kind': 'title'}, 'Costs c ≥ 0. Source A.'],
              [{'op': 'reveal', 'ids': list(nodes) + [f'{u}-{v}' for u, v, _ in edges]}, {'op': 'node', 'id': src, 'state': 'source'}]
              + [{'op': 'label', 'id': n, 'text': 'y=0' if n == src else 'y=∞'} for n in nodes]),
        _step("Every place gets a label y: the cheapest route found so far. A starts at zero, everything else at infinity.",
              ['y_A = 0, all other y = ∞']),
        _step("The rule: pick the unscanned place with the smallest label. Because no arc has negative cost, "
              "nothing found later can beat that label, so it's final.",
              ['Pick the smallest y. With c ≥ 0 it is final.']),
    ]
    before = {n: (0 if n == src else None) for n in nodes}
    for st in res['steps']:
        u, du = st['settled'], st['distances'][st['settled']]
        steps.append(_step(f"The smallest label among the places left is {u}, at {_n(du)}. That's final.",
                           [{'text': f'scan {u}  (y = {_n(du)}, final)', 'kind': 'ok'}],
                           [{'op': 'clear'}, {'op': 'node', 'id': u, 'state': 'current'}],
                           why=f"{u} had the smallest label of all unscanned places. Any other route to {u} would have to pass "
                               f"through a place whose label is already at least {_n(du)}, and with nonnegative costs it "
                               f"cannot get cheaper from there. So {_n(du)} can never improve.",
                           edges=[]))
        outs = [(a, b, w) for a, b, w in edges if a == u]
        parts, draw, lines, eids = [], [], [], []
        for a, b, w in outs:
            eid = f'{a}-{b}'
            eids.append(eid)
            old, new = before[b], st['distances'][b]
            cand = du + w
            if old is None or cand < old:
                parts.append(f"{u} to {b}: {_n(du)} plus {_n(w)} is {_n(cand)}" +
                             (f", better than {_n(old)}, so {b} drops to {_n(cand)}." if old is not None else f", so {b} gets {_n(cand)}."))
                draw += [{'op': 'edge', 'id': eid, 'state': 'current'}, {'op': 'label', 'id': b, 'text': f'y={_n(new)}'}]
                lines.append(f'  y_{b}: {inf if old is None else _n(old)} → {_n(new)}')
            else:
                parts.append(f"{u} to {b}: {_n(du)} plus {_n(w)} is {_n(cand)}, no better than {_n(old)}.")
                draw.append({'op': 'edge', 'id': eid, 'state': 'candidate'})
        if outs:
            steps.append(_step('Scan its arcs. ' + ' '.join(parts), lines or ['  no improvements'], draw,
                               why=steps[-1]['why'] + ' Scanning then checks each arc leaving ' + u + ': if going through '
                                   'it is cheaper than the label at the far end, that label is corrected.', edges=eids))
        tree = {f'{p}-{v}' for v, p in st['predecessors'].items() if p}
        tree_draw = [{'op': 'edge', 'id': f'{a}-{b}', 'state': 'tree' if f'{a}-{b}' in tree else 'plain'} for a, b, _ in edges]
        last = steps[-1]['draw']
        steps[-1]['draw'] = [d for d in last if d['op'] == 'clear'] + tree_draw + [d for d in last if d['op'] != 'clear']
        steps[-1]['draw'].append({'op': 'node', 'id': u, 'state': 'settled'})
        before = dict(st['distances'])
    fin = ', '.join(f'{k} {_n(v)}' for k, v in res['distances'].items())
    steps.append(_step(f"Every place is scanned. Final costs from A: {fin}. The green arcs form the shortest-path tree.",
                       [{'text': 'Final: ' + fin, 'kind': 'title'}], [{'op': 'clear'}]))
    _closing(card, steps)
    return _graph(nodes, edges, POS_PATH, True, _n), steps


# ---------------- max flow / min cut ----------------
def scene_maxflow(card):
    nodes, arcs, r, s = DEMO_FLOW_NODES, DEMO_FLOW, 'r', 's'
    res = max_flow(nodes, arcs, r, s)
    cap = {f'{u}-{v}': c for u, v, c in arcs}
    steps = [
        _step("Trucks leave r and must reach s. Each road has a capacity: the most trucks it can carry. "
              "How many can we send in total?",
              [{'text': 'Maximum flow', 'kind': 'title'}, 'labels: flow / capacity'],
              [{'op': 'reveal', 'ids': list(nodes) + [f'{u}-{v}' for u, v, _ in arcs]},
               {'op': 'node', 'id': r, 'state': 'source'}, {'op': 'node', 'id': s, 'state': 'sink'}]
              + [{'op': 'elabel', 'id': f'{u}-{v}', 'text': f'0/{_n(c)}'} for u, v, c in arcs]),
        _step("Start with no flow at all. Then repeat: find an augmenting path from r to s with spare room on every arc, "
              "and push as much as the tightest arc allows.",
              ['repeat: shortest augmenting path, push ε = its bottleneck']),
    ]
    prev = {f'{u}>{v}': 0 for u, v, _ in arcs}
    for k, st in enumerate(res['steps'], 1):
        ids = [a['arc'].replace('>', '-') for a in st['arcs']]
        room = []
        for a in st['arcs']:
            eid = a['arc'].replace('>', '-')
            room.append(cap[eid] - prev[a['arc']] if a['direction'] == 'forward' else prev[a['arc']])
        rev = [a['arc'].replace('>', ' to ') for a in st['arcs'] if a['direction'] == 'reverse']
        say = (f"Searching breadth-first, the shortest augmenting path is {', '.join(st['path'])}. "
               f"Spare room along it: {', '.join(_n(x) for x in room)}. The bottleneck is {_n(st['epsilon'])}, "
               f"so push {_n(st['epsilon'])}. Total flow is now {_n(st['value'])}.")
        if rev:
            say += f" Notice it sends flow backwards on {', '.join(rev)}, which undoes earlier flow there."
        draw = [{'op': 'clear'}, {'op': 'path', 'ids': ids, 'style': 'augment'}]
        draw += [{'op': 'elabel', 'id': f.replace('>', '-'), 'text': f'{_n(x)}/{_n(cap[f.replace(">", "-")])}'}
                 for f, x in st['flow'].items()]
        draw += [{'op': 'edge', 'id': f.replace('>', '-'), 'state': 'full' if x == cap[f.replace('>', '-')] else ('accept' if x > 0 else 'plain')}
                 for f, x in st['flow'].items()]
        steps.append(_step(say, [{'text': f'{k}. {"→".join(st["path"])}   ε = {_n(st["epsilon"])}   value {_n(st["value"])}', 'kind': 'ok'}],
                           draw, why=(f"Every arc on {', '.join(st['path'])} had spare capacity, so it is an augmenting path. "
                                      f"The smallest spare amount, {_n(st['epsilon'])}, is the most we can add without "
                                      "breaking a capacity. The algorithm picks a path with the fewest arcs, which bounds "
                                      "the number of augmentations by nm."), edges=ids))
        prev = st['flow']
    R = res['cut_R']
    cut_ids = [f'{u}-{v}' for u, v, _ in res['cut_arcs']]
    steps.append(_step(f"Now there's no augmenting path left. From r we can still reach {', '.join(R)}, but not s. Call that set R.",
                       ['no augmenting path → stop', f'R = {{{", ".join(R)}}}'],
                       [{'op': 'clear'}, {'op': 'shade', 'nodes': R, 'label': 'R'}],
                       why='When no augmenting path exists, the nodes reachable from r in the auxiliary digraph form a cut '
                           'whose arcs are all saturated.'))
    steps.append(_step(f"Look at the arcs leaving R: {', '.join(i.replace('-', ' to ') for i in cut_ids)}. Every one is full. "
                       f"Their capacities add up to {_n(res['cut_capacity'])}, exactly the flow value {_n(res['value'])}.",
                       [{'text': f'u(δ(R)) = {_n(res["cut_capacity"])} = flow value {_n(res["value"])}', 'kind': 'ok'}],
                       [{'op': 'edge', 'id': i, 'state': 'cut'} for i in cut_ids],
                       why='Every unit of flow must cross the cut, so no flow can exceed a cut capacity. Here they are '
                           'equal, so this flow is maximum and this cut is minimum.', edges=cut_ids))
    steps.append(_step('Every flow is at most every cut. When a flow equals a cut, both are optimal. '
                       'That is the max flow, min cut theorem.', [{'text': 'max flow = min cut', 'kind': 'title'}]))
    _closing(card, steps)
    label = lambda c: f'0/{_n(c)}'
    return _graph(nodes, arcs, POS_FLOW, True, label), steps


# ---------------- generic concept card ----------------
def scene_card(card):
    steps = [
        _step(card['simple'], [{'text': card['title'], 'kind': 'title'}, first_sentence(card['simple'])], why=card['why']),
        _step(card['analogy'], [{'text': first_sentence(card['analogy']), 'kind': 'note'}], why=card['why']),
        _step('Here is an example. ' + card['example'], ['Example: ' + first_sentence(card['example'])], why=card['why']),
        _step("Here's the key idea. " + card['why'], ['Key idea: ' + first_sentence(card['why'])], why=card['why']),
        _step('One trap to avoid. ' + card['trap'], [{'text': 'Trap: ' + first_sentence(card['trap']), 'kind': 'bad'}],
              why=card['trap']),
    ]
    _closing(card, steps)
    return None, steps


BUILDERS = {'kruskal': scene_kruskal, 'prim': scene_prim, 'cut': scene_cut, 'dijkstra': scene_dijkstra,
            'maxflow': scene_maxflow}


def build_scene(concept_id):
    if concept_id not in CARD_BY_ID:
        raise ValueError('unknown concept')
    card = CARD_BY_ID[concept_id]
    kind = SCENE_OF.get(concept_id, 'card')
    graph, steps = (BUILDERS[kind](card) if kind in BUILDERS else scene_card(card))
    for i, s in enumerate(steps):
        s['i'] = i
    srcs = card_sources(card, card['title'])[:3]
    return {'concept_id': concept_id, 'title': card['title'], 'unit': card['unit'], 'kind': kind,
            'graph': graph, 'steps': steps,
            'sources': [{k: c[k] for k in ('id', 'unit', 'pages', 'title', 'excerpt', 'permission') if k in c} for c in srcs]}


# ---------------- interruptions ----------------
import re
_PAIR = re.compile(r'\b([A-Za-z])\s*(?:-|–|—|→|->|>|\bto\b)\s*([A-Za-z])\b|\b(?:edge|arc)\s+([A-Za-z])\s*([A-Za-z])\b')
_WHY = re.compile(r'\b(why|how come|reason|explain (that|this|it)|what happened|skip|skipped|reject|rejected|final|'
                  r'accept|accepted|bottleneck|full|saturated)\b', re.I)


def answer_interruption(scene, step_i, question):
    """Answer a question asked mid-scene from the scene itself, if it is about what is on the board.
    Returns {'answer', 'step', 'draw'} or None (then the normal tutor answers)."""
    steps = scene['steps']
    step_i = max(0, min(step_i, len(steps) - 1))
    names = {n['id'] for n in (scene['graph'] or {}).get('nodes', [])}
    m = _PAIR.search(question)
    if m and scene['graph']:
        u, v = [x for x in m.groups() if x][:2]
        u, v = (u if u in names else u.upper() if u.upper() in names else u.lower()), \
               (v if v in names else v.upper() if v.upper() in names else v.lower())
        if u in names and v in names:
            ids = {f'{u}-{v}', f'{v}-{u}'}
            for j in range(step_i, -1, -1):
                if ids & set(steps[j]['edges']):
                    focus = sorted(ids & set(steps[j]['edges']))
                    return {'answer': steps[j]['why'], 'step': j,
                            'draw': [{'op': 'path', 'ids': focus, 'style': 'focus'}]}
            note = next((scene['graph'].get('notes', {}).get(i) for i in ids if scene['graph'].get('notes', {}).get(i)), None)
            if note:
                return {'answer': note, 'step': step_i, 'draw': [{'op': 'path', 'ids': sorted(ids), 'style': 'focus'}]}
            later = next((j for j in range(step_i + 1, len(steps)) if ids & set(steps[j]['edges'])), None)
            if later is not None:
                return {'answer': f"We haven't reached {u} {v} yet. Keep watching: it comes up in a moment.",
                        'step': step_i, 'draw': [{'op': 'path', 'ids': sorted(ids & set(steps[later]['edges'])), 'style': 'focus'}]}
    words = question.split()
    deictic = re.search(r'\b(that|this|it|there|here|just|now|those|these)\b', question, re.I)
    names_concept = re.search(r'\b(kruskal|prim|dijkstra|ford|bellman|k[oö]nig|matching|cover|potential|tsp|bfs|'
                              r'topological|circuit|flow|cut|tree|forest|augment\w*|graph|digraph|path|dipath)\b', question, re.I)
    if _WHY.search(question) and (len(words) <= 4 or (deictic and len(words) <= 10)) and not names_concept:
        # "why was that skipped / taken?" refers to the latest step that did that, not just the current one
        want = 'skip' if re.search(r'skip|reject', question, re.I) else ('accept' if re.search(r'\b(accept|take|took|taken|add)', question, re.I) else None)
        if want:
            for j in range(step_i, max(-1, step_i - 6), -1):
                if any(o.get('op') == 'edge' and o.get('state') == want for o in steps[j]['draw']):
                    ids = [o['id'] for o in steps[j]['draw'] if o.get('op') == 'edge' and o.get('state') == want]
                    return {'answer': steps[j]['why'], 'step': j, 'draw': [{'op': 'path', 'ids': ids, 'style': 'focus'}]}
        return {'answer': steps[step_i]['why'], 'step': step_i, 'draw': []}
    return None
