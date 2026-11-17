"""Unit 2.2 — Shortest Paths (slides 1-115). Digraphs redrawn from the slides: the r,a,b,d digraph
(slides 5-9, 28, 66), Ford's negative-dicircuit example (slides 53-59), the topological-sort example
(slides 70-78, arcs taken from the sequence S on slide 71), Dijkstra's example (slides 84-96) and the BFS
example (slides 105-115, queue order as on the slide)."""
from . import Lesson, fig
from ..algorithms import ford_sequence, dijkstra, bfs

U = 'Shortest Paths'
INF = '∞'

SD = {'r': (70, 170), 'a': (280, 60), 'b': (280, 280), 'd': (490, 170)}
SD_E = [('r', 'a', 3), ('r', 'b', 1), ('b', 'a', 1), ('a', 'd', 2)]

NEG = {'r': (60, 165), 'a': (230, 55), 'd': (300, 165), 'b': (500, 165), 'c': (230, 275)}
NEG_E = [('r', 'a', 5), ('r', 'c', 1), ('a', 'b', 2), ('b', 'c', -2), ('c', 'd', -2), ('d', 'a', 1)]

TOPO = {'b': (190, 40), 'j': (380, 40), 'a': (60, 160), 'd': (230, 160), 'i': (370, 160), 'h': (510, 160),
        'f': (170, 285), 'g': (370, 285)}
TOPO_S = ['da', 'df', 'dg', 'di', 'hg', 'hj', 'ib', 'ig', 'ij', 'gf', 'jb', 'ba', 'af']     # slide 71
TOPO_ORDER = ['d', 'h', 'i', 'g', 'j', 'b', 'a', 'f']

DJ = {'r': (60, 165), 'a': (220, 50), 'p': (420, 50), 'b': (220, 280), 'q': (420, 280)}
# diagonal arrow directions reconstructed so the final labels match the slide (a 2, p 3, b 4, q 6)
DJ_E = [('r', 'a', 2), ('r', 'b', 4), ('a', 'p', 1), ('b', 'a', 3), ('q', 'a', 3), ('b', 'p', 2), ('p', 'q', 4), ('b', 'q', 2)]

BF = {'2': (150, 45), '5': (270, 45), '8': (390, 40), '1': (40, 160), '3': (150, 160), '6': (270, 160), '9': (390, 160),
      '11': (510, 160), '4': (150, 280), '7': (270, 280), '10': (390, 285)}
BF_E = [('1', '4'), ('1', '7'), ('2', '1'), ('3', '1'), ('3', '2'), ('3', '5'), ('5', '2'), ('5', '6'), ('5', '8'),
        ('6', '3'), ('6', '9'), ('7', '6'), ('7', '10'), ('7', '4'), ('8', '9'), ('8', '11'), ('9', '5'), ('10', '9'), ('11', '10')]


def y(v):
    return INF if v is None else str(v)


def labels(ys):
    return [{'op': 'label', 'id': k, 'text': f'y={y(v)}'} for k, v in ys.items()]


