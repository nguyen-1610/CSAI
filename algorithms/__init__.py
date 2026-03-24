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
    {"name": "Breadth-First Search", "func": algo_bfs},
    {"name": "Depth-First Search", "func": algo_dfs},
    {"name": "Uniform Cost Search", "func": algo_ucs},
    {"name": "A* Search", "func": algo_astar},
    {"name": "Iterative Deepening DFS", "func": algo_iddfs},
    {"name": "Bidirectional BFS", "func": algo_bidirectional},
    {"name": "Beam Search", "func": algo_beam},
    {"name": "IDA* Search", "func": algo_idastar},
]

ALGO_FUNCS = [entry["func"] for entry in REGISTRY]
ALG_NAMES = [entry["name"] for entry in REGISTRY]
