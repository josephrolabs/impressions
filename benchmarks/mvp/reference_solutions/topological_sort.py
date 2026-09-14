import heapq
def solve(nodes, edges):
    graph={node:[] for node in nodes}; degree={node:0 for node in nodes}
    for left,right in edges: graph[left].append(right); degree[right]+=1
    ready=[node for node in nodes if degree[node]==0]; heapq.heapify(ready); result=[]
    while ready:
        node=heapq.heappop(ready); result.append(node)
        for child in graph[node]:
            degree[child]-=1
            if degree[child]==0: heapq.heappush(ready,child)
    if len(result)!=len(nodes): raise ValueError("cycle")
    return result
