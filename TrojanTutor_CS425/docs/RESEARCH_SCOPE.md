# Week 1 scope and research framing

**Course:** UW–Madison ISyE/Math/CS 425, Introduction to Combinatorial Optimization (Prof. Carla Michini). **Pilot topic:** minimum spanning trees, with shortest paths as a contrast case. **Research direction:** does structured diagnosis plus adaptive follow-up improve students' independent understanding of graph algorithms over a fixed Socratic baseline? This week builds infrastructure only; no learning-gain claim is justified.

## Learning objectives

1. Define spanning tree and total edge cost; distinguish MST from shortest path trees.
2. Walk through Kruskal's increasing-cost edge selection and explain cycle rejection.
3. Interpret a shortest-path relaxation and explain Dijkstra's nonnegative-weight restriction.
4. Locate evidence in the supplied lecture slides and distinguish quoted claims from algorithm outputs.

## Candidate misconceptions to evaluate later

- 'MST is the same as shortest paths from a source.'
- 'Kruskal should add every low-cost edge, even if it closes a cycle.'
- 'Dijkstra is correct on negative-weight graphs.'
- 'Maximum flow and minimum cut have the same definition rather than equal optimal values.'

## Pilot evidence

Provided PDFs: Problems and Algorithms (34 pages); Minimum Spanning Trees (54); Shortest Paths (115); Maximum Flow (77). The lexical index excludes pages with very little extractable text; 265 pages retained. These UW lectures are not USC-approved materials. Obtain instructor permission before classroom integration or distribution. The software retains slide-level names and page numbers but cannot interpret every diagram reliably.

## Week 1 acceptance evidence

- FastAPI skeleton, browser UI, tests: implemented and locally tested.
- Scoped slide retrieval and provenance: implemented.
- Socratic multi-turn LLM: implemented as *optional API path*, requires live API credentials for verification; offline fallback is extractive only.
- Voice interruption/resume: implemented using browser APIs, should be manually tested in Chrome.
- Research outcomes, diagnosis, adaptation, delayed tests: planned for later phases, **not yet implemented**.

## Planned checkpoints

Nov 16–22: reliably stream text and improve state handling. Nov 23–29: evaluate citations, chunking and ingestion; obtain permission for additional slides. Nov 30–Dec 6: persistent sessions and repeatable error-free demo. Dec 7–20: speech performance and interrupt latency. Dec 21–Jan 3: create expert-reviewed scenarios and fixed Socratic baseline. Jan–Feb: implement misconception labels and adaptive policy, then compare on held-out cases. March: reproducible evaluation and study proposal, subject to approval.
