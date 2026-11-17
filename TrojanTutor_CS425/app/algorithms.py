"""Verifiable algorithm animations: Kruskal and Dijkstra, not LLM calculations."""
import heapq

def validate_graph(nodes,edges):
    if not isinstance(nodes,list) or not 2<=len(nodes)<=30 or len(set(nodes))!=len(nodes):raise ValueError('Provide 2-30 distinct nodes')
    if not isinstance(edges,list) or len(edges)>150:raise ValueError('At most 150 edges')
    result=[]
    for e in edges:
        if not isinstance(e,list) or len(e)!=3:raise ValueError('Every edge must be [from,to,weight]')
        u,v,w=e
        if u not in nodes or v not in nodes or u==v:raise ValueError('Invalid edge endpoints')
        if not isinstance(w,(int,float)) or isinstance(w,bool) or not -1e6<=w<=1e6:raise ValueError('Invalid numeric weight')
        result.append((u,v,w))
    return result

def kruskal(nodes,edges):
    edges=validate_graph(nodes,edges)
    parent={x:x for x in nodes};rank={x:0 for x in nodes}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    steps=[];chosen=[];total=0
    for u,v,w in sorted(edges,key=lambda e:(e[2],str(e[0]),str(e[1]))):
        a,b=find(u),find(v);accept=a!=b
        if accept:
            if rank[a]<rank[b]:a,b=b,a
            parent[b]=a
            if rank[a]==rank[b]:rank[a]+=1
            chosen.append([u,v,w]);total+=w
        steps.append({'edge':[u,v,w],'decision':'accept' if accept else 'skip: cycle','chosen':[list(x) for x in chosen],'total':total})
    return {'algorithm':'Kruskal','steps':steps,'edges':chosen,'total':total,'spanning':len(chosen)==len(nodes)-1}

def dijkstra(nodes,edges,start):
    edges=validate_graph(nodes,edges)
    if start not in nodes:raise ValueError('Start node is not in graph')
    if any(w<0 for _,_,w in edges):raise ValueError('Dijkstra requires nonnegative arc weights')
    adj={n:[] for n in nodes}
    for u,v,w in edges:adj[u].append((v,w))
    dist={n:float('inf') for n in nodes};pred={n:None for n in nodes};dist[start]=0
    heap=[(0,str(start),start)];settled=set();steps=[]
    while heap:
        cost,_,u=heapq.heappop(heap)
        if u in settled:continue
        settled.add(u);updated=[]
        for v,w in adj[u]:
            if cost+w<dist[v]:
                dist[v]=cost+w;pred[v]=u;heapq.heappush(heap,(dist[v],str(v),v));updated.append({'to':v,'new_distance':dist[v]})
        steps.append({'settled':u,'updates':updated,'distances':{str(k):(None if val==float('inf') else val) for k,val in dist.items()},'predecessors':dict(pred)})
    return {'algorithm':'Dijkstra','steps':steps,'distances':{str(k):(None if v==float('inf') else v) for k,v in dist.items()},'predecessors':pred}

DEMO_NODES=['A','B','C','D','E']
DEMO_MST=[['A','B',4],['A','C',2],['B','C',1],['B','D',5],['C','D',8],['C','E',10],['D','E',2]]
DEMO_PATH=[['A','B',4],['A','C',2],['C','B',1],['B','D',5],['C','D',8],['D','E',2],['B','E',10]]


def prim(nodes, edges, root):
    """Prim from `root`: repeatedly add the cheapest edge leaving the current tree (slides 30-36)."""
    edges = validate_graph(nodes, edges)
    if root not in nodes: raise ValueError('Root is not in graph')
    in_tree = {root}; chosen = []; total = 0; steps = []
    while len(in_tree) < len(nodes):
        crossing = [(w, str(u), str(v), u, v) for u, v, w in edges if (u in in_tree) != (v in in_tree)]
        if not crossing: break
        w, _, _, u, v = min(crossing)
        new = v if u in in_tree else u
        in_tree.add(new); chosen.append([u, v, w]); total += w
        steps.append({'edge': [u, v, w], 'added_node': new, 'tree_nodes': sorted(in_tree, key=nodes.index),
                      'crossing': [[a, b, c] for c, _, _, a, b in sorted(crossing)], 'total': total})
    return {'algorithm': 'Prim', 'steps': steps, 'edges': chosen, 'total': total, 'spanning': len(chosen) == len(nodes) - 1}


