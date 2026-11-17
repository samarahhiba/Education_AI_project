"""Unit 2.1 — Minimum Spanning Trees (slides 1-54). Graphs are redrawn from the slides:
the a–f graph (slides 3-16), the MST exercise graph (slide 22) and the Kruskal/Prim graph (slides 23-36)."""
from collections import deque

from . import Lesson, fig
from ..algorithms import kruskal, prim

U = 'Minimum Spanning Trees'

AF = {'a': (90, 60), 'b': (260, 60), 'c': (175, 155), 'd': (90, 255), 'e': (260, 255), 'f': (430, 255)}
AF_E = [('a', 'b'), ('a', 'd'), ('a', 'c'), ('b', 'c'), ('b', 'e'), ('c', 'e'), ('d', 'e'), ('e', 'f')]

# slide 22 (exercise)
EX = {'a': (50, 60), 'q': (290, 25), 'g': (520, 60), 'r': (165, 115), 'h': (410, 135), 'p': (235, 170),
      'b': (50, 215), 'f': (520, 215), 'd': (290, 285)}
EX_E = [('a', 'q', 7), ('q', 'g', 12), ('a', 'r', 4), ('q', 'p', 14), ('q', 'h', 16), ('g', 'h', 3), ('a', 'b', 15),
        ('r', 'h', 8), ('r', 'p', 11), ('b', 'r', 13), ('p', 'h', 10), ('p', 'f', 6), ('g', 'f', 9), ('p', 'd', 2),
        ('b', 'd', 17), ('d', 'f', 5)]

# slides 23-36 (Kruskal / Prim)
KG = {'b': (190, 45), 'h': (380, 45), 'd': (285, 105), 'a': (60, 180), 'g': (380, 180), 'k': (510, 180), 'f': (285, 285)}
KG_E = [('a', 'b', 16), ('b', 'h', 31), ('b', 'd', 28), ('d', 'h', 32), ('a', 'd', 22), ('d', 'g', 23), ('h', 'g', 15),
        ('h', 'k', 18), ('a', 'g', 29), ('g', 'k', 12), ('a', 'f', 20), ('f', 'g', 35), ('f', 'k', 25)]


def eid(edges, u, v):
    for e in edges:
        if {e[0], e[1]} == {u, v}:
            return f'{e[0]}-{e[1]}'
    raise KeyError((u, v))


def forest_path(chosen, u, v):
    adj = {}
    for a, b, *_ in chosen:
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    prev, q = {u: None}, deque([u])
    while q:
        x = q.popleft()
        for y in adj.get(x, []):
            if y not in prev:
                prev[y] = x; q.append(y)
    if v not in prev:
        return None
    p = [v]
    while prev[p[-1]] is not None:
        p.append(prev[p[-1]])
    return p[::-1]


def kruskal_steps(L, pos, edges, slides, ask_skip=False):
    nodes = list(pos)
    res = kruskal(nodes, [list(e) for e in edges])
    chosen, n_acc, asked = [], 0, False
    for st in res['steps']:
        u, v, w = st['edge']
        i = eid(edges, u, v)
        if st['decision'] == 'accept':
            chosen.append((u, v, w)); n_acc += 1
            L.step(f"{u} {v}, cost {w}: {u} and {v} are in different pieces, so take it.",
                   f"✓ {u}{v} ({w})   total {st['total']}",
                   [{'op': 'clear'}, {'op': 'edge', 'id': i, 'state': 'current'}, {'op': 'edge', 'id': i, 'state': 'accept'}],
                   why=f"{u} and {v} were in different components of the forest, so {u}{v} joins them without a circuit.",
                   slides=slides, edges=[i])
        else:
            p = forest_path(chosen, u, v)
            cyc = [eid(edges, p[k], p[k + 1]) for k in range(len(p) - 1)]
            if ask_skip and not asked:
                asked = True
                L.ask(f"Next in line is {u}{v}, cost {w}. Should Kruskal add it?",
                      [[r'\bno\b|not|skip|reject|don.?t'], [r'cycle|circuit|loop|already|connected|path']],
                      f"No. {u} and {v} are already joined by {', '.join(p)}, so {u}{v} would close a circuit.",
                      draw=[{'op': 'clear'}, {'op': 'edge', 'id': i, 'state': 'current'}], slides=slides)
            L.step(f"{u} {v}, cost {w}: {u} and {v} are already connected by {', '.join(p)}. Adding it would close a "
                   "circuit, so skip it.",
                   f"✗ {u}{v} ({w}): circuit {'–'.join(p + [u])}",
                   [{'op': 'clear'}, {'op': 'path', 'ids': cyc, 'style': 'cycle'}, {'op': 'edge', 'id': i, 'state': 'skip'}],
                   why=f"{u} and {v} were already joined by the path {', '.join(p)} in the forest, so {u}{v} adds no new "
                       "connection; it would only create a circuit.", slides=slides, edges=[i])
        if n_acc == len(nodes) - 1:
            break
    return res


