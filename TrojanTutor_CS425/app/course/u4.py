"""Unit 3 — Maximum Flow (slides 1-77). Networks redrawn from the slides: the r,p,a,q,b,s network
(slides 5-11, 22, 36-52), the two-diamond cut example (slide 15), the "what we have / what we want" example
(slides 27-28), the M example (slides 54-59), and a bipartite graph in the style of slides 64-77."""
from . import Lesson, fig
from ..algorithms import max_flow, check_flow, augment_path

U = 'Maximum Flow'
INF_CAP = 1000          # stands for ∞ in the König construction (any value > |P| works)

MF = {'r': (45, 165), 'p': (200, 55), 'a': (370, 55), 'q': (200, 280), 'b': (370, 280), 's': (520, 165)}
MF_A = [('r', 'p', 1), ('r', 'q', 4), ('p', 'a', 1), ('a', 'p', 1), ('p', 'b', 3), ('q', 'a', 3), ('q', 'b', 1),
        ('b', 'q', 1), ('a', 's', 1), ('b', 's', 4)]
BEND = {('p', 'a'): -22, ('a', 'p'): -22, ('q', 'b'): 22, ('b', 'q'): 22}

DIA = {'r': (35, 160), 'u': (135, 70), 'w': (135, 250), 'm': (235, 160), 'n': (325, 160), 'x': (425, 70), 'z': (425, 250), 's': (525, 160)}
DIA_A = [('r', 'u', 10), ('r', 'w', 10), ('u', 'm', 10), ('w', 'm', 10), ('u', 'w', 10), ('m', 'n', 1), ('n', 'x', 10),
         ('n', 'z', 10), ('x', 's', 10), ('z', 's', 10), ('x', 'z', 10)]

HW = {'r': (60, 165), 'a': (290, 55), 'b': (290, 275), 's': (520, 165)}      # slides 27-28
HW_A = [('r', 'a', 1), ('r', 'b', 1), ('a', 'b', 1), ('a', 's', 1), ('b', 's', 1)]

M = 100
BAD = {'r': (70, 165), 't': (290, 50), 'w': (290, 280), 's': (510, 165)}
BAD_A = [('r', 't', M), ('r', 'w', M), ('t', 'w', 1), ('t', 's', M), ('w', 's', M)]

BP_P = ['p1', 'p2', 'p3', 'p4']
BP_Q = ['q1', 'q2', 'q3', 'q4']
BP_E = [('p1', 'q1'), ('p2', 'q1'), ('p2', 'q2'), ('p2', 'q3'), ('p3', 'q1'), ('p4', 'q3'), ('p4', 'q4')]


def mf_fig(arcs=MF_A, label=lambda c: f'0/{c}'):
    return fig(MF, [(u, v, label(c), BEND.get((u, v), 0)) for u, v, c in arcs], directed=True)


def xlabels(arcs, x):
    return [{'op': 'elabel', 'id': f'{u}-{v}', 'text': f"{x.get(f'{u}>{v}', 0)}/{'∞' if c >= INF_CAP else c}"} for u, v, c in arcs]


def xstates(arcs, x):
    return [{'op': 'edge', 'id': f'{u}-{v}', 'state': 'full' if x.get(f'{u}>{v}', 0) == c else
             ('accept' if x.get(f'{u}>{v}', 0) > 0 else 'plain')} for u, v, c in arcs]


