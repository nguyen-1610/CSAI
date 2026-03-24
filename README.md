# Maze Pathfinding Visualizer

Web app de visualize va so sanh cac thuat toan tim duong tren grid maze.

## Stack hien tai

- Backend: Python + Flask
- Frontend: HTML + CSS + JavaScript thuan
- Render: Canvas API thuan
- Giao tiep frontend/backend: polling `GET /api/state`, `GET /api/race`, va command `POST /api/action`
- Khong dung React, Vite, Tailwind, shadcn/ui, Zustand, Recharts, FastAPI, hay websocket

Project nay la app demo single-user:

- uu tien code gon, de doc, de demo
- runtime state duoc giu trong mot process
- phu hop local demo va deploy nhe

## Tinh nang

### Tab `Visualize`

- chay 1 thuat toan
- `Run`, `Pause`, `Continue`
- `Step`, `Step Back`
- keo tha start, end, checkpoint
- `Basic Maze`, `Weighted Maze`
- weighted terrain voi grass, swamp, water
- grid auto-fit, khong co zoom/pan bang chuot

### Tab `Race`

- chon nhieu thuat toan de chay song song
- mini maze cho tung runner
- bang so sanh ket qua
- cac chart so sanh nodes, path, cost, time, iterations, memory

## Cai dat va chay

Repo uu tien dung virtual environment tai `.venv/`. Thu muc nay la local dev env, khong duoc commit.

Neu may ban chua co `.venv`, tao no truoc:

```bash
python -m venv .venv
```

### macOS / Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Neu khong muon activate shell, goi truc tiep interpreter trong `.venv`:

```powershell
.venv\Scripts\python app.py
```

Mo `http://localhost:5000`.

### Tat auto-reload

```powershell
$env:MAZE_DEBUG = "0"
.venv\Scripts\python app.py
```

Hoac neu dang activate shell:

```powershell
$env:MAZE_DEBUG = "0"
python app.py
```

## Verify nhanh

### Python

```bash
python -m compileall app.py algorithms core
python -m unittest discover -s tests -v
```

### JavaScript

Frontend khong can build step. Neu may co Node.js, co the check syntax:

```bash
node --check static/js/app.js
node --check static/js/visualize.js
node --check static/js/race.js
```

### Smoke test tay

- `Visualize`
- chon thuat toan va bam `Run`
- `Pause` / `Continue`
- `Step` / `Step Back`
- keo tha start, end, checkpoint
- tao `Basic Maze` va `Weighted Maze`
- `Race`
- chon it nhat 2 thuat toan
- bam `Race`
- xem runner panels, result matrix, va charts

## API hien tai

Frontend hien dung dung 3 endpoint:

- `GET /api/state`
- `GET /api/race`
- `POST /api/action`

## Tai lieu lien quan

- [Architecture.md](./Architecture.md)
- [AGENTS.md](./AGENTS.md)
- [CLAUDE.md](./CLAUDE.md)
- [PRChecklist.md](./PRChecklist.md)
- [RefactorPlan.md](./RefactorPlan.md)