def lesson_graphs():
    L = Lesson('u2-graphs', U, 'Graphs: nodes, edges, incidence, adjacency', [24],
               'Read and use the basic vocabulary of graphs.')
    L.figure(fig(AF, AF_E))
    L.step("Unit two is about minimum spanning trees, and it starts with graphs. A graph G is a set V of nodes and a "
           "set E of edges. Here the nodes are a through f.",
           "A **graph** $G = (V, E)$ consists of\n- a set $V = V(G)$ of **nodes**\n- a set $E = E(G)$ of **edges**", slides=[3])
    L.step("Each edge is an unordered pair of two different nodes, called its ends. This edge joins b and c, "
           "so we write it b c.",
           "Each edge $e \\in E$ is an unordered pair of distinct nodes, its **ends**: $e = \\{v, w\\} = vw$.\n"
           "Highlighted: the edge $bc$.", [{'op': 'edge', 'id': 'b-c', 'state': 'accept'}], slides=[4])
    L.step("An edge is incident to each of its ends. Two nodes are adjacent if an edge joins them, like b and c. "
           "Two different edges are adjacent if they share an end.",
           "- $e$ is **incident** to $v$ if $v \\in e$\n- $v, w$ are **adjacent** if $vw$ is an edge\n"
           "- edges $e \\ne f$ are **adjacent** if they share an end",
           [{'op': 'node', 'id': 'b', 'state': 'current'}, {'op': 'node', 'id': 'c', 'state': 'current'}], slides=[5])
    L.ask('Name an edge that is adjacent to the edge b c.',
          [[r'\b(ab|ba|ac|ca|be|eb|ce|ec)\b|\ba\s*(-|and|to)?\s*b\b|\ba\s*(-|and|to)?\s*c\b|\bb\s*(-|and|to)?\s*e\b|\bc\s*(-|and|to)?\s*e\b']],
          'Any edge sharing b or c: ab, be (at b), or ac, ce (at c).', draw=[{'op': 'clear'}], slides=[5])
    return L