def lesson_intro():
    L = Lesson('u3-intro', U, 'Driving distances and digraphs', [52, 53, 54, 55, 56, 57, 58],
               'Model one-way streets as a digraph and state the shortest dipath problem.')
    L.figure(fig(SD, SD_E, directed=True))
    L.step("Unit two point two is about shortest paths. We'll meet Ford's algorithm and the Ford-Bellman algorithm, "
           "then faster methods for three special cases: acyclic digraphs, nonnegative costs, and unit costs.",
           "**Shortest Paths**: the plan\n- Minimum Driving Distances and the Shortest (Di)Path Problem\n"
           "- Ford's algorithm and the Ford–Bellman algorithm\n- Faster algorithms for special cases: acyclic digraphs, "
           "nonnegative costs, unit costs", slides=[2])
    L.step("The motivating problem: make a table of the minimum driving distance from one street corner in San "
           "Francisco to every other corner. Streets can be one-way, so each link needs a direction. A two-way "
           "street becomes two arcs in opposite directions.",
           "**Minimum Driving Distances**: shortest routes from one corner (Walnut St & Pacific Ave) to every other corner.\n"
           "- Routes must obey one-way streets → edges need a **direction**\n- A two-way street = two opposite arcs",
           slides=[4, 5])
    L.step("So we use a digraph: nodes and arcs, where each arc is an ordered pair. For an arc v w, v is the tail and "
           "w is the head. Here r to a is an arc with tail r and head a.",
           "A **digraph** $G = (V, E)$: nodes $V$ and **arcs** $E$, each an ordered pair of distinct nodes.\n"
           "For $e = vw$: **tail** $t(e) = v$, **head** $h(e) = w$.",
           [{'op': 'edge', 'id': 'r-a', 'state': 'current'}], slides=[6])
    L.step("A path can use arcs forwards or backwards. A dipath uses every arc forwards. The cost of a dipath is the sum "
           "of its arc costs: r, b, a, d costs one plus one plus two, which is four.",
           "- In a path, arc $e_i$ is **forward** if $e_i = v_{i-1}v_i$, **reverse** otherwise\n"
           "- A **dipath** uses every arc forward; a **dicircuit** is a circuit that is a dipath\n"
           "- Cost $c(P) = \\sum_i c_{e_i}$. Example: $c(r, b, a, d) = 1 + 1 + 2 = 4$",
           [{'op': 'clear'}, {'op': 'path', 'ids': ['r-b', 'b-a', 'a-d'], 'style': 'augment'}], slides=[7, 8])
    L.step("The shortest dipath problem: given a digraph, a root node r, and arc costs, find for every node v a "
           "least-cost dipath from r to v. By modifying G we can assume such dipaths exist, for example by adding "
           "very expensive arcs from r.",
           "**Shortest (Di)Path Problem.** Input: digraph $G$, node $r$, costs $c_e$. Objective: for each $v$, a dipath "
           "from $r$ to $v$ of least cost.\nWe may assume dipaths from $r$ to every node exist (add high-cost arcs $rv$).",
           [{'op': 'clear'}, {'op': 'node', 'id': 'r', 'state': 'source'}], slides=[9])
    return L


def lesson_potential():
    L = Lesson('u3-potential', U, 'Improving paths and feasible potentials', [59, 60, 61, 62, 63],
               'Use labels y to find and certify shortest dipaths.')
    L.figure(fig(SD, SD_E, directed=True))
    L.ask("Exercise: what is the cheapest dipath from r to d here, and what does it cost?",
          [[r'r.{0,4}b.{0,4}a.{0,4}d|rbad'], [r'\b4\b|four']],
          'r, b, a, d with cost 1 + 1 + 2 = 4. Going r, a, d directly costs 3 + 2 = 5.', slides=[10])
    L.step("Here's the idea behind every algorithm in this unit. Suppose we know a dipath to a costing 3, the direct arc. "
           "But there's a dipath to b costing 1, and an arc b to a costing 1. Since 3 is bigger than 1 plus 1, appending "
           "that arc gives a cheaper dipath to a.",
           "**Idea.** Dipath $P$ to $v$, dipath $P'$ to $w$, arc $vw$ with $c(P') > c(P) + c_{vw}$ ⇒ appending $vw$ to $P$ "
           "gives a cheaper dipath to $w$.\nHere: $3 > 1 + 1$, so $r, b, a$ beats $r, a$. If $P'$ were shortest, this "
           "could not happen.",
           [{'op': 'edge', 'id': 'r-a', 'state': 'candidate'}, {'op': 'path', 'ids': ['r-b', 'b-a'], 'style': 'augment'}],
           slides=[11, 12])
    ys = {'r': 0, 'a': 2, 'b': 1, 'd': 4}
    L.step("Give every node a number y. If y r is zero and every arc satisfies y v plus c v w at least y w, then y is a "
           "feasible potential. The true shortest distances always form one.",
           "A vector $y \\in \\mathbb{R}^V$ with $y_r = 0$ and $y_v + c_{vw} \\ge y_w$ for all $vw \\in E$ (\\*) is a "
           "**feasible potential**.\nThe least costs $y^*_v$ satisfy (\\*), so they form a feasible potential.",
           [{'op': 'clear'}] + labels(ys), slides=[13])
    L.step("Check it here: r to a, zero plus three is at least two. r to b, zero plus one is at least one. b to a, one "
           "plus one is at least two. a to d, two plus two is at least four. Every arc passes.",
           "Check (\\*): $0+3 \\ge 2$, $0+1 \\ge 1$, $1+1 \\ge 2$, $2+2 \\ge 4$ ✓", slides=[13])
    L.step("And conversely, Proposition 2.9: if y is a feasible potential, every dipath to v costs at least y v. Add up "
           "the inequality along the path: the y terms telescope.",
           "**Proposition 2.9.** $y$ feasible potential, $P$ a dipath from $r$ to $v$ ⇒ $c(P) \\ge y_v$.\n"
           "Proof idea: sum $c_{v_{i-1}v_i} \\ge y_{v_i} - y_{v_{i-1}}$ along $P$; the right side telescopes to $y_v - y_r = y_v$.",
           slides=[14])
    L.ask('So y gives a lower bound on every dipath. Why does that let us prove r, b, a, d is shortest?',
          [[r'cost|equal|4|four|matches|same'], [r'y|bound|potential|label|feasible|at least']],
          'Its cost, 4, equals y_d = 4, and every dipath to d costs at least y_d. So none can be cheaper.', slides=[14])
    L.step("One more structural fact. Subpaths of shortest dipaths are shortest. So for each node other than r we only "
           "need the last arc of one shortest dipath: n minus one arcs, forming a directed spanning tree.",
           "- Subpaths of shortest dipaths are shortest dipaths\n- For each $v \\ne r$ keep only the **last arc** of one "
           "least-cost dipath: $n - 1$ arcs\n- They form a \"directed\" spanning tree containing a dipath from $r$ to every node",
           [{'op': 'edge', 'id': 'r-b', 'state': 'tree'}, {'op': 'edge', 'id': 'b-a', 'state': 'tree'},
            {'op': 'edge', 'id': 'a-d', 'state': 'tree'}], slides=[15])
    return L


