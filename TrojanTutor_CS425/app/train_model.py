"""Train a local supervised CS425 topic model on lecture pages and authored study questions.
No external foundation model is used. Reproducible: python -m app.train_model.
"""
from pathlib import Path
from collections import Counter
import json, re, random
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

ROOT=Path(__file__).resolve().parents[1]
SLIDES=json.loads((ROOT/'data/slides.json').read_text())
# Carefully bounded concept labels; samples are written specifically to match lecture topics.
CONCEPTS={
 'tsp':['TSP','traveling salesman problem','tsp tour','nearest neighbor heuristic','visit all vertices and return to starting point','factorial brute force route','helicopter platforms tour'],
 'matching':['euclidean matching','pair each point exactly once','matching minimum length','odd vertices circuit drawing','perfect matching'],
 'complexity':['polynomial algorithm','running time growth','exponential algorithm','factorial time complexity','size of input'],
 'mst':['MST','minimum spanning tree','minimum cost spanning connected graph','spanning tree vs shortest path','tree with n minus one edges','forest cycle edge'],
 'kruskal':['kruskal algorithm','sort edges and skip cycles','add cheapest safe edge','union find spanning forest','why reject an edge that forms a cycle'],
 'prim':['prim algorithm','grow tree from a vertex','minimum crossing edge tree','cut property minimum spanning tree'],
 'shortest_path':['shortest dipath','source destination minimum distance','shortest path relaxation','directed weighted path','feasible potential shortest path'],
 'dijkstra':['dijkstra algorithm','greedy shortest path nonnegative edge','why dijkstra cannot handle negative weights','settle nearest distance vertex'],
 'bellman_ford':['bellman ford algorithm','ford bellman relaxation','negative cost edges shortest path','negative cycle detection','multiple passes edge relaxation'],
 'dag':['acyclic digraph shortest paths','topological order shortest path','directed acyclic graph paths'],
 'flow':['maximum flow problem','network flow conservation','source sink feasible flow','arc capacities cannot be exceeded','trucks network flow'],
 'min_cut':['minimum cut problem','cut capacity','max flow min cut theorem','bottleneck cut bound','source sink partition'],
 'augment':['augmenting path algorithm','residual network','reverse residual arc','increase flow along a residual path','ford fulkerson algorithm'],
}
QUESTIONS=[]
for label, phrases in CONCEPTS.items():
    for phrase in phrases:
        for template in ['{}','Explain {}','What is {}?','Help me understand {}','Can you teach me {}?','Why does {} matter?','Give an example of {}']:
            QUESTIONS.append((template.format(phrase),label))
# Course material is direct training data for the unit recognition task.
UNIT_NAMES=sorted(set(s['unit'] for s in SLIDES))
unit_samples=[]
for s in SLIDES:
    t=re.sub(r'\s+',' ',s['text']).strip()
    if len(t)>60:
        unit_samples.append((t[:1200],s['unit']))
        if len(t)>350:unit_samples.append((t[150:850],s['unit']))

def train():
    random.Random(425).shuffle(QUESTIONS)
    # Entire original user-query phrases are grouped by index to avoid leaking exact wording
    bybase=[]
    for label,phrases in CONCEPTS.items():
        for phrase in phrases:
            bybase.append((phrase,label))
    rng=random.Random(425);rng.shuffle(bybase)
    held=set((p,l) for p,l in bybase[::5])
    train_pairs=[];test_pairs=[]
    for label,phrases in CONCEPTS.items():
        for phrase in phrases:
            for template in ['{}','Explain {}','What is {}?','Help me understand {}','Can you teach me {}?','Why does {} matter?']:
                (test_pairs if (phrase,label) in held else train_pairs).append((template.format(phrase),label))
    topic=Pipeline([('vectorizer',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,stop_words='english')),
                    ('classifier',SGDClassifier(loss='log_loss',alpha=0.00008,random_state=425,max_iter=2500,tol=1e-4))])
    topic.fit([x for x,y in train_pairs],[y for x,y in train_pairs])
    predictions=topic.predict([x for x,y in test_pairs])
    score=accuracy_score([y for x,y in test_pairs],predictions)
    unit=Pipeline([('vectorizer',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,stop_words='english',max_features=14000)),
                   ('classifier',SGDClassifier(loss='log_loss',alpha=0.0001,random_state=425,max_iter=2500,tol=1e-4))])
    rng.shuffle(unit_samples)
    split=int(len(unit_samples)*.8)
    unit.fit([x for x,y in unit_samples[:split]],[y for x,y in unit_samples[:split]])
    unit_score=accuracy_score([y for x,y in unit_samples[split:]],unit.predict([x for x,y in unit_samples[split:]]))
    out=ROOT/'models';out.mkdir(exist_ok=True)
    joblib.dump({'topic':topic,'unit':unit,'concepts':CONCEPTS},out/'cs425_model.joblib')
    report={'model_type':'TF-IDF + supervised SGD logistic-loss classifiers','trained_on':'265 lecture pages and authored CS425 question patterns','topic_training_examples':len(train_pairs),'topic_test_examples':len(test_pairs),'topic_heldout_phrase_accuracy':round(float(score),3),'unit_page_chunk_test_accuracy':round(float(unit_score),3),'unit_training_examples':split,'unit_test_examples':len(unit_samples)-split,'limitations':'Not an LLM; cannot generate unconstrained explanations. Slides have duplicates across successive animation pages, so unit test score is optimistic.'}
    (out/'training_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':train()