def lesson_subgraphs():
    L = Lesson('u2-subgraphs', U, 'Subgraphs, spanning subgraphs, deleting edges and nodes', [25, 26],
               'Describe subgraphs and the result of deleting edges or nodes.')
    L.figure(fig(AF, AF_E))
    L.step("A subgraph H of G uses some of G's nodes and some of its edges. Here's one: nodes a, b, c, e with three edges.",
           "A **subgraph** $H$ of $G$: $V(H) \\subseteq V(G)$ and $E(H) \\subseteq E(G)$.",
           [{'op': 'hide', 'ids': ['d', 'f', 'a-d', 'd-e', 'e-f', 'a-b', 'c-e']}], slides=[6])
    L.step("A subgraph is spanning if it keeps every node, even if it drops edges. This one keeps all six nodes.",
           "$H$ is **spanning** if $V(H) = V(G)$.",
           [{'op': 'show', 'ids': ['d', 'f', 'd-e', 'e-f', 'a-d']}, {'op': 'hide', 'ids': ['a-b', 'c-e', 'b-e']}], slides=[7, 8])
    L.step("Deleting a set of edges F gives G minus F: the same nodes, without those edges. Here, G minus a b and e f.",
           "For $F \\subseteq E$: $G \\setminus F$ has $V(H) = V$ and $E(H) = E \\setminus F$.\nShown: $G \\setminus \\{ab, ef\\}$",
           [{'op': 'show', 'ids': [e for e in [f'{u}-{v}' for u, v in AF_E]]}, {'op': 'hide', 'ids': ['a-b', 'e-f']}], slides=[9])
    L.step("Deleting a set of nodes U removes those nodes and every edge incident with them. Deleting node e takes four "
           "edges with it. What's left is called the subgraph induced by the remaining nodes.",
           "For $U \\subseteq V$: $G \\setminus U$ removes $U$ and every edge incident with $U$.\n"
           "It is the subgraph $G[V \\setminus U]$ **induced** by $V \\setminus U$.\nShown: $G \\setminus \\{e\\}$",
           [{'op': 'show', 'ids': ['a-b', 'e-f']}, {'op': 'hide', 'ids': ['e', 'b-e', 'c-e', 'd-e', 'e-f']}], slides=[10, 11])
    L.ask('When we delete node e, which edges disappear with it?',
          [[r'be|eb|b.?e'], [r'ce|ec|c.?e'], [r'de|ed|d.?e'], [r'ef|fe|e.?f']],
          'Every edge incident with e: be, ce, de and ef.', slides=[10])
    L.step("Good. Let's put e back.", "", [{'op': 'show', 'ids': ['e', 'b-e', 'c-e', 'd-e', 'e-f']}])
    return L


def lesson_paths():
    L = Lesson('u2-paths', U, 'Paths, connectivity and circuits', [27, 28],
               'Define paths, connectivity, simple and edge-simple paths, and circuits.')
    L.figure(fig(AF, AF_E))
    L.step("A path is an alternating sequence of nodes and edges, where each edge joins the nodes on either side. "
           "This is a path from d to c: d, e, b, c.",
           "A **path** $P = v_0, e_1, v_1, \\dots, e_k, v_k$ with $e_i = v_{i-1}v_i$. Often just $P = v_0, \\dots, v_k$.\n"
           "A $(c, d)$-path: $P = d, e, b, c$",
           [{'op': 'path', 'ids': ['d-e', 'b-e', 'b-c'], 'style': 'augment'}], slides=[12])
    L.step("Its length is the number of edges, here three. A graph is connected if every pair of nodes is joined by a path.",
           "- $P$ is a $(v_0, v_k)$-path; its **length** is $k$ (here 3)\n- $G$ is **connected** if every pair of nodes is joined by a path",
           slides=[13])
    L.step("Paths may repeat things. This path from d to f goes d, e, b, c, e, f. It visits e twice.",
           "A $(d, f)$-path: $P = d, e, b, c, e, f$",
           [{'op': 'clear'}, {'op': 'path', 'ids': ['d-e', 'b-e', 'b-c', 'c-e', 'e-f'], 'style': 'augment'}], slides=[14])
    L.step("A path is closed if it ends where it started. It's edge-simple if no edge repeats, and simple if no node "
           "repeats. A circuit, or cycle, is a closed edge-simple path whose nodes are distinct apart from the "
           "return to the start. For example a, b, e, c, a.",
           "- **closed**: $v_0 = v_k$\n- **edge-simple**: $e_1, \\dots, e_k$ distinct\n- **simple**: $v_0, \\dots, v_k$ distinct\n"
           "- **circuit** (cycle): edge-simple, closed, $v_0, \\dots, v_{k-1}$ distinct, $k \\ge 1$\nA circuit: $C = a, b, e, c, a$",
           [{'op': 'clear'}, {'op': 'path', 'ids': ['a-b', 'b-e', 'c-e', 'a-c'], 'style': 'cycle'}], slides=[15, 16])
    L.ask('Is the path d, e, b, c, e, f simple? Is it edge-simple?',
          [[r'not simple|isn.?t simple|no.{0,25}simple|e (twice|repeat)|repeats? e|node repeats'],
           [r'edge.?simple|edges? (are )?(distinct|different)|no edge repeats|yes']],
          'It is edge-simple (all five edges differ) but not simple, because node e appears twice.', slides=[15])
    return L


