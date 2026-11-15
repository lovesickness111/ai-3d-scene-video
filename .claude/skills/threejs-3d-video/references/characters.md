# Nhân vật trong pipeline three.js

## Dev = Quaternius "Ultimate Modular Men – Casual" (chốt 2026-11-13, sửa tới 2026-11-15)

File `threejs/assets/quaternius/ModularMen_Casual.glb` (CC0, có commit trong repo), spec
`threejs/assets/dev_casual.json`, là mặc định của `shoot.mjs`. Đổi trang phục hay giới tính thì đổi `file`
(Suit, Worker, Casual2, modular_women/*): pose, IK và miệng dùng lại được vì cùng bộ xương.

**Dáng chốt:** thân ngồi thẳng vào laptop, ghế lùi khỏi mép bàn một chút, hai bàn tay úp trên bàn phím và đứng
yên, mặt quay khoảng 60° sang mascot, miệng phẳng tối màu giữa mặt. Lúc sếp nói thì quay đầu sang sếp
(`look`, xem phần sếp).

`riggedCharacter()` trong `scene.js` (chung cho mọi nhân vật có `role`) đặt nó vào cảnh:

1. **Ghế:** `replaceDev` ẩn `dev.body` (người dựng code) nhưng giữ ghế (nhóm riêng); ghế dời theo `loc`/`yaw`.
2. **Thân và chân:** `loc (−0,15, −0,6)`, `yaw 188` (thẳng với laptop xoay 8°), `offset z −0,42` hạ mông xuống
   ghế. Hông `side +85`, gối `side −85` (ống chân thẳng xuống), bụng `[8, 0, 0]`.
3. **Đầu:** `Neck [["up", −25]]` + `Head [−12, −35, 0]` (độ local: cúi 12° nhìn màn hình, xoay 35° sang mascot;
   dấu + thì quay ra xa mascot).
4. **Tay = `ik` tới tọa độ thật của laptop** (`(−0,2, −0,05)`, xoay 8°, mặt phím cao 0,77 m):
   - Cổ tay `at` ở chỗ kê tay trước bàn phím: local laptop `(±0,105, −0,11)`, cao 0,79.
   - `finger: Index2.*` chĩa tới hàng phím giữa: local `(±0,10, −0,02)`, cao 0,775.
   - `thumb: Thumb2.*`, `thumbTo [∓1, 0, 0]` (ngón cái vào trong nên lòng bàn tay úp xuống).
   - Khuỷu `pole [±0,6, −1, −1]` (thả xuống, hơi ra ngoài và ra sau).

   Spec giữ tọa độ phòng bằng số. Đổi laptop thì tính lại bằng phép xoay `x cos8 − y sin8, x sin8 + y cos8` cộng
   vị trí laptop.
5. **Neo đầu** = `Group` tĩnh tại xương Head + 0,1 m, xoay `yaw + anchorYaw` (`anchorYaw −54` giữ hướng thế giới
   134° như dáng cũ, nên offset bong bóng và camera trong `SHOTS` dùng lại được). Camera các shot `dev_*` và bong
   bóng treo vào đây, không treo vào xương đang cử động, để bong bóng không nhảy.
6. **Miệng:** hình bầu dục phẳng, tối màu, không đổ sáng (`CircleGeometry` + `M.mouthFlat`, `MeshBasicMaterial`
   hai mặt), cùng kiểu với mắt in trên texture.
   - Nằm trong `holder` con của xương Head, mang trục của khuôn mặt (x ngang, y lên, z chĩa ra), nên các dáng nói
     chỉ kéo miệng theo chiều dọc.
   - `face`: `mouthFwd 0,114`, `mouthUp 0,03`, `mouthSide 0`, cỡ dáng half `mouthW 0,028 × mouthH 0,008` (mét).
   - Vị trí đo trên đầu chưa pose rồi xoay theo góc pose của xương Head (`a.headRest`), nên quay hay cúi đầu
     không làm miệng lệch.
   - Dáng `POSE.dev_rigged`: closed `[1.15, 1, .28]` (một nét), half (nghỉ), open `[1, 1, 1.6]` (bầu dục bè ngang).
7. **Cử động** (`animateBodies`, nhánh `CHAR.dev.rigged`): mỗi khung reset xương về `userData.base` rồi chỉ cộng
   đầu gật/nghiêng × (0,3 + energy), gật −0,09 rad ở đầu mỗi câu, gối phải gõ nhịp khi nói. Tay và ngực **không
   động**: ngực thở cũng kéo tay theo.
8. Không có mày hay chớp mắt (mặt là texture). `EMPHASIS.dev` trỏ vào mảng brows rỗng nên vô hiệu, gật đầu thay.
9. **Thumbnail:** `renderTitle` bỏ góc xoay đầu sang mascot (giữ góc cúi), để chân dung nhìn thẳng camera.

**Soát dev** (still, `shoot.mjs --still a,b,c`):
- `dev_hands` (cận tay), `dev_top` (trên vai xuống), `dev_side` (nhìn ngang). Chỉ nhìn ngang thì không biết tay
  nằm trên phím hay cạnh laptop, cũng không thấy lòng hay mu bàn tay úp xuống.
- `dev_face` + crop `dev_talk` cho miệng. Chuỗi 12 khung liền nhau của một lượt nói để xem miệng đổi dáng.
- `--look 1` cho dáng quay sang sếp. `--title` cho chân dung thumbnail.
- So hai khung cùng lượt ở vùng tay (độ chênh trung bình gần 0) để chắc tay đứng yên.

**Góp ý của người dùng về dev** (giữ cho các video sau):
- Mặt quay vào bàn, ngồi lùi ra sau một tý, mặt quay sang phía mascot; khi sếp nói thì quay mặt sang sếp.
- Lòng bàn tay úp xuống phím (bản cũ có lúc mu bàn tay úp xuống). Tay để IK đặt, không đoán góc khớp. Trong video
  tay không di chuyển.
- Miệng không lệch sang bên, không được là cục lồi có đổ sáng ("xấu, không liền mạch").

**Đã thử rồi bỏ:**
- Dáng cũ quay cả người sang mascot: `yaw 112`.
- Tay bằng góc khớp (`UpperArm fwd ±75, side 20, up ±50`; khuỷu 50; `Hand fwd −100/+70`): hai tay không đối
  xứng, mu bàn tay úp xuống phím.
- Cử chỉ gõ phím, tay vung theo giọng: người dùng không muốn tay động.
- Miệng khối cầu hồng có đổ sáng: lồi như mũi hề khi nhìn nghiêng, xấu khi há. Mảng phẳng đặt ở `mouthFwd 0,108`
  thì chìm vào mặt, chỉ còn một chấm. Há cao hơn `1,6` thì thành chữ "o" như đang ngạc nhiên.
- Retarget clip UAL (Sitting_Talking_Loop) bằng `SkeletonUtils.retargetClip`: nhân vật co thành chấm. Chưa làm
  cử chỉ "có nghĩa" (chỉ tay lên thẻ).

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