def lesson_trucks():
    L = Lesson('u4-trucks', U, 'Sending trucks: families of dipaths', [101, 103, 104],
               'State the problem of sending as many trucks as possible within street limits.')
    L.figure(mf_fig(label=lambda c: str(c)))
    L.step("Unit three: maximum flow and minimum cut. We'll prove the max-flow min-cut theorem and learn the augmenting "
           "path algorithm, which solves both problems at once.",
           "**Maximum Flow**: the plan\n- The Maximum Flow Problem and the Minimum Cut Problem\n- The Max-Flow Min-Cut Theorem\n"
           "- The Augmenting Path algorithm, solving both at once", slides=[2])
    L.step("We want to send as many trucks as possible from point r to point s through a street network. Each street "
           "segment e allows at most u e trucks.",
           "**Trucks problem**: send as many trucks as possible from $r$ to $s$; street segment $e$ allows at most $u_e$ trucks.",
           [{'op': 'node', 'id': 'r', 'state': 'source'}, {'op': 'node', 'id': 's', 'state': 'sink'}], slides=[4])
    paths = [['r', 'p', 'a', 's'], ['r', 'q', 'b', 's'], ['r', 'q', 'a', 'p', 'b', 's']]
    L.step("As a graph problem: find a family of dipaths from r to s, as many as possible, such that each arc e is used "
           "by at most u e of them. The numbers on the arcs are the u e.",
           "**Problem.** On digraph $G$, find a family $(P_1, \\dots, P_k)$ of $(r,s)$-dipaths such that each arc $e$ is in at "
           "most $u_e$ of them, with $k$ maximum.", slides=[5])
    for k, P in enumerate(paths, 1):
        L.step(f"Dipath {k}: {', '.join(P)}.", f"$P_{k} = {', '.join(P)}$",
               [{'op': 'path', 'ids': [f'{a}-{b}' for a, b in zip(P, P[1:])], 'style': 'augment' if k == 1 else ('cycle' if k == 2 else 'focus')}],
               slides=[6, 7, 8])
    L.ask("The slide's family has three dipaths. Can you find four?",
          [[r'yes|four|4|can'], [r'r.{0,3}p.{0,3}b.{0,3}s|r.{0,3}q.{0,3}a.{0,3}s|\bpb\b|\bqa\b']],
          'Yes: r,p,b,s; r,q,b,s; r,q,a,s; r,q,a,p,b,s respects every capacity, giving 4. We will prove 4 is the maximum.',
          draw=[{'op': 'clear'}], slides=[8])
    return L


def lesson_flows():
    L = Lesson('u4-flows', U, 'Flows: conservation, capacities, value', [105, 106, 107, 108, 109, 110],
               'Turn a family of dipaths into a flow and define its value.')
    x = {'r>p': 1, 'r>q': 3, 'p>a': 0, 'a>p': 1, 'p>b': 2, 'q>a': 2, 'q>b': 1, 'b>q': 0, 'a>s': 1, 'b>s': 3}
    val = check_flow(list(MF), MF_A, x, 'r', 's')
    L.figure(mf_fig())
    L.step("Count, for each arc, how many dipaths use it. Call that x e. For the four dipaths we just found, here are the "
           "counts, written x over u.",
           "For each arc $e$: $x_e := |\\{i : P_i \\text{ uses } e\\}|$. Labels show $x_e / u_e$.",
           xlabels(MF_A, x) + xstates(MF_A, x), slides=[9])
    L.step("Every dipath that enters a middle node also leaves it, so at each node other than r and s, flow in equals "
           "flow out. Look at a: two units come in from q, one goes to p and one to s.",
           "**Flow conservation** (1): $\\sum_{wv \\in E} x_{wv} - \\sum_{vw \\in E} x_{vw} = 0$ for all $v \\in V \\setminus \\{r, s\\}$\n"
           "At $a$: in $= x_{qa} + x_{pa} = 2 + 0$, out $= x_{ap} + x_{as} = 1 + 1$ ✓",
           [{'op': 'node', 'id': 'a', 'state': 'current'}, {'op': 'path', 'ids': ['q-a', 'p-a', 'a-p', 'a-s'], 'style': 'focus'}],
           slides=[9, 10])
    L.step("We also need zero at most x e at most u e, and for trucks, x e integer. An r s flow satisfies conservation; it's "
           "feasible if it also respects capacities, and integral if every x e is an integer.",
           "(2) $0 \\le x_e \\le u_e$  (3) $x_e$ integer\n- $x$ is an **$(r,s)$-flow** if it satisfies (1)\n"
           "- **feasible** if also (2)\n- **integral** if also (3)", [{'op': 'clear'}], slides=[10])
    L.step(f"The net flow into v is flow in minus flow out. The value of the flow is the net flow into s, here {val}, which "
           "is the number of dipaths. A flow is acyclic if no dicircuit carries positive flow on every arc.",
           "Net flow into $v$: $f_x(v) := \\sum_{wv} x_{wv} - \\sum_{vw} x_{vw}$. **Value** of $x$: $f_x(s)$ = number of dipaths $k$.\n"
           f"Here $f_x(s) = x_{{as}} + x_{{bs}} = 1 + 3 = {val}$.\n$x$ is **acyclic** if no dicircuit has $x_e > 0$ on all its arcs.",
           [{'op': 'node', 'id': 's', 'state': 'current'}], slides=[11])
    L.step("And it goes back the other way. Proposition 3.1: such a family of k dipaths exists exactly when there's an "
           "integral feasible flow of value k. So the trucks problem is the maximum integral flow problem.",
           "**Proposition 3.1.** A family of $k$ $(r,s)$-dipaths with $|\\{i : P_i \\text{ uses } e\\}| \\le u_e$ exists **iff** an integral "
           "feasible $(r,s)$-flow of value $k$ exists.\n**Maximum Integral Flow:** max $f_x(s)$ s.t. $f_x(v) = 0$ ($v \\ne r,s$), "
           "$0 \\le x_e \\le u_e$, $x_e$ integer.", [{'op': 'clear'}], slides=[12, 13])
    L.ask('If we drop the integrality constraint, what problem do we get, and what values may capacities take?',
          [[r'max(imum)?.?flow'], [r'non.?negative|real|infinit|∞|any|reals']],
          'The maximum flow problem. Capacities u_e may be any nonnegative real numbers or ∞ (no upper bound on that arc).',
          slides=[14])
    return L


