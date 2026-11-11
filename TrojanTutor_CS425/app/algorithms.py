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
