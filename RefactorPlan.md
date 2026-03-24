# Kế hoạch Refactor Theo Từng PR Nhỏ

Tài liệu này chia công việc clean code và refactor thành nhiều PR nhỏ, ưu tiên từ rủi ro runtime cao đến cleanup an toàn.
Mục tiêu là giảm nguy cơ bug, giữ nguyên contract giữa backend và frontend ở mức tối đa, và tránh refactor quá rộng trong một lượt.

## Mục tiêu chính

- Ổn định runtime state giữa Flask request thread và background thread.
- Làm cho luồng `Visualize` và `Race` dễ reason hơn ở góc nhìn dev.
- Chuẩn hóa contract giữa thuật toán, runner, API và frontend.
- Thêm baseline test để refactor có lưới an toàn.
- Đồng bộ lại docs với code thực tế đang chạy.
- Giữ solution gọn nhẹ, phù hợp demo trên lớp và có thể deploy đơn giản lên Render.

## Giả định kiến trúc cho phase này

- Phase refactor này giữ mô hình app demo, single-process, in-memory state.
- Không làm multi-user hoặc per-session state trong plan này.
- Tối ưu cho local demo và deploy nhẹ lên Render, không tối ưu cho nhiều người dùng đồng thời.
- Tree view đã bị loại khỏi sản phẩm hiện tại; các phần còn sót phải được dọn ở docs và contract.

## Nguyên tắc chung

- Mỗi PR chỉ giải quyết một nhóm vấn đề rõ ràng.
- Ưu tiên sửa chỗ có rủi ro runtime hoặc lệch contract trước.
- Không đổi API/frontend contract trừ khi PR đó sửa đồng bộ cả hai phía.
- PR nào đụng logic nhạy cảm thì nên có test regression hoặc ít nhất là test client/API tương ứng.
- Nếu đổi behavior chính thức, phải cập nhật docs ngay trong cùng PR.

## Verify tối thiểu sau mỗi PR

- `.\.venv\Scripts\python -m compileall app.py algorithms core`
- Smoke test tay tab `Visualize`
- Smoke test tay tab `Race`
- Nếu PR có thêm test tự động: chạy toàn bộ suite trước khi merge

## PR 0: Chốt baseline test và contract hiện tại

### Mục tiêu

- Có lưới an toàn trước khi chạm sâu vào `core/runner.py`.
- Đóng băng behavior hiện tại nào là intentional, behavior nào là bug.

### Vấn đề chính

- Hiện tại refactor gần như dựa hoàn toàn vào test tay.
- Các flow như `run`, `step`, `step_back`, `race_start`, `switch_tab` rất dễ regression.
- `state` là singleton nên nếu không có helper reset test sẽ khó viết test ổn định.

### Phạm vi file

- thư mục `tests/` mới
- `app.py`
- `core/runner.py`
- `core/state.py`

### Việc nên làm

- Thêm test client cho Flask để cover:
  - `GET /api/state`
  - `GET /api/race`
  - `POST /api/action`
- Thêm helper reset singleton state giữa các test.
- Viết regression test tối thiểu cho:
  - start app state mặc định
  - `run` và `step`
  - `step_back`
  - `set_start` / `set_end` / `grid_cell`
  - `race_toggle` / `race_start`
  - `switch_tab`
- Chốt rõ expected shape cho `/api/state` và `/api/race`.

### Kết quả mong muốn

- Có baseline đủ mạnh để refactor runner mà không “mù”.
- Bug mới xuất hiện sẽ lộ nhanh hơn ngay trong local/dev.

## PR 1: Ổn định runtime state và giảm race condition

### Mục tiêu

- Giảm nguy cơ state bị mutate đồng thời giữa Flask request thread và background thread.
- Làm rõ state nào thuộc `visualize`, state nào thuộc `race`.
- Giảm phụ thuộc vào module-global rải rác trong `core/runner.py`.

### Vấn đề chính