def lesson_connector():
    L = Lesson('u2-connector', U, 'The connector problem becomes the MST problem', [29, 30, 31, 32],
               'See why an optimal network has no circuits, and state the MST problem.')
    L.figure(fig(EX, EX_E))
    L.step("A company wants to link its offices into a network. For certain pairs of offices, a link can be built at a "
           "positive cost. We want every pair of offices to be able to communicate, at minimum total cost.",
           "**Connector problem**\n- Offices; for certain pairs $v, w$ a link of positive cost $c_{vw}$ can be built\n"
           "- Build links so every pair can communicate, minimizing total cost", slides=[17])
    L.step("As a graph problem: given a connected graph with positive edge costs, find a spanning connected subgraph "
           "of minimum cost, where a subgraph costs the sum of its edges.",
           "Given a connected $G$ and $c_e > 0$ for all $e \\in E$, find a **minimum-cost spanning connected subgraph**.", slides=[18])
    L.figure(fig(AF, AF_E))
    L.step("Key lemma. An edge u v lies on a circuit exactly when there's another path from u to v that avoids it. "
           "Take a b on the circuit a, b, e, c, a: without it, a still reaches b through c and e.",
           "**Lemma 2.1.** $e = uv$ is an edge of a circuit of $G$ **iff** there is a path in $G \\setminus e$ from $u$ to $v$.",
           [{'op': 'path', 'ids': ['a-c', 'c-e', 'b-e'], 'style': 'augment'}, {'op': 'edge', 'id': 'a-b', 'state': 'skip'}], slides=[19])
    L.ask("So if we delete an edge of a circuit from a connected graph, why is the graph still connected?",
          [[r'other|another|rest|detour|around|alternative|still a path|reroute|go through'],
           [r'circuit|cycle|path|connected']],
          'Any path that used the deleted edge can detour around the rest of the circuit instead, so every pair of '
          'nodes is still joined.', slides=[20])
    L.step("So with positive costs, an optimal network never contains a circuit: we could delete a circuit edge, stay "
           "connected, and save money. A graph with no circuit is a forest. A connected forest is a tree.",
           "- An optimal connector has **no circuits**\n- **forest**: a graph with no circuit\n- **tree**: a connected forest",
           [{'op': 'clear'}, {'op': 'edge', 'id': 'a-b', 'state': 'plain'}], slides=[21])
    L.step("That gives the minimum spanning tree problem: given a connected graph and a real cost on each edge, find a "
           "spanning tree of minimum cost. For positive costs it's equivalent to the connector problem, and we'll "
           "solve it for arbitrary costs.",
           "**Minimum spanning tree (MST) problem.** Given connected $G$ and real costs $c_e$, find a minimum-cost "
           "spanning tree.\n- Equivalent to the connector problem for positive costs\n- We solve it for **arbitrary** costs",
           slides=[21])
    return L


