"""app.py — Web-based Maze Pathfinding Visualizer."""

import os

try:
    from flask import Flask, render_template, jsonify, request
except ImportError:
    print("Flask is required. Install with:  pip install flask")
    raise SystemExit(1)

from algorithms import ALG_NAMES, ALG_FULL
from core.runner import (
    get_last_algorithm_name,
    get_race_state,
    get_visual_state,
    handle_action,
    is_tree_visible,
)
from core.tree import get_tree_data

DEBUG_MODE = os.environ.get("MAZE_DEBUG", "1") != "0"

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = DEBUG_MODE
if DEBUG_MODE:
    # Disable static-file caching in development so CSS/JS changes show up immediately.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


# ─── Routes ───────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html",
                           algo_names=ALG_NAMES, algo_full=ALG_FULL)


@app.route("/api/state")
def api_state():
    return jsonify(get_visual_state())


@app.route("/api/race")
def api_race():
    return jsonify(get_race_state())


@app.route("/api/tree")
def api_tree():
    if not is_tree_visible():
        return jsonify(None)
    return jsonify(get_tree_data(get_last_algorithm_name()))


@app.route("/api/action", methods=["POST"])
def api_action():
    return jsonify(handle_action(request.json or {}))



# ─── Entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  Maze Pathfinding Visualizer (Web)")
    print("  Open: http://localhost:5000\n")
    print(f"  Auto-reload: {'on' if DEBUG_MODE else 'off'}")
    app.run(
        debug=DEBUG_MODE,
        use_reloader=DEBUG_MODE,
        port=5000,
        threaded=True,
    )