def lesson_ford():
    L = Lesson('u3-ford', U, "Ford's algorithm", [64, 65], "Run Ford's algorithm by correcting incorrect arcs.")
    L.figure(fig(SD, SD_E, directed=True))
    L.step("Ford's algorithm aims for exactly that certificate: a feasible potential plus a predecessor p of v for each "
           "node. An arc v w is incorrect if y v plus c v w is less than y w. Correcting it sets y w to y v plus c v w "
           "and p of w to v.",
           "Find a feasible potential $y$ and predecessors $p(v)$.\n- Arc $vw$ is **incorrect** if $y_v + c_{vw} < y_w$\n"
           "- To **correct** $vw$: $y_w = y_v + c_{vw}$, $p(w) = v$", slides=[16])
    L.step("Start with y r equals zero and everything else infinity. Then, while some arc is incorrect, correct one.",
           "**Ford's algorithm**\n1. $y_r = 0$, $p(r) = 0$; $y_v = \\infty$, $p(v) = -1$ for $v \\ne r$\n"
           "2. While $y$ is not a feasible potential: find an incorrect arc $vw$ and correct it",
           [{'op': 'node', 'id': 'r', 'state': 'source'}] + labels({'r': 0, 'a': None, 'b': None, 'd': None}), slides=[17])
    order = [['ra', 'ad', 'rb', 'ba', 'ad']]
    run = ford_sequence(list(SD), [list(e) for e in SD_E], 'r', order)
    k = 0
    for st in run['steps']:
        if st['new'] is None:
            continue
        k += 1
        a, b = st['arc'][0], st['arc'][1]
        L.step(f"Arc {a} {b} is incorrect: {y(st['y'][a])} plus {dict((f'{u}{v}', w) for u, v, w in SD_E)[st['arc']]} "
               f"beats {y(st['old'])}. Correct it: y {b} becomes {st['new']}, predecessor {a}.",
               f"{k}. correct {a}{b}: $y_{b}$: {y(st['old'])} → {st['new']}, $p({b}) = {a}$",
               [{'op': 'clear'}, {'op': 'edge', 'id': f'{a}-{b}', 'state': 'current'}, {'op': 'label', 'id': b, 'text': f"y={st['new']}"}],
               slides=list(range(18, 28)), edges=[f'{a}-{b}'])
    L.ask("Now every arc is correct. What are the final labels?",
          [[r'a\D{0,4}2|2\D{0,6}a'], [r'b\D{0,4}1|1\D{0,6}b'], [r'd\D{0,4}4|4\D{0,6}d']],
          f"y_r = 0, y_a = {run['y']['a']}, y_b = {run['y']['b']}, y_d = {run['y']['d']}: the slide's iteration 5. The "
          "predecessors r→b→a→d give the dipaths.", draw=[{'op': 'clear'}], slides=[28])
    L.step("Every arc is correct, so y is a feasible potential, and the predecessor arcs, shown in green, give a "
           "dipath to each node of exactly that cost. By Proposition 2.9 they are shortest.",
           f"Feasible potential reached: $y = (r{{:}}0, a{{:}}{run['y']['a']}, b{{:}}{run['y']['b']}, d{{:}}{run['y']['d']})$; predecessor arcs form the shortest-path tree.",
           [{'op': 'edge', 'id': f"{p}-{v}", 'state': 'tree'} for v, p in run['p'].items() if p not in (0, -1)], slides=[28])
    return L


