"""Unit 1 — Problems and Algorithms (slides 1-34): TSP, brute force, nearest neighbor, circuit drawing,
Euclidean matching, measuring running time."""
import math

from . import Lesson, fig
from ..algorithms import (nearest_neighbor_tour, brute_force_tsp, tour_length, degrees, min_weight_pairing, dist)

U = 'Problems and Algorithms'
# 8 points: helicopter base H + 7 platforms. Chosen so nearest neighbour is visibly beaten (checked in tests).
PTS = {'H': (433, 158), 'A': (294, 224), 'B': (131, 263), 'C': (506, 158), 'D': (471, 247), 'E': (300, 52),
       'F': (476, 83), 'G': (233, 130)}


def r(x):
    return f'{x:,.0f}'


def human(secs):
    if secs < 1e-3:
        return f'{secs * 1e6:,.2f} µs'
    if secs < 120:
        return f'{secs:,.1f} s'
    if secs < 3600 * 24 * 2:
        return f'{secs / 3600:,.1f} hours'
    if secs < 3600 * 24 * 365.25 * 2:
        return f'{secs / 86400:,.0f} days'
    return f'{secs / (3600 * 24 * 365.25):,.0f} years'


def _points_fig():
    return fig({k: (x, y, 'base' if k == 'H' else 'point') for k, (x, y) in PTS.items()})


def _legs(tour, closed=True):
    t = list(tour) + ([tour[0]] if closed else [])
    return t


def lesson_tsp():
    L = Lesson('u1-tsp', U, 'The oil company and the Traveling Salesman Problem', [1, 2, 3, 4],
               'State the Euclidean TSP precisely and see what a tour is.')
    nn = brute_force_tsp(PTS, 'H')
    some = ['H', 'E', 'B', 'C', 'G', 'F', 'A', 'D']
    L.figure(_points_fig())
    L.step("Welcome to combinatorial optimization. We'll start with two famous problems: the traveling salesman "
           "problem and the matching problem. We'll see what they share, how they differ, and how to measure "
           "the size of a problem and the running time of an algorithm.",
           "**Problems and Algorithms**: the plan\n- The Traveling Salesman Problem (TSP)\n- The Matching Problem\n"
           "- Their similarities and differences\n- The size of a problem and the running time of an algorithm",
           slides=[2])
    L.step("Here's the story from the lecture. An oil company has forty-seven drilling platforms. Every so often a "
           "helicopter must leave its base, visit certain platforms to adjust their controls, and come back. "
           "The company wants the route with the least total flying time.",
           "**Oil company problem**\n- 47 drilling platforms; some must be visited periodically\n"
           "- A helicopter leaves from the base H and returns to it\n- Goal: visit the required platforms with "
           "minimum total flying time\n- Assumption: flying time is proportional to distance",
           [{'op': 'node', 'id': 'H', 'state': 'source'}, {'op': 'note', 'id': 'n1', 'x': 433, 'y': 128, 'text': 'base'}],
           slides=[4])
    L.step("In math terms this is the Euclidean traveling salesman problem. The input is a set of points in the plane. "
           "The distance between two points is the straight-line distance. We want a tour that passes through every "
           "point once and returns, with the smallest total length.",
           "**Euclidean TSP**\n- Input: points $V = \\{(x_i, y_i) : i = 1,\\dots,n\\}$ in the plane\n"
           "- Distance: $\\sqrt{(x_i - x_j)^2 + (y_i - y_j)^2}$\n- Objective: a tour through every point of $V$ once, "
           "with minimum total distance\n- Here $V$ = the platforms to visit plus the base",
           [{'op': 'unnote', 'id': 'n1'}], slides=[5, 6])
    L.step(f"Here is one tour, chosen without much thought. It has length {r(tour_length(PTS, some))}.",
           f"One possible tour: {' → '.join(some + ['H'])}\nLength ≈ {r(tour_length(PTS, some))}",
           [{'op': 'tour', 'id': 't', 'ids': _legs(some), 'style': 'alt'}], slides=[7])
    L.step(f"And here is the best tour for these points: length {r(nn['length'])}. Same points, very different cost. "
           "Finding that best tour is the whole problem.",
           f"Optimal tour: {' → '.join(nn['tour'] + ['H'])}\nLength ≈ {r(nn['length'])}  (instance → optimal solution, as on slide 7)",
           [{'op': 'tour', 'id': 't', 'ids': _legs(nn['tour']), 'style': 'opt'}], slides=[7])
    L.ask('Is it ever profitable to pass through a platform more than once?',
          [[r'\bno\b|never|not (profitable|worth|useful|help)|doesn.?t help|wouldn.?t'],
           [r'straight|direct|shortcut|triangle|longer|detour|extra|shorter']],
          'No. Flying straight to the next platform is never longer than detouring through another point, so a '
          'repeated visit can only add distance.', slides=[6])
    return L


