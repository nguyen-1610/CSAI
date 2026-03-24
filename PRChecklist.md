# PR Checklist

File này là checklist thực thi để team follow song song với `RefactorPlan.md`.
Mục tiêu là giúp mỗi PR có scope rõ, dễ check tiến độ, và không quên bước verify trước khi merge.

## Context Đã Chốt

- Đây là app demo trên lớp.
- Ưu tiên code gọn, dễ demo, dễ sửa.
- Có thể deploy nhẹ lên Render.
- Không làm multi-user hoặc per-session state.
- Tree view đã bỏ hẳn, không khôi phục lại trong roadmap hiện tại.

## Cách Dùng

- Mỗi PR có thể điền thêm `Owner`, `Branch`, `Status`, `Notes`.
- Chỉ tick khi item đã xong thật sự.
- Nếu PR đổi behavior chính thức, phải cập nhật docs trong cùng PR.

## PR 0: Baseline Test Và Contract Hiện Tại

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Added stdlib unittest baseline for current API and runner flows.

- [X] Tạo thư mục `tests/`
- [X] Thêm helper reset singleton state giữa các test
- [X] Thêm test cho `GET /api/state`
- [X] Thêm test cho `GET /api/race`
- [X] Thêm test cho `POST /api/action`
- [X] Thêm regression test cho `run`
- [X] Thêm regression test cho `step`
- [X] Thêm regression test cho `step_back`
- [X] Thêm regression test cho `set_start` / `set_end` / `grid_cell`
- [X] Thêm regression test cho `race_toggle` / `race_start`
- [X] Thêm regression test cho `switch_tab`
- [X] Chốt expected shape của `/api/state`
- [X] Chốt expected shape của `/api/race`
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chạy toàn bộ test mới
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 1: Ổn Định Runtime State Và Giảm Race Condition

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Moved race runtime into `state.race`, added `RLock`, and wrapped key snapshots/mutations.

- [X] Rà lại toàn bộ điểm mutate shared state trong `core/runner.py`
- [X] Thêm lock hoặc cơ chế snapshot nhất quán cho các đoạn nhạy cảm
- [X] Gom state `race` về object/namespace rõ ràng hơn
- [X] Chuẩn hóa `get_visual_state()`
- [X] Chuẩn hóa `get_race_state()`
- [X] Giảm read/write rải rác khó trace
- [X] Ghi chú rõ assumption single-user trong code/docs nếu cần
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chạy test liên quan state/runner
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 2: Tách `handle_action()` Và Siết Contract Action

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Added `core/action_handlers.py`, centralized validation, and clearer `/api/action` error responses.

- [X] Tách handler theo nhóm `visualize`
- [X] Tách handler theo nhóm `race`
- [X] Tách handler theo nhóm `tab/system`
- [X] Giảm chuỗi `if/elif` dài trong `handle_action()`
- [X] Chuẩn hóa validate payload ở một chỗ
- [X] Chuẩn hóa parse kiểu dữ liệu ở một chỗ
- [X] Trả response rõ hơn cho action invalid hoặc payload lỗi
- [X] Giữ silent no-op chỉ ở chỗ thật sự chủ ý
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chạy test API/action
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 3: Chuẩn Hóa State Giữa Visualize Và Race

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Race now reads grid shape and speed from `/api/race`, and unfinished Visualize sessions are intentionally discarded on tab switch.

