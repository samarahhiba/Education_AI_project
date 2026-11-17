# TrojanTutor v0.12: the whole course, taught with synced voice, writing and diagrams

**What changed:** the tutor now teaches **every slide of the four CS 425 decks**, in order, as 32 lessons
(246 steps, 33 check questions). For each step the tutor:

- **speaks** a short explanation (written for the ear, no symbols),
- **writes it out clearly** in the conversation (with formulas rendered), typed in step with the voice,
- **draws** exactly what is being said on a redrawn version of the slide's own figure: the same
  graphs, node names and edge costs, with the current edge, cycle, cut, tour, label or flow highlighted.

At check questions it **waits for your answer** (typed or spoken), grades it with simple rules, and says
so when it can't tell. You can interrupt any time (type, speak, or click an edge). The lesson pauses,
answers about the board as it is, and continues when you say "continue".

## The 32 lessons

| Unit | Lessons |
|---|---|
| Problems & Algorithms (6) | Oil company & TSP · Brute force · Nearest neighbor · Circuit drawing & odd nodes · Euclidean matching vs TSP · Running time & polynomial-time |
| Minimum Spanning Trees (10) | Graphs · Subgraphs & deletion · Paths & circuits · Connector → MST · **Exercise: solve the slide-22 MST yourself** · Kruskal · Prim · Cuts & correctness (Lemma 2.7, Thm 2.4–2.6) · Efficiency of Prim · Efficiency of Kruskal (blocks) |
| Shortest Paths (8) | Driving distances & digraphs · Improving paths & feasible potentials · Ford's algorithm · Negative dicircuits & correctness · Ford–Bellman (the slide's S₁–S₃ passes) · Acyclic digraphs · Dijkstra · Unit costs & BFS |
| Maximum Flow (8) | Trucks & dipaths · Flows · Cuts bound flows · Max-flow min-cut & augmenting paths · Augmenting path algorithm · Number of augmentations (the "M" example) · Bipartite matchings & covers · König's theorem via max flow |

**Coverage is tested.** `tests/test_course.py` fails if any slide chunk is neither taught nor listed in
`SKIPPED` (title pages, section dividers, transition and "QUIZ!" slides, each listed with a reason).

## Faithful diagrams

The figures were transcribed from the PDF pages, and the lessons reproduce the slides' numbers. Tests check each of these:

- Kruskal/Prim graph (slides 23–36): MST cost **108**, the same red tree.
- MST exercise (slide 22): solved interactively, total 51.
- r, a, b, d digraph: Ford reaches y = (0, 2, 1, 4) as at "iteration 5"; Ford–Bellman with the slide's passes S₁, S₂, S₃.
- Negative dicircuit (slides 53–59): y_a = 4 at iteration 5, as on slide 57.
- Topological sort (slides 70–78): reconstructed from the arc sequence S printed on the slide.
- Dijkstra (slides 84–96): final labels a 2, p 3, b 4, q 6. The directions of the two diagonal arcs were
  reconstructed so these labels hold.
- BFS (slides 105–115): queue order 1, 4, 7, 6, 10, 3, 9, 2, 5, 8, 11.
- Max flow (slides 5–52): the r, p, a, q, b, s network, flow value 4, min cut R = {r, q, a}.
- Two-diamond cut (slide 15): max flow 1.
- "M" example (slides 54–59): 2M augmentations vs 2 with shortest paths.

Figures that were too dense to transcribe (the TSP point cloud, the plotter circuit, the bipartite graph)
are replaced by small illustrative versions, and the lesson says what it shows. Every algorithm run is
computed by tested code in `app/algorithms.py` when the lesson is built.

## Voice interpretability

You didn't specify the voice problem, so v0.12 fixes both directions.

**Understanding you:**
- Course vocabulary is repaired in what the browser heard: "crystals algorithm" → Kruskal, "dykstra" →
  Dijkstra, "die path" → dipath, "mint cut" → min cut, "conic theorem" → König, and "edge bee and dee"
  → edge b and d. The recogniser's alternatives are scored for course words.
- What it understood is shown under the input box ("Heard: …"), so a misunderstanding is visible.
- Commands work even mid-sentence: "continue", "repeat", "back", "stop".
- The tutor's own voice is ignored (echo filter), and one-word commands are never mistaken for noise.

**Being understood:**
- A pronunciation lexicon for the speech engine: Dijkstra → "Dyke-struh", König → "Kur-nig",
  TSP/MST/BFS spelled out, symbols (δ, ε, ∞, ≤, →) read as words.
- Lesson speech never contains formulas; those are written in the conversation instead.

## API added

`GET /api/course`, `GET /api/course/lesson/{id}`, `POST /api/course/check`, `POST /api/course/ask`,
`POST /api/course/progress`, `GET /api/slides?unit=&pages=`, `POST /api/speech/normalize`.
Progress and every answer/interruption are stored per session (SQLite).

## Known limits

- Check questions are graded by keyword rules. Unclear answers get "compare with how I'd put it",
  never a false "correct". A TA should review the expected answers.
- The browser speech recogniser still decides what it hears; the vocabulary repair fixes the common
  course-term errors but not everything. Headphones help.
- Lesson narration is authored from the slides (by me, as the assistant) and should be reviewed by the
  instructor/TA before students rely on it.
