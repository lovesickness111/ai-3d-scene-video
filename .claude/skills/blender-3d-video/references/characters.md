# Nhân vật: ông dev và mascot Claude lấy từ đâu

> **Cập nhật 2026-11-13 — pipeline three.js** (`experiments/threejs/`): người dùng đã chốt **dev = Quaternius
> "Ultimate Modular Men – Casual"** (glTF CC0, file `experiments/threejs/assets/quaternius/ModularMen_Casual.glb`,
> spec `assets/dev_casual.json`: pose ngồi bằng xoay xương, miệng gắn vào xương Head để lip-sync, neo camera/bong
> bóng cố định ở đầu, cử động thủ tục theo âm lượng). **Mascot Clawd vẫn dựng bằng code.** Dev dựng từ primitive
> dưới đây chỉ còn dùng cho bản Blender (`--assets none` trong `shoot.mjs` để quay lại).

> Đây là nhân vật **code** của video hỏi-đáp. Cần người đứng/đi, nhiều nhân vật, hoặc phong cách khác (chibi
> hài, văn phòng) thì dùng **GLB có rig** — xem `assets.md`; `demo_head_knock.py` (người dựng từ primitive)
> là ví dụ đã thất bại về thẩm mỹ, đừng lặp lại.

**Không có file asset** (.blend/.fbx/.obj). Hai nhân vật là **code**: mỗi lần chạy, scene script dựng lại
chúng từ primitive (box/ball/cyl/limb) gắn vào empty cha. Nguồn duy nhất cần giữ là hàm `programmer()` và
`mascot()` cùng bảng `MATERIALS` trong:

- repo: `scripts/_scene_lib.py` (bản gốc, dùng bởi `qa_scene.py`)
- skill: `scripts/scene_lib.py` (bản copy để mang sang project khác)

`output/qa_demo/scene.blend` chỉ là *ảnh chụp* scene đã dựng (mở được bằng Blender GUI để soi), không phải
nguồn — sửa gì cũng sửa trong code. Ảnh render của hai nhân vật (`output/*/frames`, `avatar_dev.png`,
`avatar_claude.png`) và ảnh tham chiếu `Example_2D_Image.jpeg` nằm ngoài git (`output/` bị ignore) — người
dùng muốn giữ chúng để làm video cùng kiểu, không xóa.

## Cách gọi

```python
from scene_lib import build_materials, room, desk, programmer, mascot, group, lights

M = build_materials()                                   # mọi vật liệu theo tên, màu sRGB -> linear
room(M); desk(M)                                        # phòng tường xanh ngọc + bàn/laptop/cốc/cây
p, head, face_dev = programmer(M, (-.05, -.85, 0), 112, 22)   # (loc, yaw độ, head_yaw độ)
c, face_claude   = mascot(M, (.42, -.16, .75), 30, 1.25)      # (loc, yaw độ, scale) — đứng trên mặt bàn z=.75
anchors = {'dev': head, 'claude': group('mascot_face', (0, -.06, .14), parent=c)}  # điểm neo cho camera
```

Giá trị trên là bố cục đã chốt của video hỏi-đáp (dev ngồi ghế quay 112° nhìn về mascot, mascot trên bàn
quay 30° về dev). Đổi chỗ chỉ cần đổi `loc`/`yaw`; camera dùng `anchors` nên không phải chỉnh lại shot.

## Trả về gì

| Hàm | Trả về | Dùng để |
|---|---|---|
| `programmer` | `p` (empty gốc), `h` (empty đầu, xoay `head_yaw`), `{'mouth': [ball], 'eyes': [2 ball], 'brows': [2 box]}` | `h` là neo camera + cha của bong bóng; dict là các bộ phận `key_pose` điều khiển |
| `mascot` | `c` (empty gốc, scale), `{'mouth': [box], 'eyes': [2 box]}` | neo camera = empty con `mascot_face` đặt trước mặt; dict cho lip-sync/biểu cảm |

Quy ước cục bộ: −Y là mặt trước, +X phải, +Z lên. Mọi bộ phận là con của empty gốc nên scale/xoay cả nhân vật
bằng một object.

## Hình dáng và màu (để nhận ra và để đổi)

- **Dev**: ghế xám, quần jeans, áo hoodie xanh nhạt (`hoodie` (.72,.77,.87) — người dùng chốt "áo sáng",
  **không kính**), da (.89,.7,.56), tóc nâu đen, miệng ball dẹt, hai mày box, tay phải chống bàn, tay trái
  đưa lên. Phỏng theo `Example_2D_Image.jpeg` (ảnh người thật → cartoon, `photo_cartoon_scene.py`).
- **Mascot Claude ("Clawd")**: khối hộp cam đất (`clawd` (.84,.38,.2)), 4 chân box, hai khối bên hông,
  hai mắt box đen dọc, miệng box đen nhỏ (ẩn khi `closed`). Bevel .01 cho thân, .003–.006 cho chi tiết.
- Đổi màu: sửa `MATERIALS` (tên → (rgb sRGB, roughness[, emission[, metallic]])). Đổi dáng: sửa tọa độ trong
  hàm, soát bằng still 640x360 8 samples.

## Pose mặt dùng cho lip-sync (từ `qa_scene.py`)

```python
FACE_POSES = {
    'dev': {'mouth': {'closed': {}, 'half': dict(scale=(.92, 1, 1.6), lift=-.006), 'open': dict(scale=(.85, 1, 2.2), lift=-.012)},
            'eyes': {'rest': {}, 'blink': dict(scale=(1.1, 1, .15))},
            'brows': {'rest': {}, 'up': dict(lift=.012)}},
    'claude': {'mouth': {'closed': dict(hidden=True), 'half': {}, 'open': dict(scale=(1.15, 1, 2.3), lift=-.006)},
               'eyes': {'rest': {}, 'wide': dict(scale=(1.15, 1, 1.3)), 'blink': dict(scale=(1.25, 1, .16))}},
}
EMPHASIS = {'dev': ('brows', 'up'), 'claude': ('eyes', 'wide')}   # cách mỗi người mở đầu một câu
```
Pose đầu tiên của mỗi bộ phận là pose nghỉ; `key_pose()` bước giữa các pose (CONSTANT).

## Biến thể và cách thêm nhân vật mới

- `scripts/demo_head_knock.py` có `figure()` — nhân vật **đứng**, cùng bộ phận (hông, thân nghiêng `lean`,
  gối `knee`, đầu `head_pitch`), tham số hóa màu áo/quần/tóc: mẫu để tạo người thứ ba.
- `scripts/character_kit.py` là bản primitive cũ hơn, chỉ còn để các demo cũ chạy; viết mới thì dùng `scene_lib.py`.
- Nhân vật mới: viết hàm cùng mẫu — empty gốc, bộ phận là con, trả về `(root, anchor, parts)`; thêm entry
  `FACE_POSES`/`EMPHASIS`/`SHOTS` cho speaker đó; thêm giọng vào `VOICES` của `tts.py`.