def max_flow(nodes, arcs, source, sink):
    """Augmenting-path algorithm with shortest (BFS) augmenting paths (slides 33-36, 60-61).
    Returns every augmentation (path, forward/reverse use, bottleneck) and the minimum cut R."""
    from collections import deque
    arcs = validate_graph(nodes, arcs)
    if source not in nodes or sink not in nodes or source == sink: raise ValueError('Invalid source/sink')
    if any(w < 0 for _, _, w in arcs): raise ValueError('Capacities must be nonnegative')
    flow = [0] * len(arcs); steps = []

    def residual():
        out = {n: [] for n in nodes}
        for i, (u, v, c) in enumerate(arcs):
            if flow[i] < c: out[u].append((v, i, +1))      # forward arc of G(x)
            if flow[i] > 0: out[v].append((u, i, -1))      # reverse arc of G(x)
        return out

    while True:
        G = residual(); pred = {source: None}; q = deque([source])
        while q and sink not in pred:
            u = q.popleft()
            for v, i, d in G[u]:
                if v not in pred: pred[v] = (u, i, d); q.append(v)
        if sink not in pred:
            R = [n for n in nodes if n in pred]
            cut = [[u, v, c] for u, v, c in arcs if u in pred and v not in pred]
            value = sum(f for f, (u, v, c) in zip(flow, arcs) if v == sink) - sum(f for f, (u, v, c) in zip(flow, arcs) if u == sink)
            return {'algorithm': 'MaxFlow', 'steps': steps, 'value': value, 'cut_R': R, 'cut_arcs': cut,
                    'cut_capacity': sum(c for *_, c in cut), 'flow': {f'{u}>{v}': f for f, (u, v, c) in zip(flow, arcs)}}
        path, v = [], sink
        while pred[v]:
            u, i, d = pred[v]; path.append((u, v, i, d)); v = u
        path.reverse()
        eps = min(arcs[i][2] - flow[i] if d > 0 else flow[i] for _, _, i, d in path)
        for _, _, i, d in path: flow[i] += d * eps
        steps.append({'path': [path[0][0]] + [v for _, v, _, _ in path],
                      'arcs': [{'arc': f'{arcs[i][0]}>{arcs[i][1]}', 'direction': 'forward' if d > 0 else 'reverse'} for _, _, i, d in path],
                      'epsilon': eps, 'flow': {f'{a}>{b}': f for f, (a, b, c) in zip(flow, arcs)},
                      'value': sum(f for f, (a, b, c) in zip(flow, arcs) if b == sink)})


DEMO_FLOW_NODES = ['r', 'a', 'b', 'c', 's']
DEMO_FLOW = [['r', 'a', 4], ['r', 'b', 2], ['a', 'c', 2], ['a', 'b', 2], ['b', 'c', 1], ['b', 's', 2], ['c', 's', 3]]


# ---------------- helpers for the full-course lessons (all tested in tests/test_course.py) ----------------
import math as _math
from itertools import permutations as _perms


def dist(p, q):
    return _math.hypot(p[0] - q[0], p[1] - q[1])


def tour_length(points, tour):
    return sum(dist(points[tour[i]], points[tour[(i + 1) % len(tour)]]) for i in range(len(tour)))


def nearest_neighbor_tour(points, start):
    """Slides 11-14 / 32: go to the nearest unvisited point, then return to the start."""
    tour, left, steps = [start], [k for k in points if k != start], []
    while left:
        cur = tour[-1]
        cand = sorted(left, key=lambda k: (dist(points[cur], points[k]), k))
        steps.append({'from': cur, 'candidates': list(cand), 'chosen': cand[0]})
        tour.append(cand[0]); left.remove(cand[0])
    return {'tour': tour, 'length': tour_length(points, tour), 'steps': steps}


def brute_force_tsp(points, start=None):
    """Slides 8-10: enumerate all (n-1)!/2 tours (fixing the start, skipping mirror images)."""
    keys = list(points); start = start or keys[0]; rest = [k for k in keys if k != start]
    best, count = None, 0
    for perm in _perms(rest):
        if len(perm) > 1 and perm[0] > perm[-1]:
            continue                                   # mirror image of a tour already counted
        count += 1
        t = [start, *perm]; L = tour_length(points, t)
        if best is None or L < best[0] - 1e-12:
            best = (L, t)
    return {'tour': best[1], 'length': best[0], 'tours_checked': count}