def lesson_negative():
    L = Lesson('u3-negative', U, 'Negative-cost dicircuits', [66, 67, 68, 70, 71, 72, 73, 74, 75, 76, 77],
               "See why Ford's algorithm can loop forever, and when it is guaranteed to work.")
    L.figure(fig(NEG, NEG_E, directed=True))
    cyc = ['a-b', 'b-c', 'c-d', 'd-a']
    L.step("Here's a digraph from the slides with a dicircuit a, b, c, d, a. Its cost is two minus two minus two plus "
           "one: minus one. A negative-cost dicircuit.",
           "Dicircuit $a, b, c, d, a$: cost $2 - 2 - 2 + 1 = -1 < 0$ → a **negative-cost dicircuit**",
           [{'op': 'path', 'ids': cyc, 'style': 'cycle'}, {'op': 'node', 'id': 'r', 'state': 'source'}], slides=[53])
    S = ['ra', 'ab', 'bc', 'cd', 'da']
    run = ford_sequence(list(NEG), [list(e) for e in NEG_E], 'r', [S, S[1:], S[1:]])
    shown = [s for s in run['steps'] if s['new'] is not None][:9]
    for k, st in enumerate(shown, 1):
        a, b = st['arc'][0], st['arc'][1]
        L.step(f"Correct {a} {b}: y {b} becomes {st['new']}." + (" Around the circuit again, and every label keeps dropping." if k == 6 else ''),
               f"{k}. correct {a}{b}: $y_{b}$ → {st['new']}",
               [{'op': 'clear'}, {'op': 'path', 'ids': cyc, 'style': 'cycle'}, {'op': 'edge', 'id': f'{a}-{b}', 'state': 'current'},
                {'op': 'label', 'id': b, 'text': f"y={st['new']}"}], slides=[54, 58, 59], edges=[f'{a}-{b}'])
    L.step("At iteration five, following predecessors back from a gives a, b, c, d, a: not a simple dipath, its cost "
           "minus one is less than y a. With a negative-cost dicircuit, Ford's algorithm never terminates: each lap "
           "lowers every label on the circuit by one.",
           "With a negative-cost dicircuit **Ford's algorithm does not terminate**: each lap lowers the labels by 1.\n"
           "(Slide 57: at iteration 5 the predecessors of $a$ trace $a, b, c, d, a$, cost $-1 < 4 = y_a^5$.)",
           slides=[46, 57])
    L.step("Negative dicircuits aren't just a nuisance. Exchanging currencies around a loop makes money exactly when "
           "the product of the exchange rates exceeds one. Taking minus the log of each rate as a cost, that's exactly "
           "a negative-cost dicircuit.",
           "**Money-making exchanges.** $r_{vw}$ = units of $w$ per unit of $v$. A cycle $v_0, \\dots, v_k = v_0$ makes money iff\n"
           "$$\\prod_i r_{v_{i-1}v_i} > 1 \\iff \\sum_i \\log r_{v_{i-1}v_i} > 0 \\iff \\sum_i (-\\log r_{v_{i-1}v_i}) < 0$$\n"
           "With $c_{vw} = -\\log r_{vw}$: negative-cost dicircuits = money-making sequences.", [{'op': 'clear'}], slides=[47, 48, 49])
    L.step("Without negative dicircuits, Ford's algorithm is correct. The slides prove it in steps. Proposition 2.10: at "
           "each iteration, each finite label is the cost of some dipath, and without negative dicircuits the "
           "predecessors define a simple dipath costing at most that label.",
           "Write $y^j_v$, $p^j(v)$ for the values at iteration $j$. Correcting $ab$ lowers only $y_b$.\n"
           "**Proposition 2.10.** For $y^j_v \\ne \\infty$: (1) some dipath to $v$ costs $y^j_v$; (2) with no negative "
           "dicircuit, some *simple* one does. Part 2: with no negative dicircuit, $p^j$ defines a simple dipath to $v$ of cost ≤ $y^j_v$.",
           slides=[51, 52, 53, 55, 56, 57])
    L.step("Since there are finitely many simple dipaths, the labels can only drop finitely often. Theorem 2.11: with no "
           "negative-cost dicircuit, Ford's algorithm terminates, and the predecessors give least-cost dipaths.",
           "**Theorem 2.11.** If $(G, c)$ has no negative-cost dicircuit, Ford's algorithm terminates after finitely many "
           "iterations, and $p$ defines a least-cost dipath from $r$ to each $v$ of cost $y_v$.", slides=[60])
    L.ask('Why does each lap around the dicircuit lower the labels by exactly one?',
          [[r'-1|minus one|negative|cost of the (di)?circuit|circuit costs|sum|total']],
          'Going once around adds the circuit cost, −1, to the label you started from, so each lap makes every label on the circuit one smaller.',
          slides=[54])
    return L