def lesson_exercise():
    L = Lesson('u2-exercise', U, 'Exercise: solve an MST yourself', [33],
               'Build a minimum spanning tree by hand on the slide 22 graph.')
    L.figure(fig(EX, EX_E))
    L.step("Let's try one together. This is the exercise graph from the slides. We want the cheapest set of edges that "
           "connects every node without circuits.", "**Exercise** (slide 22): find a minimum spanning tree.", slides=[22])
    L.ask('Which edge would you take first, and why?',
          [[r'\bp\s*-?\s*d\b|\bd\s*-?\s*p\b|\bpd\b|\bdp\b|\b2\b|two'], [r'cheap|small|least|lowest|minim|smallest']],
          'p–d, with cost 2: the cheapest edge can always start a minimum spanning tree.',
          draw=[{'op': 'edge', 'id': 'p-d', 'state': 'current'}], slides=[22])
    res = kruskal_steps(L, EX, EX_E, [22], ask_skip=True)
    L.step(f"Done: {len(res['edges'])} edges for {len(EX)} nodes, total cost {res['total']}. What you just did by "
           "hand is Kruskal's algorithm, which we study next.",
           f"MST of the exercise graph: total cost **{res['total']}**\nEdges: " + ', '.join(f'{u}{v} ({w})' for u, v, w in res['edges']),
           [{'op': 'clear'}], slides=[22])
    return L


def lesson_kruskal():
    L = Lesson('u2-kruskal', U, "Kruskal's algorithm", [34], "Run Kruskal's algorithm on the lecture's graph.")
    L.figure(fig(KG, KG_E))
    L.step("Kruskal's algorithm. Start with all the nodes and no edges. At each step add a cheapest edge that keeps "
           "the graph a forest, meaning it creates no circuit. Stop when the forest is a spanning tree.",
           "**Kruskal's algorithm for MST**\n1. Initialize $H = (V, F)$ as $(V, \\emptyset)$\n2. At each step add to $F$ a "
           "least-cost edge $e \\notin F$ such that $H$ remains a (spanning) forest\n3. Stop when $H$ is a (spanning) tree",
           slides=[23])
    res = kruskal_steps(L, KG, KG_E, list(range(24, 30)), ask_skip=True)
    L.step(f"Six edges for seven nodes: a spanning tree of cost {res['total']}, the same red tree as on the slide. "
           "At every step the algorithm held a spanning forest, and at the end that forest is connected.",
           f"MST cost **{res['total']}**. At each step a spanning forest; at the end it is connected (a tree).",
           [{'op': 'clear'}], slides=[29])
    return L


def lesson_prim():
    L = Lesson('u2-prim', U, "Prim's algorithm", [35], "Run Prim's algorithm and compare it with Kruskal's.")
    L.figure(fig(KG, KG_E))
    root = 'a'
    L.step("Prim's algorithm grows a single tree. Start with one node r and no edges. At each step add a cheapest edge "
           "that keeps H a tree, which means an edge with exactly one end in the tree. Stop when the tree spans.",
           "**Prim's algorithm for MST**\n1. Initialize $H = (V(H), T)$ as $(\\{r\\}, \\emptyset)$ for some $r \\in V$\n"
           "2. At each step add to $T$ a least-cost edge $e \\notin T$ such that $H$ remains a tree\n3. Stop when $H$ is spanning",
           [{'op': 'node', 'id': root, 'state': 'tree'}, {'op': 'shade', 'nodes': [root], 'label': 'tree'}], slides=[30])
    res = prim(list(KG), [list(e) for e in KG_E], root)
    for k, st in enumerate(res['steps']):
        u, v, w = st['edge']
        cand = [eid(KG_E, a, b) for a, b, _ in st['crossing']]
        opts = ', '.join(f'{a}{b} {c}' for a, b, c in st['crossing'][:4])
        draw = [{'op': 'clear'}] + [{'op': 'edge', 'id': c, 'state': 'candidate'} for c in cand] + [
            {'op': 'edge', 'id': eid(KG_E, u, v), 'state': 'accept'}, {'op': 'node', 'id': st['added_node'], 'state': 'tree'},
            {'op': 'shade', 'nodes': st['tree_nodes'], 'label': 'tree'}]
        if k == 1:
            L.ask(f"The tree is now {{{', '.join(sorted(res['steps'][0]['tree_nodes']))}}}. Which edge does Prim add next?",
                  [[rf'\b{u}\s*-?\s*{v}\b|\b{v}\s*-?\s*{u}\b|\b{w}\b']],
                  f"{u}{v}, cost {w}: the cheapest of the edges leaving the tree ({opts}).",
                  draw=[{'op': 'clear'}] + [{'op': 'edge', 'id': c, 'state': 'candidate'} for c in cand], slides=[31])
        L.step(f"Edges leaving the tree: {opts}. Cheapest is {u} {v}, so {st['added_node']} joins the tree.",
               f"+ {u}{v} ({w}) → tree {{{', '.join(sorted(st['tree_nodes']))}}}, total {st['total']}", draw,
               why=f"{u}{v} was the cheapest edge with exactly one end in the tree.", slides=list(range(31, 37)),
               edges=[eid(KG_E, u, v)] + cand)
    L.step(f"The tree spans every node. Total {res['total']}: the same cost Kruskal found, here even the same tree. "
           "At each step Prim keeps a tree, and at the end it's spanning.",
           f"Spanning tree of cost **{res['total']}** (same as Kruskal).", [{'op': 'clear'}], slides=[36])
    return L


