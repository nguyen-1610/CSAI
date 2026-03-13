# AI & Developer Instructions cho Maze Pathfinding Visualizer

Chào AI Assistant (Claude/Cursor/Copilot) và các thành viên trong team. Đây là tài liệu hướng dẫn cực kỳ quan trọng về quy ước code của dự án này. **HÃY ĐỌC KỸ TRƯỚC KHI VIẾT BẤT KỲ DÒNG CODE NÀO!**

## 🏗 Kiến trúc dự án (Plugin Architecture)

Dự án này đã được tách file (Modular) để tránh conflict khi làm việc nhóm. Mọi thành phần đều xoay quanh `config.py`.

- `config.py`: Lưu trữ hằng số cấu hình (W, H, Màu sắc) và Lớp `State` (Singleton) lưu trạng thái toàn cầu của ứng dụng.
- `grid.py`: Chứa các hàm toán học hỗ trợ (tìm hàng xóm, tính khoảng cách, dò đường) và hàm tạo mê cung.
- `gui.py`: Chứa toàn bộ logic render UI bằng Pygame và vòng lặp sự kiện chính (`while True:`).
- `main.py`: Entry point (Chỉ để khởi chạy `gui.py`).
- `algorithms/`: Thư mục chứa các thuật toán (mỗi thuật toán 1 file).

---

## ⛔️ QUY TẮC SỐ 1: KHÔNG BAO GIỜ DÙNG BIẾN `global`!

Trong project cũ, tất cả viết chung 1 file nên dùng `global path_cells`, `global stats`... Hiện tại dự án đã được tách ra. 
**NẾU BẠN VIẾT THUẬT TOÁN, BẠN PHẢI SỬ DỤNG `state` TỪ `config.py`!**

❌ **Sai (Sẽ gây lỗi tày đình):**
```python
global path_cells, stats, finished
walls.add(node)
```

✅ **Đúng (Chuẩn kiến trúc):**
```python
from config import state
from grid import get_neighbors, reconstruct_path

# ... trong hàm ...
state.walls.add(node)
```

---

## 🛠 Hướng dẫn code thuật toán mới

Khi được giao nhiệm vụ code 1 thuật toán (ví dụ: `algorithms/bfs.py`), hãy tuân thủ bộ khung sau đây:

1. **Import Đầy Đủ:**
   ```python
   import time
   from collections import deque # (hoặc heapq tuỳ thuật toán)
   from config import state
   from grid import get_neighbors, reconstruct_path, next_id # (tuỳ nhu cầu)
   ```

2. **Dùng Generator (`yield`) cho Animation:**
   Thuật toán của bạn KHÔNG ĐƯỢC return ngay lập tức. Mọi thuật toán phải là hàm sinh (Generator).
   Ở mỗi bước duyệt (lấy ra từ stack/queue/priority_queue), bạn phải `yield` ra 2 biến: 
   - `visited_set`: Tập hợp các ô đã duyệt. (Nhớ dùng `.copy()`)
   - `frontier_set`: Tập hợp các ô đang chờ duyệt trong hàng đợi.
   
   *Ví dụ: `yield visited.copy(), set(queue)`*

3. **Cập nhật State trước khi kết thúc:**
   Khi thuật toán đã tìm thấy đích (hoặc duyệt hết mà không thấy), bạn **BẮT BUỘC** phải cập nhật các biến sau trong `state` trước khi dùng `return` (không phải `yield`):
   
   - `state.path_cells = p` (Đường đi tìm được từ `reconstruct_path`)
   - `state.stats.update(...)` (Cập nhật số node đã duyệt, độ dài đường, chi phí, thời gian và trạng thái found)
   - `state.finished = True` (Báo cho GUI biết thuật toán đã dừng)

   *Ví dụ khi TÌM THẤY ĐÍCH:*
   ```python
   if curr == e:
       p = reconstruct_path(came_from, e)
       state.path_cells = p
       state.stats.update(nodes=len(visited), path=len(p),
                          cost=len(p)-1, time=time.perf_counter()-t0, found=True)
       state.finished = True
       return # Dừng generator
   ```

   *Ví dụ khi KHÔNG TÌM THẤY (Hết vòng lặp queue):*
   ```python
   state.stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
   state.finished = True
   ```

4. **Đăng ký (Register) Thuật toán:**
   Sau khi hoàn thành file thuật toán (vd `algorithms/bfs.py`), bạn hãy mở file `algorithms/__init__.py`:
   - Bỏ comment phần `import` tương ứng của bạn.
   - Bỏ comment dòng tương ứng của thuật toán bạn trong biến `REGISTRY`.

Làm đúng các bước này, thuật toán của bạn sẽ tự động xuất hiện trên UI và hoạt động hoàn hảo!



---



## 🎨 Hướng dẫn cho người viết Giao diện (gui.py)

Người chịu trách nhiệm file `gui.py` đóng vai trò là "Người điều phối". Hãy tuân thủ các quy tắc sau:

1. **Vòng lặp chính (Main Loop):**
   - Phải đóng gói trong hàm `run()`.
   - Sử dụng `clock.tick(60)` để ổn định FPS.

2. **Cơ chế Animation cho Thuật toán:**
   Trong vòng lặp chính, nếu chương trình đang ở trạng thái chạy (`state.running`), thuật toán đã được khởi tạo (`state.alg_gen`) và chưa kết thúc (`state.finished`), bạn cần tạo một vòng lặp nhỏ lặp lại theo số lần bằng với tốc độ (`state.speed`).
   Bên trong vòng lặp này, hãy gọi hàm `next()` lên biến `state.alg_gen` để lấy dữ liệu `visited` và `frontier` từ thuật toán, sau đó cập nhật chúng vào `state.vis_cells` và `state.front_cells`.
   *Lưu ý cực kỳ quan trọng:* Bắt buộc phải bọc thao tác gọi `next()` trong khối `try-except` để bắt lỗi `StopIteration` (khi thuật toán chạy xong tự nhiên) và `Exception` (khi thuật toán bị lỗi). Khi bắt được lỗi, phải chuyển `state.running` thành `False` để ứng dụng không bị văng.

3. **Render thụ động:**
   Hàm vẽ (`draw_all`) chỉ nên đọc dữ liệu từ `state` và vẽ. Hạn chế tối đa việc thay đổi logic của thuật toán bên trong hàm vẽ.

4. **Xử lý Sự kiện (Events):**
   - Khi nhấn nút "Run", hãy gọi `state.start_algorithm(ALGO_FUNCS[state.cur_alg])`.
   - Khi nhấn "Clear" hoặc "Reset", hãy gọi `state.clear_search()`.
   - Lưu ý xử lý việc kéo chuột (dragging) để vẽ tường sao cho mượt mà.