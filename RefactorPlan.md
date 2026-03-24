# Refactor Plan

Tai lieu nay la plan tham khao cho cac dot cleanup tiep theo. No khong dinh nghia stack moi; stack hien tai van la Flask + HTML/CSS/JavaScript thuan.

## Baseline hien tai

- Backend: Flask
- Frontend: HTML/CSS/JavaScript thuan
- Render: Canvas API thuan
- Data flow: polling `GET /api/state`, `GET /api/race`, va command `POST /api/action`
- Scope: demo single-user, in-memory runtime

## Uu tien tiep theo

### 1. Browser regression pass cho UI

- test zoom 90%, 100%, 110%, 125%
- test full HD va laptop viewport hep hon
- test chart overlap, label collision, va canvas resize
- test `Visualize` va `Race` sau hard refresh

### 2. Checkpoint regression tests

- them test cho `Visualize` voi checkpoint
- them test cho `Race` voi checkpoint
- dam bao end marker, partial path, va final path animate dung 2 phase

### 3. Tach bot `race.js`

- tach helper chart render neu file tiep tuc phinh to
- giu layout logic va animation logic de scan hon
- tranh lap magic numbers cho legend, panel sizing, va chart spacing

### 4. Tiep tuc dong bo docs

- giu `README.md`, `Architecture.md`, `AGENTS.md`, `CLAUDE.md` thang hang voi code
- neu thay doi API contract hoac run flow, cap nhat docs trong cung mot dot sua

### 5. Dev environment

- tiep tuc uu tien `.venv/`
- neu repo clone moi chua co `.venv`, tao bang `python -m venv .venv`
- frontend khong can npm/build step tru khi co quyet dinh doi stack trong tuong lai

## Ngoai scope hien tai

- khong chuyen sang React/Vite/Tailwind trong branch nay
- khong chuyen sang FastAPI hay websocket trong branch nay
- khong lam multi-user session state
- khong khoi phuc tree view
