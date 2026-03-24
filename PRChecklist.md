# PR Checklist

File nay la checklist thuc thi de team follow song song voi `RefactorPlan.md`.
Muc tieu la giup moi PR co scope ro, de check tien do, va khong quen buoc verify truoc khi merge.

## Context Da Chot

- Day la app demo tren lop.
- Uu tien code gon, de demo, de sua.
- Co the deploy nhe len Render.
- Khong lam multi-user hoac per-session state.
- Tree view da bo han, khong khoi phuc lai trong roadmap hien tai.

## Cach Dung

- Moi PR co the dien them `Owner`, `Branch`, `Status`, `Notes`.
- Chi tick khi item da xong that su.
- Neu PR doi behavior chinh thuc, phai cap nhat docs trong cung PR.

## PR 0: Baseline Test Va Contract Hien Tai

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Added stdlib unittest baseline for current API and runner flows.

- [X] Tao thu muc `tests/`
- [X] Them helper reset singleton state giua cac test
- [X] Them test cho `GET /api/state`
- [X] Them test cho `GET /api/race`
- [X] Them test cho `POST /api/action`
- [X] Them regression test cho `run`
- [X] Them regression test cho `step`
- [X] Them regression test cho `step_back`
- [X] Them regression test cho `set_start` / `set_end` / `grid_cell`
- [X] Them regression test cho `race_toggle` / `race_start`
- [X] Them regression test cho `switch_tab`
- [X] Chot expected shape cua `/api/state`
- [X] Chot expected shape cua `/api/race`
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chay toan bo test moi
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 1: On Dinh Runtime State Va Giam Race Condition

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Moved race runtime into `state.race`, added `RLock`, and wrapped key snapshots/mutations.

- [X] Ra lai toan bo diem mutate shared state trong `core/runner.py`
- [X] Them lock hoac co che snapshot nhat quan cho cac doan nhay cam
- [X] Gom state `race` ve object/namespace ro rang hon
- [X] Chuan hoa `get_visual_state()`
- [X] Chuan hoa `get_race_state()`
- [X] Giam read/write rai rac kho trace
- [X] Ghi chu ro assumption single-user trong code/docs neu can
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chay test lien quan state/runner
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 2: Tach `handle_action()` Va Siet Contract Action

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Added `core/action_handlers.py`, centralized validation, and clearer `/api/action` error responses.

- [X] Tach handler theo nhom `visualize`
- [X] Tach handler theo nhom `race`
- [X] Tach handler theo nhom `tab/system`
- [X] Giam chuoi `if/elif` dai trong `handle_action()`
- [X] Chuan hoa validate payload o mot cho
- [X] Chuan hoa parse kieu du lieu o mot cho
- [X] Tra response ro hon cho action invalid hoac payload loi
- [X] Giu silent no-op chi o cho that su chu y
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chay test API/action
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 3: Chuan Hoa State Giua Visualize Va Race

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Race now reads grid shape and speed from `/api/race`, and unfinished Visualize sessions are intentionally discarded on tab switch.

- [X] Chot behavior chinh thuc khi doi tab
- [X] Bo phu thuoc mo ho vao cache `state.viz` o frontend
- [X] Lam ro strategy preserve hoac reset session khi doi tab
- [X] Neu khong preserve duoc generator state thi phan anh behavior cho dung
- [X] Dam bao `Race` lay `rows`, `cols`, `speed` tu nguon dang tin cay
- [X] Dam bao quay lai `Visualize` khong gay hieu nham ve step/pause state
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chay test `switch_tab` va state snapshot
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 4: Chuan Hoa Algorithm Contract Va Checkpoint Flow

Owner:
Branch:
Status:
Notes:

- [ ] Liet ke contract chung cho moi thuat toan
- [ ] Chuan hoa `state.stats` du field cho tat ca thuat toan
- [ ] Chuan hoa `state.came_from`
- [ ] Chuan hoa `state.finished`
- [ ] Ra nhanh thoat som cua cac thuat toan
- [ ] Don assumption ngam trong checkpoint wrapper
- [ ] Can nhac helper finalize success/failure dung chung
- [ ] Xoa placeholder hoac code thua trong `algorithms/__init__.py`
- [ ] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [ ] Chay test thuat toan/race/checkpoint
- [ ] Smoke test tay `Visualize`
- [ ] Smoke test tay `Race`

## PR 5: Cleanup Race Rendering Va Logic Chap Va

Owner:
Branch:
Status:
Notes:

- [ ] Sua call signature cua `updateRaceAnimations()`
- [ ] Tach helper badge text
- [ ] Tach helper badge color
- [ ] Ra helper sizing cho panel/chart neu can
- [ ] Giam duplication trong `race.js`
- [ ] Ra lai hard-coded value lon trong chart/radar/panel
- [ ] Giu nguyen hanh vi UI hien tai sau refactor
- [ ] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [ ] Neu can, chay `node --check static/js/race.js`
- [ ] Smoke test tay `Race`

## PR 6: Don Logic Cu O Visualize

Owner:
Branch:
Status:
Notes:

- [ ] Chot ro finished-mode co zoom/pan hay khong
- [ ] Neu bo zoom/pan thi xoa toan bo state/listener lien quan
- [ ] Xoa hoac implement dung `maze_running`
- [ ] Xoa branch UI khong con reachable
- [ ] Don phan interaction/animation/polling bi chong cheo neu co the
- [ ] Don CSS thua hoac ghi de khong can thiet
- [ ] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [ ] Neu can, chay `node --check static/js/visualize.js`
- [ ] Smoke test tay `Visualize`

## PR 7: Dong Bo Docs Va Xoa Dau Vet Tree View

Owner:
Branch:
Status:
Notes:

- [ ] Xoa moi mo ta cu ve tree view trong docs chinh
- [ ] Xoa moi mo ta cu ve `/api/tree`
- [ ] Xoa moi mo ta cu ve `btn-tree`, `tree-area`, `show_tree`
- [ ] Cap nhat docs theo 3 endpoint thuc te dang dung
- [ ] Cap nhat docs theo polling model hien tai
- [ ] Cap nhat docs theo command/query split qua `/api/action`
- [ ] Cap nhat huong dan chay bang `.venv` tren PowerShell/Windows
- [ ] Ghi ro day la app demo single-user, deploy nhe len Render neu can
- [ ] Ra lai `README.md`
- [ ] Ra lai `Architecture.md`
- [ ] Ra lai `AGENTS.md`
- [ ] Ra lai doc phu khac neu repo con dung

## PR 8: Don Dead Code, Duplication Va Magic Numbers

Owner:
Branch:
Status:
Notes:

- [ ] Dua `2000`, `500` va cac threshold tuong tu thanh named constants
- [ ] Gom constant frontend dung chung neu hop ly
- [ ] Xoa field treo khong con dung
- [ ] Xoa helper thua khong con dung
- [ ] Xoa dead branch sau khi behavior da chot
- [ ] Don naming de file scan de hon
- [ ] Don formatting cho cac file dai
- [ ] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [ ] Neu can, chay `node --check static/js/app.js`
- [ ] Neu can, chay `node --check static/js/visualize.js`
- [ ] Neu can, chay `node --check static/js/race.js`
- [ ] Smoke test tay `Visualize`
- [ ] Smoke test tay `Race`