- `core/runner.py` đang giữ nhiều module-global cho race.
- Flask đang chạy `threaded=True` nhưng read/write state không có lock.
- `state` singleton và `_race_*` globals đang sống song song, khó reason.

### Phạm vi file

- `core/runner.py`
- `core/state.py`
- `app.py`

### Việc nên làm

- Thêm lock hoặc cơ chế snapshot nhất quán cho các đoạn read/write state nhạy cảm.
- Gom state race vào một object hoặc namespace rõ ràng thay vì rải nhiều global.
- Chuẩn hóa `get_visual_state()` và `get_race_state()` để luôn đọc snapshot nhất quán.
- Ghi rõ trong code chỗ nào được phép mutate shared state.
- Chốt rõ assumption single-user trong docs/code comments để tránh refactor nửa vời theo hướng multi-user.

### Kết quả mong muốn

- Không còn state “nửa cũ nửa mới” khi frontend poll.
- `core/runner.py` dễ đọc hơn và rủi ro thread bug thấp hơn.

## PR 2: Tách `handle_action()` và siết contract action

### Mục tiêu

- Làm dispatcher action dễ đọc, dễ trace, dễ test hơn.
- Giảm kiểu xử lý silent no-op khó debug.

### Vấn đề chính

- `handle_action()` đang là một chuỗi `if/elif` dài cho cả visualize lẫn race.
- Parse payload và validate input đang phân tán.
- `POST /api/action` hiện gần như luôn trả `{"ok": true}` nên rất khó debug khi action sai hoặc payload thiếu.

### Phạm vi file

- `core/runner.py`
- `app.py`
- `static/js/app.js`
- `static/js/visualize.js`
- `static/js/race.js`

### Việc nên làm

- Tách action handler theo nhóm:
  - visualize actions
  - race actions
  - tab/system actions
- Tạo registry hoặc map `action -> handler` thay cho chuỗi `if/elif` dài.
- Chuẩn hóa validate input và parse payload ở một chỗ.
- Trả về kết quả rõ hơn cho action lỗi hoặc action bị từ chối.
- Chỉ giữ silent no-op ở những chỗ thực sự cố ý.

### Kết quả mong muốn

- Dò flow action nhanh hơn.
- Debug frontend/backend dễ hơn khi payload sai hoặc behavior không như mong đợi.

## PR 3: Sửa contract state và snapshot giữa Visualize và Race

### Mục tiêu

- Làm rõ behavior chính thức khi đổi tab.
- Bỏ các phụ thuộc mơ hồ vào cache frontend.

### Vấn đề chính

- Snapshot khi chuyển tab đang chỉ lưu một phần state.
- Quay từ `Race` về `Visualize` sẽ mất `alg_gen`, `step_history`, `paused`, và ngữ cảnh step mode.
- `Race` đang phụ thuộc vào `state.viz` ở frontend cho `rows`, `cols`, `speed`.

### Phạm vi file

- `core/runner.py`
- `static/js/app.js`
- `static/js/race.js`
- `static/js/visualize.js`

### Việc nên làm

- Quyết định rõ một trong hai hướng:
  - preserve full working session khi đổi tab
  - hoặc reset có chủ đích và UI phản ánh điều đó thật rõ
- Nếu không preserve được generator state, phải định nghĩa behavior chính thức thay vì preserve nửa chừng.
- Làm cho `Race` lấy `rows`, `cols`, `speed` từ backend đáng tin cậy thay vì phụ thuộc cache frontend.
- Bổ sung field snapshot/backend response nếu cần, nhưng phải giữ contract gọn.

### Kết quả mong muốn

- Chuyển tab không còn cảm giác “mất phiên làm việc” một cách khó hiểu.
- Race render đúng grid size/speed hiện tại mà không lệ thuộc state cache cũ.

## PR 4: Chuẩn hóa algorithm contract và checkpoint flow

### Mục tiêu

- Mọi thuật toán trong `algorithms/` đều tuân thủ cùng một contract.
- Giảm special case gây vỡ stats, path hoặc race results.

### Vấn đề chính