def lesson_cuts():
    L = Lesson('u4-cuts', U, 'Cuts give upper bounds on flow', [111, 112, 113, 114],
               'Define (r,s)-cuts and prove every flow is at most every cut capacity.')
    L.figure(fig(DIA, [(u, v, c) for u, v, c in DIA_A], directed=True))
    L.step("There's a natural way to bound the maximum flow. Look at this network: lots of capacity ten, but everything "
           "has to squeeze through the single middle arc of capacity one.",
           "How do we get **upper bounds** on the maximum flow value?",
           [{'op': 'node', 'id': 'r', 'state': 'source'}, {'op': 'node', 'id': 's', 'state': 'sink'},
            {'op': 'edge', 'id': 'm-n', 'state': 'current'}], slides=[15])
    R = ['r', 'u', 'w', 'm']
    L.step("For a set of nodes R, the cut delta of R is the set of arcs leaving R. Its capacity is the total capacity of "
           "those arcs. An r s cut has r inside R and s outside. With R the left diamond, the cut is just the arc m n, "
           "capacity one.",
           "A **cut** $\\delta(R) := \\{vw \\in E : v \\in R, w \\notin R\\}$, $R \\subseteq V$.\n**Capacity** $u(\\delta(R)) = \\sum_{vw \\in \\delta(R)} u_{vw}$.\n"
           "An **$(r,s)$-cut** has $r \\in R$, $s \\notin R$. Notation: $\\bar A = V \\setminus A$.\nHere $R = \\{r, u, w, m\\}$: $\\delta(R) = \\{mn\\}$, capacity 1.",
           [{'op': 'shade', 'nodes': R, 'label': 'R'}, {'op': 'edge', 'id': 'm-n', 'state': 'cut'}], slides=[16, 17])
    L.step("Proposition 3.3: for any r s cut and any flow, the flow out across the cut minus the flow back across it "
           "equals the flow value. Corollary 3.4: for a feasible flow, the value is at most the cut's capacity.",
           "**Proposition 3.3.** For any $(r,s)$-cut $\\delta(R)$ and $(r,s)$-flow $x$: $x(\\delta(R)) - x(\\delta(\\bar R)) = f_x(s)$.\n"
           "**Corollary 3.4.** For feasible $x$: $f_x(s) \\le u(\\delta(R))$.", slides=[18, 19, 20, 21])
    L.ask('So what is the maximum flow value in this network, and how do you know?',
          [[r'\b1\b|one'], [r'cut|bottleneck|middle|mn|m.?n|capacity|bound']],
          'It is 1. The cut around the left diamond has capacity 1, so no flow can exceed 1, and sending one unit '
          'r→u→m→n→x→s achieves it.', slides=[15, 21])
    L.step("So the maximum flow is at most the minimum cut capacity. If we ever find a flow and a cut with the same value, "
           "both are optimal. The theorem we're heading for says this always happens.",
           "⇒ max flow value ≤ min cut capacity. A flow and a cut with **equal** value are both optimal, and this can always be done.",
           [{'op': 'path', 'ids': ['r-u', 'u-m', 'm-n', 'n-x', 'x-s'], 'style': 'augment'}], slides=[21])
    return L


