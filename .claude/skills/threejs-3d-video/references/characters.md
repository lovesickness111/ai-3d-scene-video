# Nhân vật trong pipeline three.js

## Dev = Quaternius "Ultimate Modular Men – Casual" (chốt 2026-11-13)

File `threejs/assets/quaternius/ModularMen_Casual.glb` (CC0), spec `threejs/assets/dev_casual.json` — mặc định
của `shoot.mjs`. Đổi trang phục/giới tính = đổi `file` (Suit, Worker, Casual2, modular_women/*), pose và miệng
dùng lại được vì cùng bộ xương.

Cách nó được đặt vào cảnh (`riggedDev()` trong `scene.js`):

1. `replaceDev`: ẩn `dev.body` (người dựng code) nhưng giữ **ghế** (ghế tách thành nhóm riêng vì lý do này);
   ghế dời theo `loc`/`yaw` của spec.
2. Pose (chốt 2026-11-13 theo góp ý người dùng): **thân ngồi thẳng vào laptop, hai tay trên bàn phím, mặt
   quay sang mascot**. `loc (−0,15, −0,6)` (ngồi lùi khỏi mép bàn một chút), `yaw 188` (thẳng với laptop xoay
   8°). Chân: hông `side +85`, gối `side −85`. **Tay bằng `ik` tới tọa độ thật của laptop** (chốt 2026-11-14,
   người dùng chê tay chỉnh bằng góc khớp "chưa hợp lý"): laptop ở `(−0,2, −0,05)`, xoay 8°, mặt phím cao
   0,77 m. Cổ tay đặt `at` ở chỗ kê tay trước bàn phím (local laptop `(±0,105, −0,11)`, cao 0,79). Ngón
   `Index2` chĩa tới hàng phím giữa (`(±0,10, −0,02)`, cao 0,775). Ngón cái `thumbTo` hướng vào trong
   (`[∓1, 0, 0]`) để lòng bàn tay úp xuống. Khuỷu `pole [±0,6, −1, −1]` (thả xuống, hơi ra ngoài và ra sau).
   Tọa độ do script Python đổi từ local laptop ra phòng, giữ bằng số trong spec. Cổ tay cách nhau ±0,075 thì hai
   bàn tay chạm nhau giữa phím. Đầu quay sang mascot ≈ 60°: `Neck up −25` + `Head [−12, −35, 0]` (độ local:
   cúi 12°, xoay 35°; dấu + thì quay ra xa mascot); bụng +8°. `offset z −0,42` hạ mông xuống ghế. Soát bằng
   still `dev_side` (nhìn ngang), `dev_top` (trên vai xuống), `dev_hands` (cận tay): chỉ nhìn ngang thì không
   biết tay nằm trên phím hay cạnh laptop, không thấy lòng hay mu bàn tay úp xuống.
   (Đã thử trước đó: tay bằng góc khớp `fwd ±75, side 20, up ±50; khuỷu 50; Hand fwd −100/+70` thì mu bàn tay
   úp xuống phím và hai tay lệch nhau. Pose cũ quay cả người sang mascot: `yaw 112`.)
3. **Neo đầu** = `Group` tĩnh tại vị trí xương Head + 0,1 m, xoay `yaw + anchorYaw` (`anchorYaw −54` giữ neo
   cùng hướng thế giới 134° như pose cũ, nên offset bong bóng và camera `SHOTS` dùng lại được): camera các
   shot `dev_*` và bong bóng treo vào đây (offset camera đặt về 0 ở `init`).
4. **Miệng** = sphere `M.mouth` r 0,016 scale (1.3,.5,.5) gắn làm con của xương Head; vị trí = đầu + 0,104 m
   trước + 0,03 m lên, `mouthSide 0` (−0,015 bị người dùng chê lệch phải), đo trên đầu **chưa pose** (thẳng, nhìn theo `yaw`) rồi xoay theo đúng
   góc pose đã xoay xương Head (`a.headRest` chụp quaternion đầu trước khi pose), nên quay/cúi đầu không làm
   miệng lệch. Đổi model hay đổi số thì dò bằng still `dev_face` (chính diện) + crop `dev_talk`: miệng ra ngoài
   mặt da thì nhìn nghiêng thấy lồi như mũi hề, vào sâu quá thì mất. Pose `dev_rigged`: closed (1.1,1,.5),
   half (nghỉ), open (.95,1,1.8) — chỉ scale, không `lift`.
5. **Cử chỉ thủ tục** (`animateBodies` nhánh `CHAR.dev.rigged`): mỗi khung reset xương về `userData.base`
   (pose ngồi) rồi cộng sin: đầu gật/nghiêng × (0,3 + energy), gối phải gõ nhịp. Nhấn đầu câu = gật −0,09 rad.
   **Tay và ngực đứng yên** (người dùng: "tay không di chuyển nữa, cứ đặt tự nhiên trên bàn phím"). Ngực thở
   cũng kéo tay theo, nên bỏ luôn.
6. Không có mày/chớp mắt (mặt là texture); `EMPHASIS.dev` giữ `['brows','up']` nhưng mảng brows rỗng → vô hiệu,
   gật đầu thay thế.

Thứ **chưa làm**: retarget clip UAL (Sitting_Talking_Loop) lên rig này — `SkeletonUtils.retargetClip` làm
nhân vật co thành chấm (rest pose/scale khác); cử chỉ "có nghĩa" (chỉ tay lên thẻ) theo từ khóa.

## Ông sếp = Quaternius Modular Men "Suit" (preview 2026-11-13, để dành cho clip sau)

File `threejs/assets/quaternius/ModularMen_Suit.glb` (CC0, cùng bộ xương với dev), spec
`threejs/assets/boss_suit.json` với `role: "boss"`. Spec này chỉ có sếp, muốn có cả hai nhân vật thì ghép với
`dev_casual.json` thành một mảng. Sếp **đứng** cạnh đầu bàn bên trái, nhìn xuống dev: `loc (−1,0, −0,42)`,
`yaw 80`, đứng thẳng nên không có `offset`. Tư thế (người dùng chọn): đầu cúi `−14`, **hai tay đút túi quần**
bằng `ik` (không dùng `pose` cho tay): cổ tay `to [±0,17, 0,08, 1,10]` (phải/trước/cao, mét tính từ chân),
khuỷu `pole [±2, −1,5, 0]` (xòe ra ngoài và ra sau), ngón `fingersTo [±0,16, 0,10, 0,97]` (chĩa xuống miệng
túi), ngón cái `thumbTo [0, 1, 0]` (ra trước). Khuỷu gập rõ, bàn tay ôm mặt trước hông.
Bài học (người dùng chê tay "thẳng xuống dưới mất tự nhiên"): tay model này chỉ với được **0,42 m**
(cánh tay trên 0,18 + cẳng tay 0,24, vai cao 1,43). Cổ tay đặt ở 0,95–1,0 là quá tầm, IK duỗi thẳng tay. Muốn
khuỷu gập khoảng 70° thì cổ tay cách vai chừng 0,34 m. In số đo bằng `"ikDebug": true` trong spec trước khi
chọn điểm. Cổ tay vào sát giữa người (`±0,15`) mà không định hướng ngón thì hai bàn tay chồng lên nhau trước
đũng quần. Góc máy `boss_talk` (cận sếp),
`boss_dev` (hai người ở bàn), cùng các góc soát `boss_body`, `boss_hips`, `boss_hipsL`, neo vào đầu sếp lúc
`init`.

**Dev quay sang sếp khi sếp nói** (người dùng yêu cầu): `animateBodies(…, look)`, `look` 0 → 1 xoay cổ 55°
và đầu 75° quanh trục đứng (`turnAboutUp`). Không xoay ngực, vì ngực xoay 8° đã kéo tay khỏi bàn phím.
`renderFrame` đặt `look = 1` cho lượt có `speaker: "boss"` và chuyển mượt trong lúc camera lia. Soát bằng
`shoot.mjs --look 1 --still dev_talk,dev_hands`.

Chưa làm: lịch nói cho speaker `boss` (`SPEAKER`, `POSE`, giọng trong `tts.py`, cử chỉ trong `animateBodies`),
và chỉnh lại `dev_talk` khi có sếp (từ góc đó sếp đứng ngay sau đầu dev). Đứng sát sau ghế thì tay giải thích
trông như sắp cốc đầu dev, nên đặt sếp ra cạnh đầu bàn.

**Dò tay bằng `ik` thay cho góc khớp.** Hai tay của model Quaternius không đối xứng theo trục `side/fwd/up`:
cùng một bộ góc đảo dấu thì một tay thả xuống, tay kia chìa ra trước (cổ tay dev cũng phải lệch số
−100/+70). Đặt bàn tay vào một điểm cụ thể (túi quần, bàn phím, tay nắm cửa) thì khai báo `ik`. Code tính khuỷu
bằng IK hai đoạn rồi xoay cánh tay trên và cẳng tay cho trúng, xong mới áp `after` (xoay cổ tay hay ngón, cùng
cú pháp với `pose`).

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