def lesson_ford_bellman():
    L = Lesson('u3-fordbellman', U, 'Choosing the order: the Ford–Bellman algorithm', [78, 79, 80, 81, 82, 83, 84],
               'Scan the arcs in passes, need at most n − 1 passes, and detect negative dicircuits.')
    L.figure(fig(SD, SD_E, directed=True))
    L.step("Ford's algorithm leaves open which incorrect arc to pick, and bad choices can be very slow. So fix a sequence "
           "S of arcs, repeats allowed, and at each step take the next arc of S and correct it if needed.",
           "**Basic step i:** choose arc $e_i$ from $S$; if incorrect, correct it (constant time).\nThe number of steps "
           "depends on the order; some choices of $S$ perform very badly.", slides=[61, 62])
    L.step("If a dipath's arcs appear in S in order, maybe with other arcs in between, we say the path is embedded in S. "
           "Then after scanning S, y v is at most the cost of that path.",
           "$P$ is **embedded** in $S$ if its arcs occur as a subsequence of $S$.\n**Proposition 2.16.** If $P$ (to $v$) is "
           "embedded in $S$, then after scanning $S$, $y_v \\le c(P)$.", slides=[63, 64, 65])
    L.step("A simple dipath has at most n minus one arcs. So n minus one passes through E, in any order, embed every "
           "simple dipath. That's Ford-Bellman, order m n time. This graph has four nodes, so three passes. Let's use "
           "the slide's three orderings.",
           "Every simple dipath is embedded in $S_1, S_2, \\dots, S_{n-1}$ (each $S_i$ any ordering of $E$) → $O(mn)$.\n"
           "Slide example (n = 4): $S_1 = ad, ba, ra, rb$; $S_2 = ba, ad, rb, ra$; $S_3 = rb, ba, ra, ad$",
           [{'op': 'node', 'id': 'r', 'state': 'source'}] + labels({'r': 0, 'a': None, 'b': None, 'd': None}), slides=[66])
    passes = [['ad', 'ba', 'ra', 'rb'], ['ba', 'ad', 'rb', 'ra'], ['rb', 'ba', 'ra', 'ad']]
    run = ford_sequence(list(SD), [list(e) for e in SD_E], 'r', passes)
    for k in range(1, 4):
        sts = [s for s in run['steps'] if s['pass'] == k]
        fixes = [s for s in sts if s['new'] is not None]
        desc = '; '.join(f"{s['arc']}: y{s['arc'][1]} → {s['new']}" for s in fixes) or 'no arc is incorrect'
        say = (f"Pass {k}: " + (', '.join(f"{s['arc'][0]} {s['arc'][1]} corrects y {s['arc'][1]} to {s['new']}" for s in fixes)
                                if fixes else "nothing changes") + '.')
        L.step(say, f"Pass {k} ({', '.join(passes[k - 1])}): {desc}",
               [{'op': 'clear'}] + [{'op': 'edge', 'id': f"{s['arc'][0]}-{s['arc'][1]}", 'state': 'current'} for s in fixes]
               + labels(sts[-1]['y']), slides=[66], edges=[f"{s['arc'][0]}-{s['arc'][1]}" for s in fixes])
    L.ask("Why did pass one only fix arcs out of r, even though a d came first?",
          [[r'infinit|∞|inf|not (yet )?(reach|label|known)|no label|unlabel'], [r'\ba\b|tail|start|before|order|first']],
          'When a d was scanned, y_a was still ∞, so a d could not lower y_d. Arcs only help once their tail has a finite label, which is why order matters.',
          slides=[66])
    L.step("If after n minus one passes some arc is still incorrect, there must be a negative-cost dicircuit. Theorem "
           "2.17: Ford-Bellman either computes least-cost dipaths or detects a negative dicircuit, in order m n time.",
           "**Ford–Bellman.** Initialize $y, p$; $i = 0$; while $i < n$ and $y$ not feasible: $i \\leftarrow i + 1$, correct "
           "every incorrect $e \\in E$.\n**Theorem 2.17.** If $i < n$ at the end: least-cost dipaths found. If $i = n$: a "
           "negative-cost dicircuit exists. Time $O(mn)$.", [{'op': 'clear'}], slides=[67, 68, 69])
    return L