def lesson_mfmc():
    L = Lesson('u4-mfmc', U, 'The Max-Flow Min-Cut Theorem and augmenting paths', [115, 116, 117, 118, 119],
               'State the theorem and discover x-augmenting paths, including reverse arcs.')
    x = {'r>p': 1, 'r>q': 3, 'p>a': 0, 'a>p': 1, 'p>b': 2, 'q>a': 2, 'q>b': 1, 'b>q': 0, 'a>s': 1, 'b>s': 3}
    res = max_flow(list(MF), [list(a) for a in MF_A], 'r', 's')
    L.figure(mf_fig())
    L.step(f"The Max-Flow Min-Cut Theorem: if a maximum flow exists, its value equals the minimum capacity of an r s cut. "
           f"Here's a flow of value 4, and the cut R equal to {', '.join(res['cut_R'])}: its arcs all carry full flow, "
           f"capacity {res['cut_capacity']}.",
           "**Theorem 3.5 (Max-Flow Min-Cut).** If there is a maximum $(r,s)$-flow, then\n"
           "$$\\max\\{f_x(s) : x \\text{ feasible}\\} = \\min\\{u(\\delta(R)) : \\delta(R) \\text{ an } (r,s)\\text{-cut}\\}$$\n"
           f"Example: value 4, cut $R = \\{{{', '.join(res['cut_R'])}\\}}$ of capacity {res['cut_capacity']}.",
           xlabels(MF_A, x) + xstates(MF_A, x) + [{'op': 'shade', 'nodes': res['cut_R'], 'label': 'R'}] +
           [{'op': 'edge', 'id': f'{u}-{v}', 'state': 'cut'} for u, v, _ in res['cut_arcs']], slides=[22])
    L.figure(fig(HW, [(u, v, f'{"1" if (u, v) in (("r", "a"), ("a", "b"), ("b", "s")) else "0"}/{c}') for u, v, c in HW_A], directed=True))
    L.step("We prove it by solving both problems. Idea: given a feasible flow, find a better one. Here one unit goes r, a, "
           "b, s. Is there an r s dipath where every arc still has room? No: r a and b s are full.",
           "Proof plan: solve both problems. Given feasible $x$, find one of larger value.\n**What we have:** 1 unit on $r, a, b, s$. "
           "No dipath with $x_e < u_e$ on every arc remains, yet this is **not** maximum.",
           [{'op': 'node', 'id': 'r', 'state': 'source'}, {'op': 'node', 'id': 's', 'state': 'sink'},
            {'op': 'path', 'ids': ['r-a', 'a-b', 'b-s'], 'style': 'augment'}], slides=[23, 24, 25, 26, 27])
    x0 = {'r>a': 1, 'a>b': 1, 'b>s': 1}
    x1, eps = augment_path(HW_A, x0, ['r', 'b', 'a', 's'])
    L.step(f"Use the path r, b, a, s, going backwards along a b. Forward arcs gain flow, the reverse arc a b loses it. "
           f"Pushing {eps} gives value {check_flow(list(HW), HW_A, x1, 'r', 's')}: r, a, s and r, b, s.",
           "**What we want:** use path $r, b, a, s$ with $ab$ as a **reverse** arc: $+1$ on $rb, as$, $-1$ on $ab$.\n"
           f"New value: {check_flow(list(HW), HW_A, x1, 'r', 's')}",
           [{'op': 'clear'}, {'op': 'path', 'ids': ['r-b', 'a-b', 'a-s'], 'style': 'focus'}] + xlabels(HW_A, x1) + xstates(HW_A, x1),
           slides=[27, 28])
    L.step("A path is x-incrementing if every forward arc has x below u and every reverse arc has x above zero. An "
           "x-augmenting path is an incrementing path from r to s. Pushing along it raises the flow value.",
           "A path is **$x$-incrementing** if every forward arc has $x_e < u_e$ and every reverse arc has $x_e > 0$.\n"
           "An **$x$-augmenting path** is an $x$-incrementing $(r,s)$-path; it increases the flow value.", slides=[29, 30])
    L.ask("In the path r, b, a, s, why is it fine to send flow 'backwards' along a b?",
          [[r'x.?ab|ab.{0,20}(1|positive|flow|>\s*0)|already (has|carr)|cancel|undo|reduc|decreas|remov']],
          'Because a b already carried 1 unit. Sending back along it just reduces x_ab (undoing that flow), which is allowed while x_ab > 0.',
          slides=[29, 30])
    L.step("Theorem 3.6: a feasible flow is maximum exactly when there is no x-augmenting path. That, plus the cut we "
           "find when the search fails, proves the max-flow min-cut theorem.",
           "**Theorem 3.6.** A feasible flow $x$ is maximum **iff** there is no $x$-augmenting path.", slides=[31, 32])
    return L