- Một số thuật toán có thể khác nhau ở shape `stats` hoặc nhánh thoát sớm.
- Checkpoint wrapper đang phụ thuộc vào assumption ngầm: thuật toán capture `start/end` ở lần `next()` đầu tiên.
- Logic set success/failure state đang lặp lại ở nhiều file thuật toán.

### Phạm vi file

- `algorithms/*.py`
- `algorithms/__init__.py`
- `core/runner.py`
- `core/state.py`

### Việc nên làm

- Viết checklist contract rõ cho mọi thuật toán:
  - luôn set `state.came_from`
  - luôn set `state.finished`
  - luôn set `state.stats` đủ field
  - luôn thống nhất semantics của `time`, `cost`, `iterations`, `peak_memory`
- Sửa các file lệch contract trước.
- Cân nhắc thêm helper chung để finalize success/failure thay vì copy-paste.
- Xem lại checkpoint wrapper để giảm assumption ngầm và tăng độ explicit.
- Xóa placeholder hoặc code không còn dùng trong `algorithms/__init__.py`.

### Kết quả mong muốn

- Mọi thuật toán behave đồng nhất hơn.
- Runner đỡ phải “đoán” hành vi từng thuật toán.

## PR 5: Sửa bug thực tế và cleanup logic chắp vá trong Race

### Mục tiêu

- Dọn các bug thực tế còn sót ở tab `Race`.
- Tách bớt logic lặp và giảm patch logic.

### Vấn đề chính

- `updateRaceAnimations()` đang có call site truyền sai tham số.
- Logic render badge bị lặp.
- `Race` đang có nhiều đoạn sizing/chart hard-code khó chỉnh.
- `race.js` vừa render mini maze vừa render chart nên file khá nặng và khó scan.

### Phạm vi file

- `static/js/race.js`
- `static/css/race.css`

### Việc nên làm

- Sửa call signature của `updateRaceAnimations()`.
- Tách helper cho badge text và badge color.
- Tách helper cho chart sizing hoặc panel sizing nếu cần.
- Rà lại các hard-coded value lớn trong radar chart và layout panel.
- Cân nhắc tách phần render chart ra module/helper riêng nếu file vẫn quá tải.

### Kết quả mong muốn

- Race code ngắn hơn, ít lặp hơn và ít lỗi tham số hơn.

## PR 6: Dọn logic cũ ở Visualize và đồng bộ với behavior hiện tại

### Mục tiêu

- Xóa logic không còn đúng với spec hiện tại.
- Giảm độ phức tạp của `visualize.js`.

### Vấn đề chính

- Code hiện tại vẫn cho zoom/pan ở finished mode, trong khi spec/docs mô tả grid auto-fit.
- `maze_running` đang là field treo.
- Còn dấu vết state/UI của các feature cũ hoặc chưa hoàn tất.
- `visualize.js` đang vừa xử lý interaction vừa animation vừa polling nên khá dày.

### Phạm vi file

- `static/js/visualize.js`
- `static/css/visualize.css`
- `core/runner.py`

### Việc nên làm

- Chốt rõ finished-mode có được zoom/pan hay không.
- Nếu không giữ nữa, xóa toàn bộ state và listener liên quan.
- Xóa hoặc implement đúng `maze_running`.
- Rà lại các branch UI không còn reachable.
- Dọn CSS trùng/ghi đè không cần thiết.

### Kết quả mong muốn

- `Visualize` bám đúng behavior được mô tả chính thức.
- JS/CSS nhẹ hơn và dễ đọc hơn.

## PR 7: Đồng bộ docs và contract với code thực tế

### Mục tiêu

- Chấm dứt tình trạng docs nói một đằng, code chạy một nẻo.
- Giúp dev mới onboarding đúng với code hiện tại ngay từ đầu.

### Vấn đề chính

- Docs hiện vẫn nhắc `core/tree.py`, `/api/tree`, `tree-area`, `btn-tree`, trong khi tree view đã bị bỏ.
- Một số hướng dẫn chạy app/verify chưa khớp hẳn với môi trường PowerShell/Windows hiện tại.
- Chưa có mô tả rõ frontend/backend đang giao tiếp kiểu polling + command API.

