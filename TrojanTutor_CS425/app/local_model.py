"""Locally trained topic understanding model and evidence-bounded teaching policies."""
from pathlib import Path
import re
import joblib
ROOT=Path(__file__).resolve().parents[1]
MODEL_FILE=ROOT/'models/cs425_model.joblib'
_model=None
LESSONS={
 'tsp':('A traveling salesperson tour visits each required point and returns to its start while minimizing total distance. A nearest-neighbor tour is fast, but its locally cheapest next step need not yield the global optimum.','Why might a locally shortest next edge produce a poor complete tour?'),
 'matching':('A matching consists of edges that do not share endpoints. A perfect matching pairs every vertex exactly once. The Euclidean matching problem minimizes total pair length.','Would an edge set where one vertex participates twice still be a matching?'),
 'complexity':('Running-time analysis asks how the number of operations scales with input size. Enumerating all traveling-salesperson tours grows factorially, making brute force rapidly impractical.','Why is factorial growth problematic even if a single tour evaluation is fast?'),
 'mst':('A minimum spanning tree connects all vertices, contains no cycle, and minimizes the sum of chosen edge costs. It optimizes total network cost, not the distance from one designated source.','Can a minimum spanning tree differ from a shortest-path tree?'),
 'kruskal':('Kruskal sorts edges by cost and adds the next cheapest edge that does not create a cycle. The selected edges form a forest until all vertices are connected.','Why must Kruskal reject an edge whose endpoints are already connected?'),
 'prim':('Prim grows one connected tree, repeatedly choosing a cheapest edge crossing from the tree into an unvisited vertex.','How does Prim’s maintained structure differ from Kruskal’s forest?'),
 'shortest_path':('A shortest-path problem minimizes the cost from a chosen source to each reachable vertex. Relaxing an arc v→w improves the estimate when d[v] + cost(v,w) < d[w].','When would an arc relaxation change an estimated distance?'),
 'dijkstra':('Dijkstra repeatedly settles an unsettled vertex with minimum tentative distance. Its standard greedy correctness relies on nonnegative edge costs.','What breaks if an edge with negative cost leads to an already settled vertex?'),
 'bellman_ford':('Bellman–Ford repeatedly relaxes edges to compute shortest paths when negative edges may exist. A reachable negative cycle prevents finite shortest-path costs for affected destinations.','Why are repeated relaxation passes necessary?'),
 'dag':('A directed acyclic graph permits shortest-path relaxations in topological order, since all predecessors of a vertex can be processed first.','Why does topological ordering remove the need for repeated relaxation?'),
 'flow':('A feasible source-to-sink flow respects arc capacities and conserves flow at intermediate vertices. The objective is to maximize total delivered flow.','Why must inflow equal outflow at an intermediate vertex?'),
 'min_cut':('An s–t cut partitions vertices into a source side and a sink side. Its forward arc capacity upper-bounds the value of any feasible flow; the max-flow min-cut theorem says the optimal values coincide.','How can a cut prove no larger flow is possible?'),
 'augment':('An augmenting path in the residual network allows additional flow to move from source to sink. Reverse residual arcs represent the ability to undo an earlier flow decision.','Why do residual networks need reverse arcs?'),
}
CONCEPT_UNIT={'tsp':'Problems and Algorithms','matching':'Problems and Algorithms','complexity':'Problems and Algorithms','mst':'Minimum Spanning Trees','kruskal':'Minimum Spanning Trees','prim':'Minimum Spanning Trees','shortest_path':'Shortest Paths','dijkstra':'Shortest Paths','bellman_ford':'Shortest Paths','dag':'Shortest Paths','flow':'Maximum Flow','min_cut':'Maximum Flow','augment':'Maximum Flow'}

def get_model():
    global _model
    if _model is None:
        if not MODEL_FILE.exists():raise RuntimeError('Missing trained model: run python -m app.train_model')
        _model=joblib.load(MODEL_FILE)
    return _model

def classify(question):
    topic=get_model()['topic'];prob=topic.predict_proba([question])[0]; idx=prob.argmax()
    return str(topic.classes_[idx]),float(prob[idx])

def teach(question, unit, sources, history):
    # Resolve short anaphoric follow-up questions with the previous user question.
    prompt=question
    if len(question.split())<8 and re.search(r'\b(it|that|this|they|why|how|difference)\b',question,re.I):
        prior=next((m['content'] for m in reversed(history) if m.get('role')=='user'), '')
        prompt=prior+' '+question
    topic,confidence=classify(prompt)
    if confidence<.19 or CONCEPT_UNIT.get(topic)!=unit or not sources:
        if not sources:return 'I cannot locate a matching passage in the selected CS 425 unit. Could you name an algorithm or a theorem from the lecture?',topic,confidence
        return ('I found relevant lecture evidence, but my trained topic model is not confident enough to teach this question. '+
                'Please specify the concept or choose another unit. Evidence: '+sources[0]['excerpt'][:250]+'… [1]'),topic,confidence
    explanation,diagnostic=LESSONS[topic]
    # These explanations are expert-authored teaching rules, NOT language model generations.
    return f'{explanation}\n\nLecture evidence: {sources[0]["excerpt"][:300].strip()}… [1]\n\nCheck your understanding: {diagnostic}',topic,confidence