def lesson_augmenting():
    L = Lesson('u4-augmenting', U, 'The augmenting path algorithm', [120, 121, 122, 123, 124],
               'Run the algorithm with the auxiliary digraph and read off the minimum cut.')
    L.figure(mf_fig())
    L.step("The algorithm: start from zero flow and repeatedly push the maximum amount epsilon along an x-augmenting "
           "path. Epsilon is the smaller of two minimums: the room u minus x on forward arcs, and x on reverse arcs.",
           "**Augmenting Path Algorithm.** From $x = 0$, repeatedly find an $x$-augmenting path $P$ and augment by\n"
           "$\\varepsilon := \\min(\\varepsilon_1, \\varepsilon_2)$, $\\varepsilon_1 = \\min\\{u_e - x_e : e \\text{ forward}\\}$, "
           "$\\varepsilon_2 = \\min\\{x_e : e \\text{ reverse}\\}$.\nIf no augmenting path exists, $x$ is maximum (Theorem 3.6), and the "
           "nodes reachable from $r$ by incrementing paths define a minimum cut.",
           [{'op': 'node', 'id': 'r', 'state': 'source'}, {'op': 'node', 'id': 's', 'state': 'sink'}], slides=[33])
    L.step("With integral capacities, round them down. Each augmentation is then integral, so the final maximum flow is "
           "integral too: max flow solves the trucks problem.",
           "Integral flows: replace $u_e$ by $\\lfloor u_e \\rfloor$; every iteration keeps $x$ integral ⇒ the maximum flow is integral.", slides=[34])
    L.step("How do we search? Build the auxiliary digraph G of x: it has arc v w when v w has spare room, and also when "
           "w v carries flow, since we can undo it. Augmenting paths are exactly the r s dipaths in G of x, found by "
           "breadth-first search in order m time.",
           "**Auxiliary digraph** $G(x)$: $V(G(x)) = V$,\n$E(G(x)) = \\{vw : vw \\in E,\\ x_{vw} < u_{vw}\\ \\text{or}\\ wv \\in E,\\ x_{wv} > 0\\}$.\n"
           "$x$-augmenting paths ↔ $(r,s)$-dipaths in $G(x)$; each iteration is $O(m)$ with BFS.", slides=[35, 36])
    res = max_flow(list(MF), [list(a) for a in MF_A], 'r', 's')
    cap = {f'{u}>{v}': c for u, v, c in MF_A}
    prev = {k: 0 for k in cap}
    for k, st in enumerate(res['steps'], 1):
        ids = [a['arc'].replace('>', '-') for a in st['arcs']]
        room = [cap[a['arc']] - prev[a['arc']] if a['direction'] == 'forward' else prev[a['arc']] for a in st['arcs']]
        rev = [a['arc'].replace('>', '') for a in st['arcs'] if a['direction'] == 'reverse']
        draw = [{'op': 'clear'}, {'op': 'path', 'ids': ids, 'style': 'augment'}] + xlabels(MF_A, st['flow']) + xstates(MF_A, st['flow'])
        if k == 2:
            L.ask(f"The next augmenting path is {', '.join(st['path'])}. How much can we push?",
                  [[rf"\b{st['epsilon']}\b|\b{['zero', 'one', 'two', 'three', 'four'][st['epsilon']]}\b"]],
                  f"ε = {st['epsilon']}: the smallest room along the path ({', '.join(str(r) for r in room)}).",
                  draw=[{'op': 'clear'}, {'op': 'path', 'ids': ids, 'style': 'focus'}], slides=list(range(37, 53)))
        L.step(f"Augmenting path {', '.join(st['path'])}. Room along it: {', '.join(str(r) for r in room)}. Push "
               f"{st['epsilon']}." + (f" It uses {', '.join(rev)} in reverse, undoing earlier flow." if rev else '') +
               f" Value now {st['value']}.",
               f"{k}. $P = {', '.join(st['path'])}$, ε = {st['epsilon']}" + (f" (reverse: {', '.join(rev)})" if rev else '') + f" → value {st['value']}",
               draw, why=f"Every arc on {', '.join(st['path'])} had room in G(x); ε is the smallest room.",
               slides=list(range(37, 53)), edges=ids)
        prev = st['flow']
    L.step(f"No augmenting path is left: from r, the auxiliary digraph only reaches {', '.join(res['cut_R'])}. That set R "
           f"gives a cut of capacity {res['cut_capacity']}, equal to the flow value {res['value']}. Both are optimal.",
           f"Stop: $R = \\{{{', '.join(res['cut_R'])}\\}}$, $u(\\delta(R)) = {res['cut_capacity']} = f_x(s)$ ⇒ maximum flow and minimum cut.",
           [{'op': 'clear'}, {'op': 'shade', 'nodes': res['cut_R'], 'label': 'R'}] +
           [{'op': 'edge', 'id': f'{u}-{v}', 'state': 'cut'} for u, v, _ in res['cut_arcs']], slides=[52])
    return L


