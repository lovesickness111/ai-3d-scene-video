# Model 3D có sẵn cho three.js: lấy ở đâu, tải thế nào, đặt vào cảnh ra sao

## Nguồn đã kiểm chứng (2026-11-13)

| Nguồn | Nội dung | Rig/anim | License | Tải |
|---|---|---|---|---|
| **Quaternius – Ultimate Modular Men/Women** (`quaternius_modular_men/women`) | 11 nam (Casual, Casual2, Suit, Worker, Farmer, Punk, Beach, Adventurer, King, Spacesuit, Swat), 10 nữ; low-poly phẳng màu, tỉ lệ người thật, cao 1,87 m | rig 49 xương (Hips, Abdomen, Torso, Chest, Neck, Head, Shoulder/UpperArm/LowerArm/Hand.L/R, UpperLeg/LowerLeg/Foot.L/R, ngón tay); **mirror bỏ animation**, rest = chữ T | **CC0** (LICENSES.md của mirror, đối chiếu quaternius.com 2026-10-10) | mirror `trebeljahr/quaternius-showcase` |
| Quaternius props (`quaternius_house_interior`, `_cyberpunk`, `_modular_sci_fi`, `_street`, `--mirror <folder>`) | nội thất, máy tính, phố… | tĩnh | CC0 | cùng mirror (33 pack, 1 545 GLB) |
| **Kenney** (`kenney_furniture`, `kenney_food`, `kenney_nature`, hoặc kit khác trong `3d/kits.tsv`) | 4 812 GLB / 49 kit: Furniture 140, Food 200, Nature 329, City ×4, Modular Buildings, Space, Pirate, Castle, Car, Train… | tĩnh (kit nhân vật rig chỉ FBX, mirror bỏ) | **CC0** | mirror `shorepine/kenney` |
| **KayKit** (`kaykit_adventurers`, `_skeletons`, `_furniture`, `_city`, `_space`, `_restaurant`, `_dungeon`, `_halloween`) | nhân vật chibi (Knight, Mage, Rogue, Barbarian, Skeletons) + 75 animation trong file; bộ nội thất/phố/trạm | rig + anim | **CC0** (LICENSE.txt) | GitHub org `KayKit-Game-Assets` |
| Quaternius Universal Base Characters [Standard] + Universal Animation Library 1/2 (`quaternius_ubc_ual`) | bản free chỉ có thân **Superhero** nam/nữ (cơ bắp, không quần áo, tóc rời rigged) + UAL 44 clip trên mannequin UE (Idle_Talking, Sitting_Talking_Loop, Walk, Interact…) | rig 65 xương UE (pelvis, spine_01-03, neck_01, Head, upperarm_l…) | **CC0** (License_Standard.txt) | repo `NafisRayan/Animate-Rigged-Humanoid-No-Blender` |
| pmndrs/assets (`npm i @pmndrs/assets`) | vài model demo, HDRI, matcap, font | — | CC0 theo README | npm |

Bị **firewall công ty chặn** (lỗi chứng chỉ TLS, không lách): kenney.nl, itch.io (nơi Quaternius/KayKit phát
hành), poly.pizza, polyhaven.com, sketchfab.com, adobe.com (Mixamo). Chỉ GitHub + npm đi được → mọi thứ ở
trên tải qua `fetch_assets.py`. Trang `quaternius.com` đọc được (xem license/pack) nhưng nút tải là widget itch.

**Đã chọn cho video đối thoại**: dev = *Modular Men – Casual* (quần áo sẵn, tỉ lệ thật, cùng ngôn ngữ low-poly
với phòng + mascot); nội thất Kenney hợp tông. **Bị loại**: KayKit (chibi, đầu bằng 1/3 người → lệch với dev),
UBC bản free (thân trần bán thực, lệch tông hẳn). Quaternius pack **mới** (2025+) theo *Quaternius Asset
License* — miễn phí kể cả thương mại nhưng **cấm phân phối lại**; pack cũ CC0. Luôn đọc LICENSE trong pack.

## Tải

```
python <skill>/templates/fetch_assets.py --list
python <skill>/templates/fetch_assets.py quaternius_modular_men kenney_furniture --models threejs/assets
python <skill>/templates/fetch_assets.py --mirror-folders            # mọi pack của mirror Quaternius
python <skill>/templates/fetch_assets.py --mirror house_interior_pack --only "Chair_|Houseplant_" --models threejs/assets
```
Mỗi pack vào `threejs/assets/<pack>/` kèm license. Model video **đang dùng** thì commit vào repo (dùng chung, không phụ thuộc mirror); pack chỉ tải về thử thì để trong `.gitignore`, cần thì tải lại. Chỉ `urllib`,
GitHub API không token (60 req/giờ). File `.gltf` cần `.bin` + texture cạnh nó; UBC tham chiếu texture tên
`*_png.png` không có trong repo → copy từ bản không `_png`, và hair "Rigged to Head Bone" dùng `../Textures/`
→ sửa `uri` trong JSON về tên file (xem `experiments/threejs/assets/ubc/` đã sửa).

## Spec đặt model vào cảnh (`--assets <json>`)

```json
[{"file": "quaternius/ModularMen_Casual.glb", "role": "dev", "replaceDev": true, "asIs": true,
  "loc": [-0.15, -0.6, 0], "yaw": 188, "offset": [0, 0, -0.42],
  "pose": {"UpperLeg.L": [["side", 85]], "LowerLeg.L": [["side", -85]], "Neck": [["up", -25]], "Head": [-12, -35, 0]},
  "ik": {"Hand.R": {"at": [-0.0807, -0.1443, 0.79], "pole": [0.6, -1, -1], "fingers": [-0.0982, -0.0559, 0.775],
                    "finger": "Index2.R", "thumb": "Thumb2.R", "thumbTo": [-1, 0, 0]}},
  "face": {"anchorUp": 0.1, "anchorYaw": -54, "mouthFwd": 0.114, "mouthUp": 0.03, "mouthSide": 0, "mouthW": 0.028, "mouthH": 0.008}},
 {"file": "kenney_bookcaseOpen.glb", "loc": [-1.05, 1.05, 0], "yaw": 0, "height": 1.9},
 {"file": "kaykit_knight.glb", "loc": [0.15, 0.92, 0], "yaw": -35, "height": 1.3, "clip": "Cheer"}]
```