def degrees(edges):
    d = {}
    for u, v, *_ in edges:
        d[u] = d.get(u, 0) + 1; d[v] = d.get(v, 0) + 1
    return d


def min_weight_pairing(points, nodes):
    """Exact minimum-length perfect matching of an even set of points (small n, exhaustive)."""
    nodes = list(nodes)
    if not nodes:
        return 0.0, []
    a = nodes[0]; best = None
    for b in nodes[1:]:
        L, m = min_weight_pairing(points, [x for x in nodes if x not in (a, b)])
        L += dist(points[a], points[b])
        if best is None or L < best[0] - 1e-12:
            best = (L, [(a, b)] + m)
    return best


def ford_sequence(nodes, arcs, root, passes):
    """Ford's algorithm scanning arcs in a given order (slides 61-69). `passes` is a list of arc-name
    sequences like ['ad','ba','ra','rb']. Records every correction."""
    cost = {f'{u}{v}': w for u, v, w in arcs}
    y = {n: (0 if n == root else None) for n in nodes}; p = {n: (0 if n == root else -1) for n in nodes}
    steps = []
    for k, S in enumerate(passes, 1):
        for a in S:
            u, v = a[0], a[1]; w = cost[a]
            if y[u] is not None and (y[v] is None or y[u] + w < y[v]):
                old = y[v]; y[v] = y[u] + w; p[v] = u
                steps.append({'pass': k, 'arc': a, 'old': old, 'new': y[v], 'y': dict(y)})
            else:
                steps.append({'pass': k, 'arc': a, 'old': y[v], 'new': None, 'y': dict(y)})
    feasible = all(y[u] is None or (y[v] is not None and y[u] + w >= y[v]) for u, v, w in arcs)
    return {'y': y, 'p': p, 'steps': steps, 'feasible': feasible}


def bfs(nodes, arcs, root):
    """Slides 101-103: breadth-first search; with unit costs the first label is final."""
    from collections import deque
    adj = {n: [] for n in nodes}
    for u, v, *_ in arcs:
        adj[u].append(v)
    p = {n: -1 for n in nodes}; p[root] = 0; dist_ = {root: 0}; q = deque([root]); order = []
    while q:
        v = q.popleft(); order.append(v)
        for w in adj[v]:
            if p[w] == -1:
                p[w] = v; dist_[w] = dist_[v] + 1; q.append(w)
    return {'order': order, 'pred': p, 'dist': dist_}


def check_flow(nodes, arcs, x, r, s):
    """Feasibility of a flow x (dict 'u>v' -> value): capacities and conservation. Returns its value."""
    for u, v, c in arcs:
        if not 0 <= x.get(f'{u}>{v}', 0) <= c:
            raise ValueError(f'capacity violated on {u}>{v}')
    for n in nodes:
        if n in (r, s):
            continue
        inflow = sum(x.get(f'{u}>{v}', 0) for u, v, _ in arcs if v == n)
        out = sum(x.get(f'{u}>{v}', 0) for u, v, _ in arcs if u == n)
        if inflow != out:
            raise ValueError(f'conservation violated at {n}')
    return sum(x.get(f'{u}>{v}', 0) for u, v, _ in arcs if v == s) - sum(x.get(f'{u}>{v}', 0) for u, v, _ in arcs if u == s)


def augment_path(arcs, x, path):
    """Push the bottleneck amount along a given (r,s)-path that may use reverse arcs; returns (new x, eps)."""
    cap = {f'{u}>{v}': c for u, v, c in arcs}; x = dict(x); room = []
    for a, b in zip(path, path[1:]):
        if f'{a}>{b}' in cap and x.get(f'{a}>{b}', 0) < cap[f'{a}>{b}']:
            room.append((f'{a}>{b}', +1, cap[f'{a}>{b}'] - x.get(f'{a}>{b}', 0)))
        elif f'{b}>{a}' in cap and x.get(f'{b}>{a}', 0) > 0:
            room.append((f'{b}>{a}', -1, x[f'{b}>{a}']))
        else:
            raise ValueError(f'{a}-{b} is not incrementing')
    eps = min(r for *_, r in room)
    for k, d, _ in room:
        x[k] = x.get(k, 0) + d * eps
    return x, eps