def lesson_brute_force():
    L = Lesson('u1-brute', U, 'Brute force: try every tour', [5],
               'Count the tours and see why trying them all is hopeless.')
    sq = {'1': (150, 80), '2': (410, 80), '3': (410, 250), '4': (150, 250)}
    tours = [['1', '2', '3', '4'], ['1', '2', '4', '3'], ['1', '3', '2', '4']]
    L.figure(fig({k: (x, y, 'point') for k, (x, y) in sq.items()}))
    L.step("There are only finitely many tours, so here's an obvious algorithm. List every tour, measure each, and "
           "keep the best. Fix the starting point, and a tour and its reverse are the same, so there are "
           "n minus one factorial over two different tours.",
           "**Brute force algorithm**\n1. List all $(n-1)!/2$ different tours\n2. Evaluate each one\n3. Pick the best",
           slides=[8])
    for k, t in enumerate(tours, 1):
        L.step(f"With four points there are three factorial over two, which is three tours. Tour {k} has length "
               f"{r(tour_length(sq, t))}.",
               f"n = 4: tour {k} of 3: {'–'.join(t + ['1'])}, length {r(tour_length(sq, t))}",
               [{'op': 'tour', 'id': 't', 'ids': _legs(t), 'style': 'opt' if k == 1 else 'alt'}], slides=[8])
    rows = []
    for n in (5, 10, 15, 23):
        tours_n = math.factorial(n - 1) // 2
        secs = tours_n * 1e-9
        rows.append((n, tours_n, secs))
    cent = rows[-1][2] / (3600 * 24 * 365.25 * 100)
    L.step(f"But the count explodes. Even if checking one tour takes a single nanosecond, twenty-three points "
           f"would take about {cent:.0f} centuries.",
           "Tours to check at 1 ns each:\n" + '\n'.join(
               f"- n = {n}: {t:,} tours → {human(s)}" for n, t, s in rows) + f"\n- n = 23 ≈ **{cent:.0f} centuries**",
           [{'op': 'untour', 'id': 't'}], slides=[9, 10])
    L.ask('How does 2 to the n compare with n factorial as n grows?',
          [[r'n!|factorial|n fact'], [r'fast|bigger|larger|more|grow|dominat|much|huge']],
          'n! grows much faster. From n = 4 on, n! is larger than 2ⁿ, and the gap widens, because every new '
          'factor of n! is bigger than 2 (for n = 23: 2²³ ≈ 8.4 million, but 23! ≈ 2.6 × 10²²).', slides=[10])
    return L