def lesson_acyclic():
    L = Lesson('u3-acyclic', U, 'Acyclic digraphs: one pass is enough', [85, 86, 87, 88, 89],
               'Use a topological sort to solve shortest paths in O(m).')
    arcs = [(a[0], a[1], '') for a in TOPO_S]
    L.figure(fig(TOPO, arcs, directed=True))
    L.step("First special case. A topological sort is an ordering of the nodes so that every arc goes from earlier to "
           "later. For this example from the slides the order is d, h, i, g, j, b, a, f.",
           "A **topological sort**: an ordering $v_1, \\dots, v_n$ with $v_iv_j \\in E \\Rightarrow i < j$.\n"
           "Example: $d, h, i, g, j, b, a, f$",
           [{'op': 'label', 'id': v, 'text': f'#{k}'} for k, v in enumerate(TOPO_ORDER, 1)], slides=[70])
    L.step("Now list the arcs by their tail's position: all arcs out of d, then out of h, and so on. Every dipath is then "
           "embedded in this one sequence, so Ford's algorithm finishes in a single pass.",
           "Order arcs by the position of their tail: $S = da, df, dg, di, hg, hj, ib, ig, ij, gf, jb, ba, af$.\n"
           "Every dipath is embedded in $S$ → Ford's algorithm needs **one pass**.",
           [{'op': 'path', 'ids': [f'{a[0]}-{a[1]}' for a in TOPO_S[:4]], 'style': 'augment'}], slides=[71, 72, 73, 74, 75, 76, 77, 78])
    L.ask('When does a digraph have a topological sort?',
          [[r'acyclic|no (di)?(circuit|cycle)|without (di)?(circuit|cycle)|dag']],
          'Exactly when it is acyclic, meaning it has no dicircuit (Observation on slide 80).', draw=[{'op': 'clear'}], slides=[79, 80])
    L.step("In practice we store the arcs leaving each node v in a list L v. Scanning v means correcting every incorrect "
           "arc in L v. Find a topological sort with r first, then scan the nodes in that order.",
           "Store arcs with tail $v$ in a list $L_v$; **scan** $v$ = correct every incorrect arc of $L_v$.\n"
           "**Shortest paths in an acyclic digraph:** 1. topological sort with $r = v_1$; 2. initialize $y, p$; 3. for $i = 1..n$: scan $v_i$\n"
           "(Nodes before $r$ in the order are unreachable and can be deleted.)", slides=[81])
    L.step("A topological sort can be found in order m time, every dipath is simple, and each arc is handled once. "
           "Theorem 2.18: shortest paths in an acyclic digraph take order m time.",
           "**Theorem 2.18.** The shortest path problem on an acyclic digraph can be solved in time $O(m)$.", slides=[82])
    return L


