# Nhân vật trong pipeline three.js

## Dev = Quaternius "Ultimate Modular Men – Casual" (chốt 2026-11-13)

File `threejs/assets/quaternius/ModularMen_Casual.glb` (CC0), spec `threejs/assets/dev_casual.json` — mặc định
của `shoot.mjs`. Đổi trang phục/giới tính = đổi `file` (Suit, Worker, Casual2, modular_women/*), pose và miệng
dùng lại được vì cùng bộ xương.

Cách nó được đặt vào cảnh (`riggedDev()` trong `scene.js`):

1. `replaceDev`: ẩn `dev.body` (người dựng code) nhưng giữ **ghế** (ghế tách thành nhóm riêng vì lý do này).
2. Pose ngồi bằng xoay xương theo trục thế giới (`pose` trong spec): hông `side +85`, gối `side −85` (ống chân
   thẳng xuống), tay phía mascot gập sát người (`fwd −70, side 15; khuỷu 55`), tay kia đặt bàn (`fwd +70,
   side 45; khuỷu 40`), bụng +8°, đầu −6°. `offset z −0,42` hạ mông xuống ghế.
3. **Neo đầu** = `Group` tĩnh tại vị trí xương Head + 0,1 m, xoay `yaw + 22°`: camera các shot `dev_*` và bong
   bóng treo vào đây (offset camera đặt về 0 ở `init`).
4. **Miệng** = sphere `M.mouth` r 0,016 scale (1.3,.5,.5) gắn làm con của xương Head; vị trí = đầu + 0,13 m
   trước + 0,035 m lên − 0,015 m sang phải (tìm bằng sweep 6 ảnh). Pose `dev_rigged`: closed (1.1,1,.5),
   half (nghỉ), open (.95,1,1.8) — chỉ scale, không `lift`.
5. **Cử chỉ thủ tục** (`animateBodies` nhánh `CHAR.dev.rigged`): mỗi khung reset xương về `userData.base`
   (pose ngồi) rồi cộng sin: ngực thở, đầu gật/nghiêng × (0,3 + energy), tay bàn (UpperArm/LowerArm **R**)
   vung theo energy, tay phía mascot gần như đứng, gối phải gõ nhịp. Nhấn đầu câu = gật −0,09 rad.
6. Không có mày/chớp mắt (mặt là texture); `EMPHASIS.dev` giữ `['brows','up']` nhưng mảng brows rỗng → vô hiệu,
   gật đầu thay thế.

Thứ **chưa làm**: retarget clip UAL (Sitting_Talking_Loop) lên rig này — `SkeletonUtils.retargetClip` làm
nhân vật co thành chấm (rest pose/scale khác); cử chỉ "có nghĩa" (chỉ tay lên thẻ) theo từ khóa.

## Mascot Clawd (dựng code, không đổi)

`mascot(loc, yaw, scale)` trong `scene.js`: 4 chân (nhóm riêng để đung đưa), **thân** là nhóm `body` (nhún,
co giãn, lắc) chứa hộp, 2 khối tay (trục quay dịch vào trong 0,118 để vẫy không hở), 2 mắt box, miệng box
(ẩn khi closed). Neo `face` tại (0, −.06, .14) là con của **root, không phải `body`** — bong bóng và camera
treo vào neo nên không nhún theo thân (quy tắc: bong bóng không được nhảy). Pose mặt `POSE.claude`: mắt `wide`
đầu câu, `blink`.

## Dev dựng code (dự phòng, `--assets none`)

`programmer(loc, yaw, headYaw)`: ghế (nhóm `seat`) + người (nhóm `body`) với khớp vai/khuỷu (`armL/armR`),
gối (`knees`), đầu (`head`), miệng/mắt/mày. Cùng số liệu với `_scene_lib.py` của Blender.

## Thêm nhân vật/thay nhân vật

- Người: thêm entry spec với `file` khác, `loc/yaw`, `pose` (bắt đầu từ pose ngồi/đứng đã có), nếu nói được
  thì `role` mới + `face`, thêm `SPEAKER` màu, `POSE`, `SHOTS` cho speaker đó, giọng trong `tts.py`.
- Vật/bối cảnh: entry với `height`, không rig. Đặt theo tọa độ Blender của phòng (bàn tại gốc 1,6×0,7, mặt
  bàn z .75; tường sau y 1,25; tường trái x −1,55).
