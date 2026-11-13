# Bẫy bpy đã dẫm phải (Blender 4.5, headless)

Mỗi mục: triệu chứng → nguyên nhân → cách làm trong `scene_lib.py`.

## Dựng hình

- **Bevel/độ dày lệch theo trục** khi scale primitive. Blender scale cả modifier; gọi
  `bpy.ops.object.transform_apply(scale=True)` ngay sau khi đặt `o.scale` (hàm `finish()`), trước khi thêm bevel.
- **Màu nhợt/khác hex mong muốn.** Base Color nhận giá trị *linear*; đổi sRGB → linear bằng `linear(rgb)`
  trước khi gán. Nhớ cả world background và màu đèn.
- **`bpy.ops.mesh.primitive_*` làm việc trên `bpy.context.active_object`** — lấy object ngay sau ops, trước
  khi tạo cái khác. Dùng empty (`group()`) làm gốc cho từng cụm (đầu, laptop, bong bóng) để xoay/scale/parent
  cả cụm bằng một object.
- **Quy ước cục bộ của nhân vật**: −Y là mặt trước, +X phải, +Z lên; `yaw_deg` quay quanh Z. Camera chọn
  điểm neo trong không gian cục bộ (`anchor_world(obj, offset)`) chứ không hard-code tọa độ thế giới — đổi
  pose/vị trí nhân vật không phải sửa camera.
- **Tranh/đồ trang trí trên tường**: đặt vào chỗ *trống* của khung hình mỗi shot (sau khi đã xem stills),
  không rải đều — chúng dễ chui vào sau bong bóng/thẻ.

## Import GLB (chi tiết trong `assets.md`, code trong `glb_lib.py`)

- Rig sau import ở `rotation_mode='QUATERNION'` và có thể mang góc −90° X → **không gán rotation cho rig**;
  parent vào empty holder rồi xoay holder. Gán `rotation_euler` thẳng = không xoay, hoặc nhân vật nằm bẹp.
- Mỗi GLB kèm mesh `Icosphere` rác; KayKit kèm vũ khí parent vào rig → giữ mesh prefix `<TênFile>_`, ẩn còn lại.
- Animation nằm trong NLA track (một track/action); pose tĩnh = mute các track khác, dịch `strip.frame_start`
  để khung muốn trùng `scene.frame_current`, extrapolation HOLD.
- Quaternius mirror: rig có, animation không → `pose.bones[...]` xoay tay; props to gấp 2 → scale 0.5.

## Transform và cập nhật

- **`matrix_world` cũ** sau khi set location/parent cho đến `bpy.context.view_layer.update()`. Gọi
  update một lần sau khi dựng xong, trước khi tính camera. `look_at` cho object không parent dùng
  `.location` (đúng ngay) thay cho matrix_world.
- **Camera lia "vòng xa"** giữa hai shot (quay 350° thay vì −10°): Euler không tương thích. Khi đặt góc shot
  mới dùng `to_euler('XYZ', cam.rotation_euler)` để lấy nghiệm gần góc cũ (`shot_face`).
- **Khung hình đặt chủ thể**: `shot_face(cam, anchor, offset, lens, dist, side, low, aside)` — `side` là
  hướng từ chủ thể tới camera, `low` ngắm cao hơn chủ thể (chủ thể tụt xuống thấp trong khung, có
  headroom), `aside` ngắm lệch sang phải (chủ thể dạt sang trái, chừa chỗ cho thẻ). Chỉnh bằng stills,
  mỗi vòng 2–3 khung 640x360.

## Animation

- **`hide_render` không lan xuống con.** Ẩn bong bóng = ẩn empty + mọi mesh con (`children_recursive`),
  key `hide_render` với interpolation CONSTANT (`toggle()`).
- **Pose bước (miệng, mày, mắt)**: `key_pose(obj, frame, scale, lift, hidden)` key `scale`, `location`,
  `hide_render` cùng lúc, tất cả CONSTANT; lưu `rest_z` vào custom property lần đầu để `lift` luôn tính từ
  vị trí dựng. Key **theo thứ tự khung tăng dần** — hàm chỉ chỉnh keyframe cuối.
- **Camera giữ và lia**: `hold(cam, frame)` key location + rotation + lens với BEZIER EASE_IN_OUT; key tại
  `voice_frame` và `frame_end` của mỗi turn → đoạn giữa hai turn khác shot tự thành cú lia mượt trong khoảng
  im lặng (`--move` giây).
- **Chuyển động liên tục** (lắc, thở, nhấp nhô) dùng driver `sin(frame/period*6.28)` (`sway()`), không
  keyframe — nhưng driver làm *mọi khung khác nhau* nên phá dedupe; chỉ dùng cho video ngắn render hết.
- Cắt cứng (hard cut) = hai key sát nhau với CONSTANT; người dùng dự án này thích **lia mượt** hơn cắt.

## Đèn và render

- **Vệt sáng/khung sáng trên tường**: area light xuyên qua tường hoặc lọt vào ống kính ở shot rộng. Đặt
  `o.visible_camera = False` cho mọi đèn và giữ panel đèn cách tường.
- Cycles: `use_denoising = True`, `seed = 1`, `use_animated_seed = False` (bắt buộc để dedupe). Số sample
  8 đủ để soát bố cục, 32 cho bản cuối ở 720p stylized.
- `read_factory_settings(use_empty=True)` đầu script để không kế thừa cube/đèn mặc định; chạy Blender với
  `--factory-startup --python-exit-code 1` (`render.py`) để lỗi Python làm lệnh fail thật.
- Lưu `scene.blend` trước khi render — mở được bằng GUI để debug khi stills khó hiểu.

## Môi trường

- Blender mang Python riêng (có numpy, **không** Pillow); đọc wav bằng module `wave` chuẩn + numpy ngay
  trong script Blender được (lip-sync), nhưng vẽ 2D phải ở `.venv` bên ngoài.
- Windows console không in được tiếng Việt: `sys.stdout.reconfigure(encoding='utf-8')` ở đầu script Python
  thường; file output của background task có thể không phải UTF-8 (Read sẽ cảnh báo) — đừng Edit chúng.
- Trong tool Bash, `cd` đổi cwd của cả phiên → dùng đường dẫn tương đối từ gốc repo, không `cd`.
- `curl` của git-bash lỗi chứng chỉ qua proxy công ty; `urllib` của Python thì được.
- Tham số sau `--` trong lệnh blender là của script: `argv = sys.argv[sys.argv.index('--')+1:]`.
