# Kế Hoạch Refactor Theo Từng PR Nhỏ

Tài liệu này chia công việc clean code và refactor thành nhiều PR nhỏ, ưu tiên từ rủi ro cao đến cleanup an toàn.
Mục tiêu là giảm nguy cơ bug, giữ nguyên contract giữa backend và frontend, và tránh refactor quá rộng trong một lượt.

## Nguyên tắc chung

- Mỗi PR chỉ giải quyết một nhóm vấn đề rõ ràng.
- Ưu tiên sửa chỗ có rủi ro runtime hoặc lệch contract trước.
- Không đổi API/frontend contract trừ khi PR đó sửa đồng bộ cả hai phía.
- Sau mỗi PR nên chạy:
  - `source .venv/bin/activate && python -m compileall app.py algorithms core`
  - test tay `Visualize`
  - test tay `Race`

## PR 1: Ổn định runtime state và giảm race condition

### Mục tiêu

- Giảm nguy cơ state bị mutate đồng thời giữa Flask request thread và background thread.
- Làm rõ state nào thuộc `visualize`, state nào thuộc `race`.
- Giảm phụ thuộc vào module-global trong `core/runner.py`.

### Vấn đề chính

- `core/runner.py` đang giữ nhiều module-global cho race.
- Flask đang chạy `threaded=True` nhưng read/write state không có lock.
- `state` singleton và `_race_*` globals đang sống song song, khó reason.

### Phạm vi file

- `core/runner.py`
- `core/state.py`
- `app.py`

### Việc nên làm

- Thêm lock chung cho các đoạn read/write state nhạy cảm.
- Gom state race vào một object hoặc một namespace rõ ràng thay vì rải nhiều global.
- Chuẩn hóa hàm đọc snapshot như `get_visual_state()` và `get_race_state()` để lấy snapshot nhất quán.
- Giảm thao tác mutate trực tiếp từ nhiều nơi nếu có thể.

### Kết quả mong muốn

- Không còn state “nửa cũ nửa mới” khi frontend poll.
- `core/runner.py` dễ đọc hơn, ít global hơn.

## PR 2: Sửa contract state và snapshot giữa Visualize và Race

### Mục tiêu

- Làm cho việc đổi tab không làm mất trạng thái đang step/pause.
- Giữ contract state rõ ràng và nhất quán.

### Vấn đề chính

- Snapshot khi chuyển tab đang chỉ lưu một phần state.
- Quay từ `Race` về `Visualize` sẽ mất `alg_gen`, `step_history`, `step_ptr`.
- `Race` đang phụ thuộc vào `state.viz` có thể stale.

### Phạm vi file

- `core/runner.py`
- `static/js/app.js`
- `static/js/race.js`
- `static/js/visualize.js`

### Việc nên làm

- Quyết định rõ:
  - hoặc `Visualize` phải preserve full state khi sang `Race`
  - hoặc chủ động reset nhưng UI phải phản ánh rõ
- Nếu preserve:
  - snapshot đủ `step_history`, `step_ptr`, `paused`, generator state chiến lược
- Nếu không preserve generator được:
  - cần define lại behavior chính thức và làm UI nhất quán
- `Race` nên refresh `rows`, `cols`, `speed` từ backend đáng tin cậy thay vì cache mơ hồ.

### Kết quả mong muốn

- Chuyển tab không còn cảm giác “mất phiên làm việc”.
- `Race` render đúng grid size/speed hiện tại.

## PR 3: Chuẩn hóa algorithm contract

### Mục tiêu

- Mọi thuật toán trong `algorithms/` đều tuân thủ cùng một contract.
- Giảm special case gây vỡ tree view, stats, hoặc race results.

### Vấn đề chính

- `algo_iddfs()` có nhánh thoát sớm chưa set đầy đủ `came_from` và stats.
- Một số thuật toán có thể khác nhau ở shape `stats`.
- Checkpoint wrapper đang giả định thuật toán capture `start/end` ở lần `next()` đầu tiên.

### Phạm vi file

- `algorithms/*.py`
- `algorithms/__init__.py`
- `core/runner.py`
- `core/state.py`

### Việc nên làm

- Viết checklist contract cho mọi thuật toán:
  - luôn set `state.came_from`
  - luôn set `state.finished`
  - luôn trả `stats` đủ field
- Sửa `iddfs.py` trước.
- Xem lại wrapper checkpoint để giảm phụ thuộc vào assumption ngầm.
- Xóa code placeholder không dùng trong `algorithms/__init__.py`.

### Kết quả mong muốn

- Mọi thuật toán behave đồng nhất hơn.
- Backend đỡ phải “đoán” từng thuật toán.

## PR 4: Sửa các bug nhỏ và logic chắp vá trong Race

### Mục tiêu

- Dọn các bug thực tế còn sót ở tab `Race`.
- Tách bớt đoạn lặp và giảm patch logic.

