"""
Plugin Registry cho các thuật toán tìm kiếm.
Khi các thành viên trong team code xong thuật toán của mình trong thư mục này,
chỉ cần vào đây import và thêm vào list REGISTRY.
"""

# 1. IMPORT CÁC THUẬT TOÁN Ở ĐÂY
# (Mở comment khi các file .py tương ứng đã được tạo)

# from algorithms.bfs import algo_bfs
from algorithms.dfs import algo_dfs
# from algorithms.ucs import algo_ucs
from algorithms.astar import algo_astar
from algorithms.iddfs import algo_iddfs
# from algorithms.bidirectional import algo_bidirectional
# from algorithms.beam import algo_beam
from algorithms.idastar import algo_idastar


# 2. ĐĂNG KÝ THUẬT TOÁN VÀO DANH SÁCH NÀY
# Hệ thống GUI sẽ tự động đọc danh sách này để tạo các nút bấm trên màn hình.

REGISTRY = [
    # {"name": "BFS",   "full": "Breadth-First Search",        "func": algo_bfs},
    {"name": "DFS",   "full": "Depth-First Search",          "func": algo_dfs},
    # {"name": "UCS",   "full": "Uniform Cost Search",         "func": algo_ucs},
    {"name": "A*",    "full": "A* (Manhattan heuristic)",    "func": algo_astar},
    {"name": "IDDFS", "full": "Iterative Deepening DFS",     "func": algo_iddfs},
    # {"name": "Bidir.", "full": "Bidirectional BFS",          "func": algo_bidirectional},
    # {"name": "Beam",  "full": "Beam Search  (width=8)",      "func": algo_beam},
    {"name": "IDA*",  "full": "Iterative Deepening A*",      "func": algo_idastar},
]


# ---------------------------------------------------------
# KHÔNG CẦN SỬA PHẦN DƯỚI NÀY
# (Tự động trích xuất dữ liệu cho GUI sử dụng)
# ---------------------------------------------------------
ALGO_FUNCS = [e["func"] for e in REGISTRY]
ALG_NAMES  = [e["name"] for e in REGISTRY]
ALG_FULL   = [e["full"] for e in REGISTRY]