def lesson_dijkstra():
    L = Lesson('u3-dijkstra', U, "Nonnegative costs: Dijkstra's algorithm", [90, 91, 93, 94],
               "Run Dijkstra's algorithm on the slide example and see why it is O(n²).")
    L.figure(fig(DJ, DJ_E, directed=True))
    L.step("Second special case: all costs nonnegative, which is common. Then there's a one-pass algorithm that orders "
           "the nodes as it goes: next, scan the unscanned node with the smallest label.",
           "With $c \\ge 0$: a \"one-pass\" algorithm whose node order is computed during execution:\n"
           "$v_{i+1}$ = the unscanned node $v$ with **minimum** $y_v$.", slides=[83])
    L.step("Dijkstra's algorithm: initialize, put every node in Q, and while Q isn't empty, take the node in Q with "
           "minimum y, remove it, and scan it. This is the slide's example, rooted at r.",
           "**Dijkstra's algorithm**\n1. Initialize $y, p$\n2. $Q = V$\n3. While $Q \\ne \\emptyset$: choose $v \\in Q$ with "
           "$y_v$ minimum; delete $v$ from $Q$; scan $v$",
           [{'op': 'node', 'id': 'r', 'state': 'source'}] + labels({'r': 0, 'a': None, 'p': None, 'b': None, 'q': None}), slides=[84])
    res = dijkstra(list(DJ), [list(e) for e in DJ_E], 'r')
    before = {'r': 0, 'a': None, 'p': None, 'b': None, 'q': None}
    Q = list(DJ)
    for k, st in enumerate(res['steps']):
        u = st['settled']; du = st['distances'][u]; Q.remove(u)
        ups = [x for x in st['updates']]
        txt = ', '.join(f"{x['to']}: {y(before[x['to']])} → {x['new_distance']}" for x in ups) or 'no change'
        say = f"Smallest label in Q: {u}, at {du}. Scan it. " + (
            ' '.join(f"{x['to']} drops to {x['new_distance']}." if before[x['to']] is not None else f"{x['to']} gets {x['new_distance']}." for x in ups)
            if ups else 'Nothing improves.')
        tree = {f'{p}-{v}' for v, p in st['predecessors'].items() if p}
        draw = [{'op': 'clear'}, {'op': 'node', 'id': u, 'state': 'current'}] + \
               [{'op': 'edge', 'id': f'{a}-{b}', 'state': 'tree' if f'{a}-{b}' in tree else 'plain'} for a, b, _ in DJ_E] + \
               [{'op': 'label', 'id': x['to'], 'text': f"y={x['new_distance']}"} for x in ups] + \
               [{'op': 'node', 'id': u, 'state': 'settled'}]
        if k == 2:
            L.ask(f"Q is now {{{', '.join(Q + [u])}}}. Which node does Dijkstra scan next?",
                  [[rf'\b{u}\b']], f"{u}: it has the smallest label in Q, y_{u} = {du}.",
                  draw=[{'op': 'clear'}], slides=list(range(85, 97)))
        L.step(say, f"scan **{u}** ($y_{u} = {du}$): {txt}.  Q = {{{', '.join(Q)}}}", draw,
               why=f"{u} had the minimum label among unscanned nodes; with c ≥ 0 no later dipath can be cheaper.",
               slides=list(range(85, 97)), edges=[f'{u}-{x["to"]}' for x in ups])
        before = dict(st['distances'])
    fin = ', '.join(f'{k} {v}' for k, v in res['distances'].items())
    L.step(f"Done. Final labels {fin}, as on the slide, and the green arcs form the shortest-path tree.",
           f"Final: {fin}. Green arcs = shortest-path tree.", [{'op': 'clear'}], slides=[96])
    L.step("Why is it valid? Let y prime of w be w's label when it is scanned. Proposition 2.19: if u is scanned before "
           "v, then y prime u is at most y prime v. With nonnegative costs, scanning can never lower an earlier label.",
           "Let $y'_w$ = value of $y_w$ when $w$ is scanned.\n**Proposition 2.19.** If $u$ is scanned before $v$, then $y'_u \\le y'_v$.\n"
           "**Theorem.** Dijkstra's algorithm is valid.", slides=[99])
    L.step("Running time: scanning all nodes costs order m in total. Choosing the minimum takes about n squared over two "
           "comparisons overall. So Dijkstra is order n squared.",
           "Time = time to find $v$ + time to scan $v$. Scanning all nodes: $O(m)$. Choosing $v$: $1 + 2 + \\dots + (n-1) = O(n^2)$ comparisons.\n"
           "**Theorem 2.20.** If $c \\ge 0$, the shortest path problem can be solved in time $O(n^2)$.", slides=[100])
    return L