- [X] Chốt behavior chính thức khi đổi tab
- [X] Bỏ phụ thuộc mơ hồ vào cache `state.viz` ở frontend
- [X] Làm rõ strategy preserve hoặc reset session khi đổi tab
- [X] Nếu không preserve được generator state thì phản ánh behavior cho đúng
- [X] Đảm bảo `Race` lấy `rows`, `cols`, `speed` từ nguồn đáng tin cậy
- [X] Đảm bảo quay lại `Visualize` không gây hiểu nhầm về step/pause state
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chạy test `switch_tab` và state snapshot
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`

## PR 4: Chuẩn Hóa Algorithm Contract Và Checkpoint Flow

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Added shared finalize helpers, normalized algorithm stats/came_from/finished, and hardened checkpoint wrappers.

- [X] Liệt kê contract chung cho mỗi thuật toán
- [X] Chuẩn hóa `state.stats` đủ field cho tất cả thuật toán
- [X] Chuẩn hóa `state.came_from`
- [X] Chuẩn hóa `state.finished`
- [X] Rà nhanh thoát sớm của các thuật toán
- [X] Dọn assumption ngầm trong checkpoint wrapper
- [X] Cân nhắc helper finalize success/failure dùng chung
- [X] Xóa placeholder hoặc code thừa trong `algorithms/__init__.py`
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Chạy test thuật toán/race/checkpoint
- [ ] Smoke test tay `Visualize`
- [ ] Smoke test tay `Race`

## PR 5: Cleanup Race Rendering Và Logic Chắp Vá

Owner:
Branch:
Status: Done
Notes: Reduced `race.js` duplication with shared sizing/badge helpers and preserved the tighter Race layout. Manual Race smoke test passed.

- [X] Sửa call signature của `updateRaceAnimations()`
- [X] Tách helper badge text
- [X] Tách helper badge color
- [X] Rà helper sizing cho panel/chart nếu cần
- [X] Giảm duplication trong `race.js`
- [X] Rà lại hard-coded value lớn trong chart/radar/panel
- [X] Giữ nguyên hành vi UI hiện tại sau refactor
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Nếu cần, chạy `node --check static/js/race.js`
- [X] Smoke test tay `Race`

## PR 6: Dọn Logic Cũ Ở Visualize

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Removed finished-mode zoom/pan, dropped dead `maze_running` state, and cleaned duplicated Visualize CSS without changing the current layout structure.

- [X] Chốt rõ finished-mode có zoom/pan hay không
- [X] Nếu bỏ zoom/pan thì xóa toàn bộ state/listener liên quan
- [X] Xóa hoặc implement đúng `maze_running`
- [X] Xóa branch UI không còn reachable
- [X] Dọn phần interaction/animation/polling bị chồng chéo nếu có thể
- [X] Dọn CSS thừa hoặc ghi đè không cần thiết
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Nếu cần, chạy `node --check static/js/visualize.js`
- [X] Smoke test tay `Visualize`

## PR 7: Đồng Bộ Docs Và Xóa Dấu Vết Tree View

Owner:
Branch:
Status: Done
Notes: Rewrote core docs to match the current codebase, removed old tree-view descriptions, and documented the actual 3-endpoint polling model with `.venv` run instructions for macOS/Linux and PowerShell.

- [X] Xóa mọi mô tả cũ về tree view trong docs chính
- [X] Xóa mọi mô tả cũ về `/api/tree`
- [X] Xóa mọi mô tả cũ về `btn-tree`, `tree-area`, `show_tree`
- [X] Cập nhật docs theo 3 endpoint thực tế đang dùng
- [X] Cập nhật docs theo polling model hiện tại
- [X] Cập nhật docs theo command/query split qua `/api/action`
- [X] Cập nhật hướng dẫn chạy bằng `.venv` trên PowerShell/Windows
- [X] Ghi rõ đây là app demo single-user, deploy nhẹ lên Render nếu cần
- [X] Rà lại `README.md`
- [X] Rà lại `Architecture.md`
- [X] Rà lại `AGENTS.md và CLAUDE.md`
- [X] Rà lại doc phụ khác nếu repo còn dùng

## PR 8: Dọn Dead Code, Duplication Và Magic Numbers

Owner:
Branch:
Status: Implemented, manual smoke pending
Notes: Centralized backend/frontend timing constants, removed dead data like `ALG_FULL`, `treeData`, and `run_history`, and cleaned a few remaining magic numbers without changing behavior.

- [X] Đưa `2000`, `500` và các threshold tương tự thành named constants
- [X] Gom constant frontend dùng chung nếu hợp lý
- [X] Xóa field treo không còn dùng
- [X] Xóa helper thừa không còn dùng
- [X] Xóa dead branch sau khi behavior đã chốt
- [X] Dọn naming để file scan dễ hơn
- [X] Dọn formatting cho các file dài
- [X] Verify compile: `.\.venv\Scripts\python -m compileall app.py algorithms core`
- [X] Nếu cần, chạy `node --check static/js/app.js`
- [X] Nếu cần, chạy `node --check static/js/visualize.js`
- [X] Nếu cần, chạy `node --check static/js/race.js`
- [X] Smoke test tay `Visualize`
- [X] Smoke test tay `Race`