### Vấn đề chính

- `updateRaceAnimations()` đang có call site truyền sai tham số.
- Logic render badge bị lặp.
- Một số phần radar/panel/chart đang được vá trực tiếp nhiều chỗ.

### Phạm vi file

- `static/js/race.js`
- `static/css/race.css`

### Việc nên làm

- Sửa call signature của `updateRaceAnimations()`.
- Tách helper cho badge text và badge color.
- Tách helper cho chart sizing nếu cần.
- Rà lại các hard-coded value lớn trong radar chart và panel sizing.

### Kết quả mong muốn

- Race code ngắn hơn, ít lặp, ít tham số truyền sai.

## PR 5: Dọn logic cũ ở Visualize và đồng bộ với behavior hiện tại

### Mục tiêu

- Xóa logic không còn đúng với spec hiện tại.
- Giảm độ phức tạp của `visualize.js`.

### Vấn đề chính

- Vẫn còn zoom/pan bằng chuột dù spec nói grid auto-fit.
- `maze_running` đang là field treo.
- Có dấu hiệu CSS/JS dư sau các lần đổi layout.

### Phạm vi file

- `static/js/visualize.js`
- `static/css/visualize.css`
- `core/runner.py`

### Việc nên làm

- Xóa toàn bộ state và listener zoom/pan nếu thật sự không còn dùng.
- Xóa hoặc implement đúng `maze_running`.
- Rà lại các branch UI không còn reachable.
- Dọn CSS trùng/ghi đè không cần thiết.

### Kết quả mong muốn

- `Visualize` bám đúng behavior được mô tả.
- JS/CSS nhẹ và dễ đọc hơn.

## PR 6: Quyết định rõ số phận của tree view

### Mục tiêu

- Chốt một trong hai hướng:
  - khôi phục tree view đúng contract
  - hoặc chính thức loại bỏ tree view và cập nhật docs/contracts

### Vấn đề chính

- Docs hiện nhắc `core/tree.py`, `/api/tree`, `btn-tree`, `tree-area`.
- Code hiện tại không còn đầy đủ các phần đó.

### Phạm vi file

- `templates/index.html`
- `static/js/app.js`
- `static/js/visualize.js`
- `static/css/visualize.css`
- `app.py`
- `Architecture.md`
- `README.md`
- `AGENTS.md` nếu cần cập nhật nội dung lệch spec

### Việc nên làm

- Nếu giữ tree:
  - khôi phục đầy đủ DOM, API, render logic, state flow
- Nếu bỏ tree:
  - xóa code/CSS/state liên quan
  - cập nhật tài liệu và contract cho khớp code

### Kết quả mong muốn

- Không còn tình trạng docs nói một đằng, code chạy một nẻo.

## PR 7: Dọn dead code, duplication và magic numbers

### Mục tiêu

- Làm codebase gọn hơn sau khi các bug/contract lớn đã ổn.

### Vấn đề chính

- Có helper và state không dùng tới.
- Có nhiều magic numbers như `2000/500`, beam width, chart spacing.
- Có đoạn CSS/JS lặp nhưng chưa nguy hiểm.

### Phạm vi file

- `core/runner.py`
- `core/state.py`
- `core/constants.py`
- `algorithms/beam.py`
- `static/js/race.js`
- `static/css/visualize.css`
- `static/css/style.css`

### Việc nên làm

- Đưa threshold/history cap thành hằng số có tên.
- Xóa field hoặc helper không dùng.
- Tách helper chung cho logic lặp.
- Dọn formatting và naming để file dễ đọc hơn.

### Kết quả mong muốn

- Code gọn, ít nhiễu, dễ onboarding hơn.

## Thứ tự khuyến nghị

1. PR 1
2. PR 2
3. PR 3
4. PR 4
5. PR 5
6. PR 6
7. PR 7

## Nếu muốn chia nhỏ hơn nữa

- PR 1a: thêm lock và snapshot an toàn
- PR 1b: gom state race ra khỏi module-global
- PR 2a: fix stale `state.viz` trong Race
- PR 2b: chốt behavior preserve state khi đổi tab
- PR 3a: sửa `iddfs.py`
- PR 3b: chuẩn hóa `state.stats`
- PR 4a: fix animation args và helper badge
- PR 5a: remove zoom/pan cũ
- PR 6a: quyết định giữ hay bỏ tree view

## Gợi ý commit message cho từng PR

- `refactor: stabilize shared runtime state for visualize and race`
- `refactor: preserve and normalize state across tab switches`
- `fix: align pathfinding algorithms with shared generator contract`
- `refactor: clean up race rendering and animation logic`
- `refactor: remove stale visualize interactions and dead UI state`
- `docs: reconcile tree view contract with current implementation`
- `chore: remove dead code and replace magic numbers with named constants`