def lesson_nearest_neighbor():
    L = Lesson('u1-nn', U, 'The nearest neighbor heuristic', [6, 19],
               'Run nearest neighbor and see why fast is not the same as optimal.')
    run = nearest_neighbor_tour(PTS, 'H')
    best = brute_force_tsp(PTS, 'H')
    L.figure(_points_fig())
    L.step("A much faster idea: start anywhere, always fly to the nearest platform you haven't visited, and when "
           "everything is visited, go home. It's quick, but it doesn't guarantee the best tour. Let's run it from the base.",
           "**Nearest Neighbor Algorithm** (fast, not guaranteed optimal)\n1. Pick any starting point\n"
           "2. Go to the nearest point not yet visited\n3. Repeat until all points are visited\n4. Return to the start",
           [{'op': 'node', 'id': 'H', 'state': 'source'}], slides=[11, 32])
    path = ['H']
    for k, st in enumerate(run['steps'], 1):
        path.append(st['chosen'])
        others = [c for c in st['candidates'] if c != st['chosen']]
        far = (f"closer than {', '.join(others[:2])}" if others else 'the last one left')
        L.step(f"From {st['from']}, the nearest unvisited point is {st['chosen']}, {far}.",
               f"{k}. {st['from']} → {st['chosen']}  ({r(dist(PTS[st['from']], PTS[st['chosen']]))})",
               [{'op': 'rays', 'id': 'r', 'from': st['from'], 'to': st['candidates']},
                {'op': 'tour', 'id': 'nn', 'ids': list(path), 'style': 'nn'}], slides=[12, 13])
    L.step(f"Everything is visited, so we fly back to the base. Total length {r(run['length'])}. Notice that long "
           "flight home at the end.",
           f"Return {path[-1]} → H.  Nearest-neighbor tour length ≈ **{r(run['length'])}**",
           [{'op': 'unrays', 'id': 'r'}, {'op': 'tour', 'id': 'nn', 'ids': _legs(run['tour']), 'style': 'nn'}], slides=[14])
    pct = 100 * (run['length'] / best['length'] - 1)
    L.step(f"Now compare with the optimal tour, found by checking all {best['tours_checked']:,} tours: length "
           f"{r(best['length'])}. Nearest neighbor came out about {pct:.0f} percent longer.",
           f"Optimal tour (brute force over {best['tours_checked']:,} tours): ≈ **{r(best['length'])}**\n"
           f"Nearest neighbor is ≈ {pct:.0f}% longer.",
           [{'op': 'tour', 'id': 'nn', 'ids': _legs(run['tour']), 'style': 'alt'},
            {'op': 'tour', 'id': 'opt', 'ids': _legs(best['tour']), 'style': 'opt'}], slides=[14])
    L.ask("Why isn't the nearest neighbor tour optimal?",
          [[r'greed|nearest|closest|local|short.?sight|myopic|each step|cheap'],
           [r'later|end|long|return|never|undo|reconsider|forced|back|future']],
          'It is greedy: each move is the cheapest one available right now, and it never reconsiders. Early short '
          'hops can strand the tour far from the remaining points, forcing long legs later, like the flight home.',
          slides=[13])
    L.step("A question from the slides to think about: can you build a family of point sets where nearest neighbor "
           "does badly? Hint: arrange points so the closest choice keeps leading you away from where you'll need to come back.",
           "**Think about it** (slide 13): construct instances where Nearest Neighbor performs \"badly\".",
           [{'op': 'untour', 'id': 'opt'}], slides=[13])
    return L