| Khóa | Ý nghĩa |
|---|---|
| `file` | đường dẫn trong `threejs/assets/` |
| `loc`, `yaw` | tọa độ **Blender** (x, y, z up) và góc quay quanh Z; mặt model = −Y |
| `height` | scale để bbox cao đúng mét, đáy chạm sàn, tâm x/z về gốc (props, nhân vật đứng) |
| `scale` | scale thẳng (thảm, vật phẳng) |
| `asIs` | giữ nguyên gốc/scale của file — **bắt buộc khi nhiều file ghép một nhân vật** (thân + tóc) |
| `offset` | dịch thêm (Blender) sau khi đặt — hạ nhân vật ngồi xuống ghế (−0,42) |
| `pose` | `{xương: [x,y,z]}` cộng độ vào góc cục bộ, hoặc `{xương: [["side"\|"fwd"\|"up", độ], ...]}` xoay quanh **trục thế giới của nhân vật** (phải/trước/lên), áp theo thứ tự, cha trước con — dùng cái này cho gối/vai, trục cục bộ của xương không đoán được |
| `ik` | `{xươngBànTay: {to: [phải, trước, cao] \| at: [x, y, z phòng], pole, fingers \| fingersTo, finger, thumb, thumbTo}}`: IK hai đoạn đặt cổ tay vào điểm (`to` tính từ chân theo trục nhân vật, `at` theo tọa độ phòng Blender, vd. trên laptop), khuỷu chĩa theo `pole`. Sau đó `finger` (vd. `Index2.R`) được hướng tới `fingers`/`fingersTo`, rồi bàn tay xoay quanh trục đó cho `thumb` chĩa theo `thumbTo`: ngón cái vào trong là lòng bàn tay úp xuống. Chạy sau `pose`. Dùng khi tay phải chạm đúng chỗ, vì góc khớp hai tay không đối xứng. `"ikDebug": true` in vai, chiều dài xương, khoảng cách: đích quá tầm với thì tay duỗi thẳng |
| `after` | như `pose` dạng trục thế giới, áp **sau** `ik` (xoay cổ tay, ngón) |
| `clip` | tên animation trong file (hoặc trong `animations`) chạy theo `mixer.setTime(f/fps)` |
| `animations` | glb khác cung cấp clip (cùng tên xương); `retarget: true` thử `SkeletonUtils.retargetClip` — **thất bại** với UAL→Quaternius (nhân vật co thành chấm), để lại cho sau |
| `bodyOnly` (mặc định true khi có SkinnedMesh) | ẩn mesh không rig — KayKit rải 25 vũ khí quanh nhân vật, mũ giáp cũng rời nên bị ẩn theo |
| `replaceDev`, `role`, `face` | `role` ("dev", "boss"…) dựng neo đầu tĩnh cho camera/bong bóng và gắn miệng theo hướng đầu; `replaceDev` ẩn dev dựng code (ghế dời theo `loc/yaw`), chuyển cử chỉ sang xương — xem `characters.md` |

## Bẫy GLTFLoader / rig

1. **Tên xương bị bỏ dấu chấm**: `UpperLeg.L` → `UpperLegL` (`PropertyBinding.sanitizeNodeName`). Tra cả hai.
2. Bbox để scale phải tính từ mesh **đang hiện** (sau khi ẩn vũ khí) bằng `geometry.boundingBox × matrixWorld`;
   `Box3.setFromObject` tính cả vũ khí rải quanh → nhân vật bị scale sai gấp đôi.
3. Kenney/Quaternius props dựng ở **cỡ nửa thật** (tủ sách .88) → luôn đặt `height` theo mét. KayKit đúng cỡ.
4. Tỉ lệ: nhân vật 1,75 m đứng sau bàn trong shot cận mascot (40 cm) chắc chắn bị cắt đầu — soát bằng
   `--still wide` trước khi tin một shot cận.
5. Pose bằng xoay xương: dấu/trục không đoán được → **sweep**: sinh 4 spec biến thể, chụp 4 still
   `--still wide`, ghép sheet, chọn (mỗi vòng ~1 phút). Đã tìm được cho rig Quaternius: hông
   `side +85`, gối `side −85`, vai hạ `fwd ∓70` (L −/R +), đưa trước `side +`, khuỷu `side +40..55`.
6. Khi nhân vật ngồi cạnh vật khác, kiểm **mọi góc máy**: tay duỗi tới đè lên mascot chỉ thấy ở shot phía
   Claude, không thấy ở shot dev.
7. `mixer.setTime` hoạt động trên clip đã `play()`; nhiều file ghép một nhân vật → mỗi file một mixer, cùng
   clip, cùng `setTime` → đồng bộ.
8. Tên clip KayKit: Idle, Walking_A/B/C, Running_A/B, Cheer, Interact, PickUp, Sit_Chair_Idle, Lie_Idle,
   Jump_*, Hit_A/B, Death_A/B, 1H/2H_Melee_*, Spellcast_*, T-Pose… UAL1: A_TPose, Idle_Loop,
   Idle_Talking_Loop, Sitting_Idle_Loop, Sitting_Talking_Loop, Walk_Loop, Interact, PickUp_Table, Dance_Loop…