def lesson_correctness():
    L = Lesson('u2-correct', U, 'Cuts, and why both algorithms are correct', [37, 38, 39, 40],
               'Use cuts and the exchange lemma to see why Prim and Kruskal find an MST.')
    L.figure(fig(KG, KG_E))
    U_ = ['a', 'b', 'f']
    cut = [f'{u}-{v}' for u, v, _ in KG_E if (u in U_) != (v in U_)]
    L.step("Now, why do these algorithms work? We need cuts. For a set of nodes U, the cut delta of U is the set of "
           "edges with one end inside U and the other outside.",
           "For $U \\subseteq V$: $\\delta(U) = \\{e \\in E : e = uv,\\ u \\in U,\\ v \\in V \\setminus U\\}$ is a **cut**.\n"
           "If $U = \\emptyset$ or $U = V$, $\\delta(U) = \\emptyset$ is a **trivial cut**.",
           [{'op': 'shade', 'nodes': U_, 'label': 'U'}] + [{'op': 'edge', 'id': c, 'state': 'candidate'} for c in cut], slides=[38])
    L.step("If you delete a non-trivial cut, nothing inside U can reach anything outside. That gives Theorem 2.3: a "
           "graph is connected exactly when no non-trivial cut is empty.",
           "Exercise: for a non-trivial cut $\\delta(U)$, $u \\in U$, $v \\notin U$, there is no $(u,v)$-path in $G \\setminus \\delta(U)$.\n"
           "**Theorem 2.3.** $G$ is connected **iff** there is no $U$, $\\emptyset \\ne U \\ne V$, with $\\delta(U) = \\emptyset$.",
           [{'op': 'hide', 'ids': cut}], slides=[38, 39])
    T = [f'{u}-{v}' for u, v, _ in kruskal(list(KG), [list(e) for e in KG_E])['edges']]
    L.step("Next, the exchange lemma. Take a spanning tree H, shown in green, and an edge e equals v w that's not in it. "
           "Adding e creates a circuit with the tree path from v to w.",
           "**Lemma 2.7.** $H = (V, T)$ a spanning tree, $e = vw \\notin T$, $f$ an edge of the simple $v$–$w$ path in $T$. "
           "Then $H' = (V, T \\cup \\{e\\} \\setminus \\{f\\})$ is a spanning tree.",
           [{'op': 'show', 'ids': cut}, {'op': 'shade', 'nodes': []}, {'op': 'clear'}] + [{'op': 'edge', 'id': i, 'state': 'accept'} for i in T]
           + [{'op': 'edge', 'id': 'a-g', 'state': 'current'}, {'op': 'path', 'ids': ['a-d', 'd-g'], 'style': 'cycle'}], slides=[40])
    L.step("Remove any edge f of that path, say a d, and you get a spanning tree again. Swapping like this is how the "
           "correctness proofs move from any optimal tree toward the one the algorithm builds.",
           "Swap: add $e = ag$, remove $f = ad$ → still a spanning tree.",
           [{'op': 'edge', 'id': 'a-g', 'state': 'accept'}, {'op': 'edge', 'id': 'a-d', 'state': 'skip'}], slides=[40])
    L.step("Call a set of edges extendible if some minimum spanning tree contains it. Theorem 2.4: if B is extendible, "
           "and e is a cheapest edge of some cut that contains no edge of B, then B plus e is still extendible.",
           "$F$ is **extendible** to an MST if some MST contains $F$.\n**Theorem 2.4.** $B \\subseteq E$ extendible, $e$ a "
           "minimum-cost edge of a cut $D$ with $D \\cap B = \\emptyset$ ⇒ $B \\cup \\{e\\}$ is extendible.",
           [{'op': 'clear'}] + [{'op': 'edge', 'id': f'{u}-{v}', 'state': 'plain'} for u, v, _ in KG_E], slides=[40])
    L.ask("In Prim's algorithm, which cut does the next edge come from?",
          [[r'tree|v\(h\)|current|nodes (already )?in|delta of v|the tree.?s nodes|leaving']],
          "The cut δ(V(H)) between the tree's nodes and the rest. The new edge is a cheapest edge of that cut, which "
          "contains no tree edge, so Theorem 2.4 keeps the tree extendible to an MST.", slides=[41])
    L.step("Applying Theorem 2.4 at every step proves both algorithms correct, for any edge costs, positive or not.",
           "**Theorem 2.5.** For any connected $G$ and arbitrary costs $c$, Prim's algorithm finds an MST.\n"
           "**Theorem 2.6.** For any connected $G$ and arbitrary costs $c$, Kruskal's algorithm finds an MST.", slides=[41])
    return L