### Phạm vi file

- `README.md`
- `Architecture.md`
- `AGENTS.md`
- `CLAUDE.md` nếu repo còn dùng
- các doc phụ khác nếu có

### Việc nên làm

- Xóa hoàn toàn dấu vết tree view khỏi docs và contract chính thức.
- Cập nhật docs về:
  - 3 endpoint thực tế đang dùng
  - polling model của frontend
  - command/query split qua `/api/action`
  - cách chạy app trên Windows PowerShell và trong `.venv`
  - scope single-user/demo/Render của dự án
- Rà lại toàn bộ contract `/api/state` và `/api/race` trong docs.

### Kết quả mong muốn

- Dev đọc docs là hiểu đúng hệ thống hiện tại.
- Giảm hiểu nhầm khi maintain hoặc bàn giao.

## PR 8: Dọn dead code, duplication và magic numbers

### Mục tiêu

- Làm codebase gọn hơn sau khi các bug/contract lớn đã ổn.

### Vấn đề chính

- Có helper và field không dùng tới.
- Có nhiều magic numbers như `2000`, `500`, chart spacing, animation timings.
- Một số constant đang duplicate giữa `visualize.js` và `race.js`.

### Phạm vi file

- `core/runner.py`
- `core/state.py`
- `core/constants.py`
- `algorithms/beam.py`
- `static/js/visualize.js`
- `static/js/race.js`
- `static/css/style.css`
- `static/css/visualize.css`

### Việc nên làm

- Đưa threshold/history cap thành hằng số có tên.
- Gom constant frontend dùng chung nếu hợp lý.
- Xóa field hoặc helper không dùng như:
  - field treo
  - biến cache/placeholder cũ
  - dead branch sau khi chốt behavior
- Dọn formatting và naming để file dễ scan hơn.

### Kết quả mong muốn

- Code gọn, ít nhiễu và dễ onboarding hơn.

## Ngoài scope hiện tại

- Không làm multi-user hoặc per-session state.
- Không khôi phục tree view.
- Không tối ưu production scale; ưu tiên gọn nhẹ, ổn định cho demo lớp và deploy Render đơn giản.

## Thứ tự khuyến nghị

1. PR 0
2. PR 1
3. PR 2
4. PR 3
5. PR 4
6. PR 5
7. PR 6
8. PR 7
9. PR 8

## Nếu muốn chia nhỏ hơn nữa

- PR 0a: thêm helper reset state và test `/api/state`
- PR 0b: test `run`, `step`, `race_start`, `switch_tab`
- PR 1a: thêm lock và snapshot an toàn
- PR 1b: gom state race ra khỏi module-global
- PR 2a: tách visualize actions
- PR 2b: tách race actions
- PR 2c: trả error rõ hơn cho action invalid
- PR 3a: chốt behavior preserve state khi đổi tab
- PR 3b: bỏ phụ thuộc `state.viz` stale trong Race
- PR 4a: chuẩn hóa `state.stats`
- PR 4b: dọn checkpoint wrapper
- PR 5a: fix animation args và helper badge
- PR 6a: chốt giữ hay bỏ zoom/pan finished-mode
- PR 7a: xóa contract/docs cũ liên quan tree view
- PR 8a: thay magic numbers bằng named constants

## Gợi ý commit message cho từng PR

- `test: add regression coverage for runner actions and API snapshots`
- `refactor: stabilize shared runtime state for visualize and race`
- `refactor: split action dispatcher and validate action payloads`
- `refactor: normalize visualize and race state across tab switches`
- `fix: align pathfinding algorithms with the shared generator contract`
- `refactor: clean up race rendering and animation logic`
- `refactor: remove stale visualize interactions and dead UI state`
- `docs: reconcile architecture docs with current runtime behavior`
- `chore: remove dead code and replace magic numbers with named constants`