def lesson_bfs():
    L = Lesson('u3-bfs', U, 'Unit costs: breadth-first search', [95, 96, 97, 98, 99],
               'Turn Dijkstra into a queue: BFS finds fewest-arc dipaths in O(m).')
    L.figure(fig(BF, [(u, v, '') for u, v in BF_E], directed=True))
    L.step("Last special case: every arc costs one, so we want dipaths with as few arcs as possible. In Dijkstra's "
           "algorithm, a node's first finite label is then already final, and nodes get labels in increasing order.",
           "All $c_e = 1$: find dipaths with as few arcs as possible.\n**Proposition 2.21.** With unit costs, in Dijkstra's "
           "algorithm the final $y_v$ is the first finite value assigned. If $v$ gets its first finite value before $q$, then $y_v \\le y_q$.",
           slides=[101])
    L.step("So the node with the minimum label is simply the one that got its label first. Keep Q as a queue: take from "
           "the front, add to the back. That's constant time per node, so order m overall, and we don't even need y.",
           "Choose the element added to $Q$ first: keep $Q$ as a **queue** → $O(1)$ per choice → $O(m)$ total; no need to keep $y_v$.\n"
           "**Breadth-first search**\n1. Initialize $p$\n2. $Q = \\{r\\}$\n3. While $Q \\ne \\emptyset$: delete $v$ from the front of $Q$; "
           "for each $vw \\in L_v$: if $p(w) = -1$, add $w$ to the back of $Q$ and set $p(w) = v$",
           [{'op': 'node', 'id': '1', 'state': 'source'}], slides=[102, 103])
    run = bfs(list(BF), BF_E, '1')
    seen = ['1']
    for k, v in enumerate(run['order']):
        new = [w for w in run['order'] if run['pred'].get(w) == v]
        seen += new
        L.step(f"Take {v} from the front." + (f" It discovers {', '.join(new)}, added to the back." if new else ' Nothing new.'),
               f"dequeue **{v}**" + (f" → enqueue {', '.join(new)}" if new else '') + f"   Q order so far: {', '.join(seen)}",
               [{'op': 'clear'}, {'op': 'node', 'id': v, 'state': 'current'}] +
               [{'op': 'edge', 'id': f'{v}-{w}', 'state': 'tree'} for w in new] + [{'op': 'node', 'id': v, 'state': 'settled'}] +
               [{'op': 'label', 'id': w, 'text': f"d={run['dist'][w]}"} for w in new + ([v] if v == '1' else [])],
               slides=[105, 106] if k < 3 else list(range(107, 116)), edges=[f'{v}-{w}' for w in new])
        if k == 1:
            L.ask('Which node leaves the queue next?', [[rf"\b{run['order'][2]}\b|seven"]],
                  f"{run['order'][2]}: it was added to the queue right after 4.", slides=[106])
    L.step(f"The queue order was {', '.join(run['order'])}, exactly as on the slide. The blue tree arcs give a fewest-arc "
           "dipath from 1 to every node.",
           f"Q = {{{', '.join(run['order'])}}} (as on slide 115). Tree arcs = fewest-arc dipaths.", [{'op': 'clear'}], slides=[115])
    return L


def lessons():
    return [lesson_intro(), lesson_potential(), lesson_ford(), lesson_negative(), lesson_ford_bellman(), lesson_acyclic(),
            lesson_dijkstra(), lesson_bfs()]