def lesson_prim_eff():
    L = Lesson('u2-prim-eff', U, "Efficiency of Prim's algorithm", [41, 42, 43, 44, 45, 46],
               "Show Prim runs in O(nm) and why m ≥ n − 1.")
    L.figure(fig(KG, KG_E))
    m, n = len(KG_E), len(KG)
    L.step("How fast is Prim? First, how do we store a graph? As a list of edges, each written as its two ends and "
           "its cost.",
           "Store $G$ as a list of edges; edge $f = uv$ is stored as $(u, v, c_f)$.",
           slides=[42, 43])
    L.ask('What is the length of this encoding, in terms of the number of edges m?',
          [[r'3\s*m|three\s*m|3 times m|3 per edge|three (numbers|entries) per edge']],
          f"3m: three entries per edge. This graph has m = {m}, so 3m = {3 * m}.", slides=[44])
    L.step("By the correctness proof, Prim can be restated: while H isn't spanning, add a minimum-cost edge of the "
           "cut delta of V of H.",
           "**Prim restated.** Initialize $H = (\\{r\\}, \\emptyset)$. While $H$ is not spanning, add to $T$ a "
           "minimum-cost edge from $\\delta(V(H))$.", slides=[45, 46])
    st = prim(list(KG), [list(e) for e in KG_E], 'a')['steps'][1]
    xs = [{'op': 'label', 'id': v, 'text': 'x=1' if v in st['tree_nodes'][:-1] else 'x=0'} for v in KG]
    L.step("To find that edge, keep a characteristic vector x: x is one for nodes in the tree, zero otherwise. Run "
           "through all m edges; an edge u v is in the cut when x u differs from x v, and we keep the cheapest.",
           "- Keep $V(H)$ as a characteristic vector $x$: $x_u = 1$ if $u \\in V(H)$, else 0\n"
           "- Scan $E$: $f = uv \\in \\delta(V(H))$ iff $x_u \\ne x_v$; keep the cheapest → $O(m)$\n"
           "- Then set $x_v = 1$ for the new node. One loop: $O(m)$ steps",
           xs + [{'op': 'shade', 'nodes': st['tree_nodes'][:-1], 'label': 'x=1'}], slides=[47, 48, 49])
    L.step("How many loops? Lemma 2.2: a spanning connected subgraph is a spanning tree exactly when it has n minus "
           "one edges. So the loop runs n minus one times, and Prim takes order n times m.",
           "**Lemma 2.2.** A spanning connected subgraph is a spanning tree **iff** it has exactly $n - 1$ edges.\n"
           f"→ the loop runs $n - 1$ times → Prim is $O(nm)$. (Here $n = {n}$: 6 loops.)\n"
           "Note: connected ⇒ $m \\ge n - 1$, so we assume $n = O(m)$ and $m = O(n^2)$.",
           [{'op': 'shade', 'nodes': []}] + [{'op': 'label', 'id': v, 'text': ''} for v in KG], slides=[50])
    return L