def lesson_count():
    L = Lesson('u4-count', U, 'How many augmentations? Shortest augmenting paths', [125, 126, 127, 128],
               'See why bad path choices are slow and why shortest paths fix it.')
    L.figure(fig(BAD, [(u, v, ('M' if c == M else c)) for u, v, c in BAD_A], directed=True))
    L.step("The running time depends on the number of augmentations. Theorem 3.9: with integral capacities and maximum "
           "value K, the algorithm stops after at most K augmentations, since each adds at least one.",
           "**Theorem 3.9.** If each $u_e$ is integral or $\\infty$ and the max flow value is $K < \\infty$, the algorithm "
           "terminates after at most $K$ augmentations (each adds ≥ 1).", slides=[53])
    x = {}
    bad = [['r', 't', 'w', 's'], ['r', 'w', 't', 's']]
    for k, P in enumerate(bad, 1):
        x, eps = augment_path(BAD_A, x, P)
        v = check_flow(list(BAD), BAD_A, x, 'r', 's')
        ids = [f'{a}-{b}' if (a, b) in [(u, w) for u, w, _ in BAD_A] else f'{b}-{a}' for a, b in zip(P, P[1:])]
        L.step(f"That bound can actually be reached. Choose the path {', '.join(P)}" +
               (", using the middle arc backwards" if k == 2 else ", through the middle arc") +
               f". Its bottleneck is the middle arc, so we push only {eps}. Value {v}.",
               f"Bad choice {k}: $P = {', '.join(P)}$, ε = {eps}, value {v}",
               [{'op': 'clear'}, {'op': 'path', 'ids': ids, 'style': 'augment'}] +
               [{'op': 'elabel', 'id': f'{u}-{w}', 'text': f"{x.get(f'{u}>{w}', 0)}/{'M' if c == M else c}"} for u, w, c in BAD_A],
               slides=[54, 55, 56, 57, 58, 59], edges=ids)
    L.ask(f"If we keep alternating like this, how many augmentations does it take to reach the maximum value 2M?",
          [[r'2\s*m|two\s*m|2 times m|twice m|200|2m']],
          'About 2M: each augmentation adds just 1, so it depends on the capacities, even though two augmentations '
          '(r,t,s and r,w,s) would do.', slides=[54])
    good = max_flow(list(BAD), [list(a) for a in BAD_A], 'r', 's')
    L.step(f"Shortest augmenting paths fix this. Call a path shortest if it has as few arcs as possible. Breadth-first "
           f"search picks r, t, s and r, w, s, and finishes in {len(good['steps'])} augmentations with value {good['value']}.",
           f"An $x$-augmenting path is **shortest** if it has the fewest arcs. Here BFS finds $r,t,s$ and $r,w,s$: "
           f"{len(good['steps'])} augmentations, value {good['value']} = 2M.",
           [{'op': 'clear'}] + [{'op': 'elabel', 'id': f'{u}-{w}', 'text': (lambda f: ('M' if f == M else str(f)) + '/' + ('M' if c == M else str(c)))(good['flow'].get(f'{u}>{w}', 0))} for u, w, c in BAD_A]
           + [{'op': 'path', 'ids': ['r-t', 't-s', 'r-w', 'w-s'], 'style': 'augment'}], slides=[60])
    L.step("Theorem 3.10: with shortest augmenting paths, at most n m augmentations, regardless of capacities. Each BFS "
           "is order m, so Corollary 3.11: maximum flow in order n m squared time.",
           "**Theorem 3.10.** Augmenting along shortest paths needs at most $nm$ augmentations.\n"
           "**Corollary 3.11.** The augmenting path algorithm with BFS solves max flow in $O(nm^2)$.", slides=[60, 61])
    return L