# A figure with odd nodes for the plotter problem.
CIRC = {'a': (150, 250), 'b': (330, 250), 'c': (330, 110), 'd': (150, 110), 'e': (240, 40), 'f': (470, 250)}
CIRC_E = [('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'a'), ('d', 'e'), ('e', 'c'), ('a', 'c'), ('b', 'f')]


def lesson_circuit():
    L = Lesson('u1-circuit', U, 'Drawing a circuit with a plotter: odd nodes', [7, 8, 9, 10, 11],
               'Connect pen-up time to odd nodes and see that it becomes a matching problem.')
    deg = degrees(CIRC_E)
    odd = sorted(v for v, d in deg.items() if d % 2 == 1 and d != 2)
    nodes_def = sorted(v for v, d in deg.items() if d != 2)
    length, pairs = min_weight_pairing(CIRC, odd)
    L.figure(fig({k: (x, y, 'point') for k, (x, y) in CIRC.items()}, CIRC_E))
    L.step("Second application. A plotter draws a logic circuit by moving a pen while rolling the paper. "
           "It must end where it started. The time is pen-down time, while actually drawing, plus pen-up time, "
           "while moving without drawing.",
           "**Circuit drawing problem**\n- A plotter draws the figure; the pen must return to its start\n"
           "- Time = \"pen-down\" time (drawing) + \"pen-up\" time (moving without drawing)\n"
           "- Drawing a line twice never helps: it costs time and draws nothing new",
           slides=[15])
    L.step("Pen-down time is fixed: every line must be drawn once. So the only thing we can reduce is pen-up time. "
           "And usually some pen-up motion is unavoidable. To see why, look at the nodes.",
           "Pen-down time is fixed → we minimize **pen-up time**.\nSome pen-up motion is necessary. Why?", slides=[17])
    draw = [{'op': 'note', 'id': f'deg{v}', 'x': CIRC[v][0] + 14, 'y': CIRC[v][1] - 14,
             'text': f'{deg[v]}' + (' odd' if v in odd else ''), 'style': 'bad' if v in odd else ''} for v in nodes_def]
    draw += [{'op': 'node', 'id': v, 'state': 'current'} for v in odd]
    L.step(f"A node is a point where some number of lines other than two meet. It's odd if an odd number of lines "
           f"meet there. In this figure the odd nodes are {', '.join(odd)}.",
           "- A **node**: a point where a positive number of lines, other than 2, meet\n"
           f"- A node is **odd** if an odd number of lines meet there, **even** otherwise\nOdd nodes here: {', '.join(odd)}",
           draw, slides=[18])
    L.step("The key theorem: the figure can be drawn, returning to the start, without tracing a line twice and "
           "without lifting the pen, if and only if it is connected and has no odd nodes.",
           "**Theorem.** The figure can be drawn, returning to the start, without retracing and with no pen-up "
           "motion **iff** it is connected and has **no odd nodes**.", slides=[19])
    L.ask('A second theorem says the number of odd nodes is always even. Why?',
          [[r'two ends|2 ends|each (line|edge)|twice|handshak|sum of (the )?degree|total|counted'], [r'even']],
          'Every line has two ends, so adding up the number of lines at every node gives twice the number of lines, '
          'an even number. The even nodes add an even amount, so the odd nodes together must too, and that needs '
          'an even number of odd nodes.', slides=[20])
    L.step(f"So here's the plan. Add new lines that pair up the odd nodes, making every node even, with the least "
           f"total length. The cheapest pairing here is {' and '.join(a + ' ' + b for a, b in pairs)}, total "
           f"{r(length)}. Choosing that pairing is exactly a matching problem, our second problem.",
           "Minimize pen-up motion: add new lines joining the odd nodes in pairs so every node becomes even, with "
           f"minimum total length.\nBest pairing here: {', '.join(a + b for a, b in pairs)}, total ≈ {r(length)}\n"
           "→ This is a **matching problem**.",
           [{'op': 'pairs', 'id': 'm', 'pairs': [list(p) for p in pairs], 'style': 'new'}], slides=[21])
    return L


HEX = {k: (280 + 150 * math.cos(math.radians(a)), 160 + 120 * math.sin(math.radians(a)))
       for k, a in zip('123456', (0, 60, 120, 180, 240, 300))}
HEX['2'] = (HEX['2'][0] + 40, HEX['2'][1] - 25)     # make it irregular so one matching is clearly best


def lesson_matching():
    L = Lesson('u1-matching', U, 'Euclidean matching, and how it differs from TSP', [12, 13, 14],
               'State the matching problem and the key contrast with TSP.')
    m1 = [('1', '4'), ('2', '5'), ('3', '6')]
    m2 = [('1', '2'), ('3', '4'), ('5', '6')]
    m3 = [('2', '3'), ('4', '5'), ('6', '1')]
    lens = [sum(dist(HEX[a], HEX[b]) for a, b in m) for m in (m1, m2, m3)]
    bestL, best = min_weight_pairing(HEX, list(HEX))
    L.figure(fig({k: (x, y, 'point') for k, (x, y) in HEX.items()}))
    L.step("The Euclidean matching problem: given an even number of points, draw lines so that every point is the "
           "end of exactly one line, and the total length is as small as possible.",
           "**Euclidean matching problem**\n- Input: a set $V$ of points in the plane, $|V|$ even\n"
           "- Objective: a set of lines so that each point is the end of exactly one line, minimizing the total length",
           slides=[22])
    for k, (m, Lm) in enumerate(zip((m1, m2, m3), lens), 1):
        L.step(f"Option {k}: total length {r(Lm)}.", f"Matching {k}: {', '.join(a + b for a, b in m)}  → {r(Lm)}",
               [{'op': 'pairs', 'id': 'm', 'pairs': [list(p) for p in m], 'style': 'opt' if k == 1 else 'alt'}], slides=[24])
    bk = 1 + lens.index(min(lens))
    L.ask('Which of the three matchings is optimal, and why?',
          [[rf'\b{bk}\b|' + {1: 'one|first', 2: 'two|second', 3: 'three|third|last'}[bk]]],
          f"Matching {1 + lens.index(min(lens))} is the shortest of these three ({r(min(lens))}). Checking every "
          f"matching, the true optimum here has length {r(bestL)}. Long diagonal pairs waste length.", slides=[24])
    L.step("How do TSP and matching compare? Both pick lines between points, both have far too many feasible "
           "solutions to check, and simple heuristics do poorly on both. The big difference: matching has an "
           "efficient algorithm. For the traveling salesman problem none is known, and most researchers believe "
           "none exists. If one did, nearly every combinatorial optimization problem would have one too.",
           "**Similarities**\n- Choose sets of lines connecting points in the plane\n- Far too many feasible solutions "
           "to consider them all\n- Simple heuristics don't perform well\n**Major difference**\n- Euclidean matching: an "
           "**efficient algorithm exists**\n- Euclidean TSP: none known; most researchers believe none exists\n"
           "- An efficient TSP algorithm would give one for almost every combinatorial optimization problem",
           [{'op': 'unpairs', 'id': 'm'}], slides=[25, 26])
    return L


def lesson_running_time():
    L = Lesson('u1-runtime', U, 'Measuring running time and polynomial-time algorithms', [16, 17, 18, 20, 21],
               "Count steps, define problem size and O-notation, and show nearest neighbor is polynomial-time.")
    n = len(PTS)
    L.figure(_points_fig())
    L.step("What makes an algorithm efficient? We bound the number of elementary steps it needs, as a function of "
           "the problem's size. Elementary steps are things like reading, writing, adding, multiplying, dividing "
           "and comparing. The bound covers every instance, so it's an estimate, and a better bound doesn't "
           "always mean faster in practice.",
           "**Measuring running time**\n- Efficiency = an upper bound on the number of steps for problems of a given size\n"
           "- Only an estimate: the bound is over all instances\n- A better bound isn't necessarily better in practice\n"
           "- Count elementary operations: read, write, +, ×, ÷, comparison", slides=[28])
    L.step("The size of a problem is the length of an encoding of its structure plus how many numbers it uses. "
           "For the Euclidean traveling salesman problem we just list the x and y coordinates of the n points, "
           "so the size is two n.",
           "**Size of a problem** $s$ = length of the encoding of the structure + number of numbers used\n"
           "- Euclidean TSP: give $(x_i, y_i)$ for the $n$ points → $s = 2n$", slides=[29, 30])
    L.step("We care about large instances, so we keep only the order of magnitude. Five s squared plus three s is "
           "order s squared. Formally, f is in big O of g if f is at most a constant times g for all large enough s.",
           "**Magnitude of the bound**\n$f(s) \\in O(g(s))$ if there is $c > 0$ with $f(s) \\le c \\cdot g(s)$ for all large $s$.\n"
           "- $5s^2 + 3s \\in O(s^2)$\n- $35 \\cdot 2^s + s^3 \\in O(2^s)$\n"
           "**Polynomial-time** (efficient) algorithms have bounds $O(s^k)$ for some $k$.", slides=[31])
    L.step(f"Let's count nearest neighbor. Each pass takes the current point and scans every unmarked point: "
           f"check its mark, compute the squared distance, keep the best. Here, from H that's {n - 1} scans.",
           "**Nearest neighbor, step count** (slide 33)\n- Initialization: $(x_i, y_i, \\text{mark}=0)$ per point: $3n$ steps\n"
           "- Pass $n-1$ times: scan the other points; per point 1 compare + 6 steps for distance² + 2 to track the best\n"
           "- Then output the next point (1) and mark it (1)",
           [{'op': 'node', 'id': 'H', 'state': 'source'}, {'op': 'rays', 'id': 'r', 'from': 'H', 'to': [k for k in PTS if k != 'H']}],
           slides=[33])
    total = 3 * n + (n - 1) * ((n - 1) * 9 + 2)
    L.step(f"In total at most three n plus n minus one times nine n minus seven steps, which is order n squared. "
           f"For our {n} points that's at most {total} steps. Since s is two n, that's order s squared: nearest "
           "neighbor is a polynomial-time algorithm.",
           f"At most $3n + (n-1)((n-1)\\cdot 9 + 2)$ steps $\\in O(n^2)$  (here n = {n}: ≤ {total} steps)\n"
           "With $s = 2n$: $O(n^2) = O((s/2)^2) \\subseteq O(s^2)$ → **polynomial-time**",
           [{'op': 'unrays', 'id': 'r'}], slides=[33, 34])
    L.ask('Is the brute force algorithm a polynomial-time algorithm?',
          [[r'\bno\b|not|isn.?t'], [r'factorial|n!|tours|exponential|grow|faster|polynom']],
          'No. It examines (n−1)!/2 tours, and n! grows faster than s^k for every fixed k, so no polynomial bound holds.',
          slides=[31, 34])
    return L


def lessons():
    return [lesson_tsp(), lesson_brute_force(), lesson_nearest_neighbor(), lesson_circuit(), lesson_matching(),
            lesson_running_time()]