def lesson_kruskal_eff():
    L = Lesson('u2-kruskal-eff', U, "Efficiency of Kruskal's algorithm", [47, 48, 49, 50],
               "Show Kruskal runs in O(m log m + n²) using blocks.")
    L.figure(fig(KG, KG_E))
    L.step("Kruskal's efficiency. Once an edge becomes unavailable, because its ends are already joined, it stays "
           "unavailable. So we can sort the edges once and make one pass.",
           "Once $e = vw$ is unavailable ($H$ has a $v$–$w$ path), it stays unavailable.\n**Kruskal restated.**\n"
           "1. Order $E$ as $e_1, \\dots, e_m$ with $c_{e_1} \\le \\dots \\le c_{e_m}$\n2. $H = (V, \\emptyset)$\n"
           "3. For $i = 1..m$: if the ends of $e_i$ are in different components of $H$, add $e_i$", slides=[51, 52])
    L.step("Phase one is sorting, order m log m. Phase two keeps the components as blocks: each node v remembers "
           "block of v. A find just reads that label.",
           "- Phase 1: sorting, $O(m \\log m)$\n- Phase 2: keep the partition of $V$ into **blocks**; $2m$ finds, $n-1$ merges\n"
           "- Store $\\text{block}(v)$ for each $v$: a find is 1 step",
           [{'op': 'label', 'id': v, 'text': f'block {v}'} for v in KG], slides=[53, 54])
    res = kruskal(list(KG), [list(e) for e in KG_E])
    block = {v: v for v in KG}
    for st in res['steps']:
        u, v, w = st['edge']
        if st['decision'] != 'accept':
            continue
        keep, gone = block[u], block[v]
        changed = [x for x in KG if block[x] == gone]
        for x in changed:
            block[x] = keep
        L.step(f"Add {u} {v}: merge by relabelling every node in block {gone} as block {keep}. That's {len(changed)} "
               "relabel" + ('s' if len(changed) > 1 else '') + '.',
               f"merge on {u}{v}: block {gone} → block {keep}  ({len(changed)} relabel{'s' if len(changed) > 1 else ''})",
               [{'op': 'edge', 'id': eid(KG_E, u, v), 'state': 'accept'}] + [{'op': 'label', 'id': x, 'text': f'block {block[x]}'} for x in KG],
               slides=[54], edges=[eid(KG_E, u, v)])
    L.step("A merge relabels at most n nodes, and there are n minus one merges, so phase two is order m plus n squared. "
           "In total Kruskal runs in order m log m plus n squared.",
           "A merge costs ≤ $n$ steps; $n-1$ merges ⇒ phase 2 is $O(m + n^2)$.\n"
           "**Kruskal:** $O(m \\log m + m + n^2) = O(m \\log m + n^2)$", slides=[54])
    L.ask('Why can each find be done in one elementary step?',
          [[r'label|block\(v\)|stored|store|look ?up|read|array|each node (keeps|has|stores)|name']],
          'Because every node stores the name of its block, block(v): a find just reads that label.', slides=[54])
    return L


def lessons():
    return [lesson_graphs(), lesson_subgraphs(), lesson_paths(), lesson_connector(), lesson_exercise(), lesson_kruskal(),
            lesson_prim(), lesson_correctness(), lesson_prim_eff(), lesson_kruskal_eff()]