def bp_fig():
    pos = {p: (170, 50 + 80 * i) for i, p in enumerate(BP_P)}
    pos.update({q: (390, 50 + 80 * i) for i, q in enumerate(BP_Q)})
    return fig(pos, BP_E)


def konig_data():
    nodes = ['r'] + BP_P + BP_Q + ['s']
    arcs = [['r', p, 1] for p in BP_P] + [[p, q, INF_CAP] for p, q in BP_E] + [[q, 's', 1] for q in BP_Q]
    res = max_flow(nodes, arcs, 'r', 's')
    M_ = [(p, q) for p, q in BP_E if res['flow'][f'{p}>{q}'] == 1]
    R = set(res['cut_R'])
    C = [p for p in BP_P if p not in R] + [q for q in BP_Q if q in R]
    return nodes, arcs, res, M_, C


def lesson_matching():
    L = Lesson('u4-matching', U, 'Bipartite matchings and covers', [130, 131, 132, 133, 134, 135],
               'Define matchings and covers and show |M| ≤ |C|.')
    _, _, _, M_, C = konig_data()
    L.figure(bp_fig())
    L.step("Applications. The marriage problem: two groups P and Q, and the pairs who like each other. Arrange as many "
           "marriages as possible, each between a liking pair, with no one married twice.",
           "**Marriage problem**: sets $P$, $Q$ of people, pairs $(p, q)$ that like each other; arrange as many "
           "(monogamous) marriages as possible between liking pairs.", slides=[63])
    L.step("As a graph: nodes P union Q, an edge for each liking pair. Every edge goes between the two sides; such a "
           "graph is bipartite, and P, Q is its bipartition.",
           "Graph $G$: $V = P \\cup Q$, $E \\subseteq \\{pq : p \\in P, q \\in Q\\}$. A graph whose nodes split into two sets with "
           "every edge between them is **bipartite**; $\\{P, Q\\}$ is a **bipartition**.", slides=[64])
    L.step(f"A matching is a set of edges, no two sharing an end. The marriage problem asks for a maximum matching. "
           f"Here's one with {len(M_)} edges.",
           f"A **matching** $M \\subseteq E$: no two edges share an end. Marriage problem = maximum matching.\n"
           f"Shown: $M = \\{{{', '.join(p + q for p, q in M_)}\\}}$, $|M| = {len(M_)}$",
           [{'op': 'edge', 'id': f'{p}-{q}', 'state': 'accept'} for p, q in M_], slides=[65])
    L.step(f"A cover is a set of nodes touching every edge. Here {', '.join(C)} is a cover: every edge has an end among them.",
           f"A **cover** $C$: a set of nodes such that every edge has at least one end in $C$.\nShown: $C = \\{{{', '.join(C)}\\}}$, $|C| = {len(C)}$",
           [{'op': 'node', 'id': v, 'state': 'current'} for v in C], slides=[66])
    L.ask('Why is every matching at most as large as every cover?',
          [[r'each (matching )?edge|every (matching )?edge|end in c|endpoint|covered'], [r'distinct|different|share|no two|disjoint|own|separate']],
          'Each matching edge has an end in C, and since matching edges share no ends, those ends are all different nodes '
          'of C. So |M| ≤ |C|.', slides=[67])
    L.step(f"So if a matching and a cover have the same size, the matching is maximum. Here both have size {len(M_)}. "
           "Notice p one and p three both like only q one: at most one of them can be matched.",
           "**Observation.** For any matching $M$ and cover $C$, $|M| \\le |C|$. If $|M| = |C|$, $M$ is maximum (and $C$ minimum).",
           slides=[67, 68])
    return L


