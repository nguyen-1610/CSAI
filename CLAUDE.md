# CLAUDE.md

File nay duoc giu dong bo voi `AGENTS.md` de giam lech docs trong qua trinh maintain.

## Muc tieu project

- Visualizer cho cac thuat toan tim duong tren grid maze
- 2 mode chinh:
  - `Visualize`: chay 1 thuat toan, ho tro pause, step, step-back, checkpoint, weighted terrain
  - `Race`: chay nhieu thuat toan song song de so sanh ket qua

Luu y:

- tree view khong con nam trong code hien tai
- grid o tab `Visualize` luon auto-fit
- app la demo single-user voi runtime singleton trong mot process
- frontend hien tai la HTML/CSS/JavaScript thuan, khong phai React/Vite

## Cach chay

Repo uu tien dung `.venv/`. Neu chua co, tao bang:

```bash
python -m venv .venv
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Mo `http://localhost:5000`.

## Verify nhanh

```powershell
python -m compileall app.py algorithms core
python -m unittest discover -s tests -v
```

Neu may co Node.js, co the check syntax frontend:

```powershell
node --check static/js/app.js
node --check static/js/visualize.js
node --check static/js/race.js
```

## Kien truc hien tai

- `app.py`: Flask app mong, render template va expose API routes
- `core/action_handlers.py`: parse/validate action payload va dispatch theo nhom
- `core/runner.py`: orchestration cho visualize/race va background threads
- `core/state.py`: singleton runtime state
- `core/grid.py`: helper grid, terrain cost, build grid array, maze generation
- `static/js/visualize.js`: poll `/api/state`, render grid, handle interaction
- `static/js/race.js`: poll `/api/race`, render mini mazes va charts

## API contract hien tai

Frontend hien dung dung 3 endpoint:

- `GET /api/state`
- `GET /api/race`
- `POST /api/action`

Khong con:

- `/api/tree`
- `toggle_tree`
- `show_tree`
- `has_tree`

## Frontend behavior quan trong

- `visualize.js` poll `/api/state` khoang moi `40ms`
- `race.js` poll `/api/race` khoang moi `40ms`
- tab switch gui command `switch_tab` qua `/api/action`
- grid o `Visualize` luon auto-fit
