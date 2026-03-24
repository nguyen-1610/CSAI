"""Registry for search algorithms used by the demo UI."""

from algorithms.astar import algo_astar
from algorithms.beam import algo_beam
from algorithms.bidirectional import algo_bidirectional
from algorithms.bfs import algo_bfs
from algorithms.dfs import algo_dfs
from algorithms.idastar import algo_idastar
from algorithms.iddfs import algo_iddfs
from algorithms.ucs import algo_ucs


REGISTRY = [
    {"name": "Breadth-First Search", "full": "Breadth-First Search", "func": algo_bfs},
    {"name": "Depth-First Search", "full": "Depth-First Search", "func": algo_dfs},
    {"name": "Uniform Cost Search", "full": "Uniform Cost Search", "func": algo_ucs},
    {"name": "A* Search", "full": "A* (Manhattan heuristic)", "func": algo_astar},
    {"name": "Iterative Deepening DFS", "full": "Iterative Deepening DFS", "func": algo_iddfs},
    {"name": "Bidirectional BFS", "full": "Bidirectional BFS", "func": algo_bidirectional},
    {"name": "Beam Search", "full": "Beam Search (width=8)", "func": algo_beam},
    {"name": "IDA* Search", "full": "Iterative Deepening A*", "func": algo_idastar},
]

ALGO_FUNCS = [entry["func"] for entry in REGISTRY]
ALG_NAMES = [entry["name"] for entry in REGISTRY]
ALG_FULL = [entry["full"] for entry in REGISTRY]