def lesson_konig():
    L = Lesson('u4-konig', U, "König's theorem via maximum flow", [136, 137, 138, 139, 140, 141, 142],
               "Build the flow network G′ and read off a maximum matching and a minimum cover.")
    nodes, arcs, res, M_, C = konig_data()
    pos = {'r': (40, 165), 's': (520, 165)}
    pos.update({p: (200, 45 + 80 * i) for i, p in enumerate(BP_P)})
    pos.update({q: (360, 45 + 80 * i) for i, q in enumerate(BP_Q)})
    L.figure(fig(pos, [(u, v, '∞' if c >= INF_CAP else c) for u, v, c in arcs], directed=True))
    L.step("König's theorem: in a bipartite graph, the maximum size of a matching equals the minimum size of a cover. "
           "We'll prove it with maximum flows.",
           "**Theorem 3.14 (König).** For a bipartite graph $G$: $\\max\\{|M| : M \\text{ matching}\\} = \\min\\{|C| : C \\text{ cover}\\}$.",
           slides=[69])
    L.step("Build G prime: add a source r and a sink s. Arc r p with capacity one for each p, arc q s with capacity one "
           "for each q, and each edge p q becomes an arc p q with infinite capacity.",
           "$G'$: $V' = V \\cup \\{r, s\\}$; arcs $pq$ ($p \\in P, q \\in Q$) of capacity $\\infty$; $rp$ of capacity 1; $qs$ of capacity 1.",
           [{'op': 'node', 'id': 'r', 'state': 'source'}, {'op': 'node', 'id': 's', 'state': 'sink'}], slides=[70, 71])
    L.step(f"Run the augmenting path algorithm. It finds a flow of value {res['value']}. Each p sends at most one unit and "
           "each q receives at most one, so the flow is zero-one, and the arcs p q carrying flow form a matching.",
           f"Max integral flow value $k = {res['value']}$; it is $\\{{0,1\\}}$-valued. $M = \\{{pq : x_{{pq}} = 1\\}}$ = "
           f"{{{', '.join(p + q for p, q in M_)}}} is a matching with $|M| = k$.",
           [{'op': 'edge', 'id': f'{a}-{b}', 'state': 'accept'} for a, b in [k.split('>') for k, v in res['flow'].items() if v == 1]],
           slides=[72, 73])
    L.ask('Why is this flow zero-one valued on every arc?',
          [[r'capacity (of )?1|capacity one|only 1|at most (1|one)|one unit|rp|qs'], [r'conserv|in.?=.?out|enter|leav|each p|each q|into p|out of q']],
          'Each p receives at most 1 unit (its only incoming arc rp has capacity 1) and must send out what it receives; '
          'likewise each q can send at most 1 to s. So every arc carries 0 or 1.', slides=[72])
    R = res['cut_R']
    L.step(f"Now take the minimum cut, R equal to {{{', '.join(R)}}}. It has finite capacity, so no infinite arc leaves R: "
           f"no edge goes from P inside R to Q outside R. So the nodes of P outside R together with the nodes of Q inside R "
           f"cover every edge: {', '.join(C)}.",
           f"Min cut $\\delta'(\\{{r\\}} \\cup U)$, $R = \\{{{', '.join(R)}\\}}$. Finite capacity ⇒ no edge from $P \\cap U$ to $Q \\setminus U$ ⇒\n"
           f"$C := (P \\setminus U) \\cup (Q \\cap U) = \\{{{', '.join(C)}\\}}$ is a cover, and $|C| = u(\\delta') = {res['cut_capacity']}$.",
           [{'op': 'shade', 'nodes': R, 'label': 'R'}] + [{'op': 'node', 'id': v, 'state': 'current'} for v in C], slides=[74, 75])
    L.step(f"By max-flow min-cut, the cut capacity {res['cut_capacity']} equals the flow value {res['value']}, so the matching "
           "and the cover have the same size: the matching is maximum and the cover minimum. That proves König's theorem, "
           "and gives an algorithm: at most |P| augmentations, order n m time.",
           f"$|M| = k = u(\\delta') = |C|$ ⇒ $M$ maximum, $C$ minimum. **König's theorem** follows.\n"
           "Algorithm: max flow on $G'$; at most $|P| \\le n$ augmentations (Theorem 3.9) ⇒ maximum bipartite matching in $O(nm)$.",
           [{'op': 'shade', 'nodes': []}], slides=[76, 77])
    return L


def lessons():
    return [lesson_trucks(), lesson_flows(), lesson_cuts(), lesson_mfmc(), lesson_augmenting(), lesson_count(),
            lesson_matching(), lesson_konig()]
