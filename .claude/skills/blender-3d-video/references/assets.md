# Model 3D có sẵn (GLB): lấy ở đâu, tải thế nào, dùng trong bpy ra sao

Nhân vật dựng từ primitive (xem `characters.md`) chỉ đẹp khi là khối cố ý (mascot). **Người đứng/đi dựng
bằng primitive trông hỏng** — đã thử (`demo_head_knock.py`) và người dùng chê "xấu đau đớn". Với người,
dùng GLB có rig sẵn: chất lượng nhảy vọt, pose = chọn animation + khung, không phải đặt tay chân.

## Nguồn đã kiểm chứng (tải được qua `scripts/fetch_assets.py`)

| Pack id | Nội dung | Rig / anim | Scale, hướng | License |
|---|---|---|---|---|
| `kaykit_adventurers` | Knight, Mage, Rogue, Rogue_Hooded, Barbarian — chibi đầu to, hài | Rig 41 xương + **76 animation** trong file | cao ≈1.75 m, mặt về **−Y** | CC0 |
| `kaykit_skeletons` | Skeleton_Warrior/Mage/Rogue/Minion — cùng rig/anim với Adventurers | như trên | như trên | CC0 |
| `quaternius_modular_men` | Suit, Casual, Casual2, Worker, Farmer, Punk, Beach, Swat, Spacesuit, King, Adventurer | Rig 50 xương (có ngón tay), **không có animation** (mirror bỏ) | cao ≈1.86 m, mặt về −Y, rest = chữ T | CC0 |
| `quaternius_modular_women` | Suit, Formal, Casual, Worker, SciFi, Soldier, Punk, Witch, Medieval, Adventurer | như trên | như trên | CC0 |
| `quaternius_house_interior` | 123 món: Chair_1-4, Bookshelf, Shelf_*, Houseplant_1-8, Light_*, Table_*, Couch_*, Door_*, Window_*, Kitchen_*, Bed_* | tĩnh | **to gấp 2** (ghế 1.7 m) → scale 0.5 | CC0 |
| `quaternius_cyberpunk` | 71 món, có Computer, Computer_Large, TV_1-3 (kiểu thùng máy/arcade) | tĩnh | ≈ gấp 2 | CC0 |
| `quaternius_modular_sci_fi` | 91 món, Props_Computer, Props_ComputerSmall, Props_Shelf… | tĩnh | ≈ gấp 2 | CC0 |
| `kaykit_furniture` | 53 món gltf: bàn, ghế, kệ, giường, đèn, thảm, tranh | tĩnh | cùng cỡ KayKit | CC0 |
| `kaykit_city`, `kaykit_space`, `kaykit_restaurant`, `kaykit_dungeon`, `kaykit_halloween` | nhà/đường/xe; module trạm vũ trụ, máy tính; bếp; hầm ngục; bí ngô | tĩnh | — | CC0 |
| `kenney_platformer` | 1 robot bé có ăng-ten (`character.glb`): idle/walk/jump | rig đơn giản | nhỏ | MIT |

Nhân vật hài: **Barbarian** (đầu gấu, râu), **Skeleton_Minion** (trọc, mắt tròn), **Skeleton_Mage** (mũ hồng
khổng lồ), **Mage** (mắt to, mũ quá khổ). Văn phòng/business: Quaternius **Suit/Formal/Casual/Worker**.
Chưa có laptop, bàn chữ nhật, ghế xoay trong các pack trên → dựng procedural (`scene_lib.desk`).

Danh sách 76 animation KayKit (dùng chung cho mọi nhân vật KayKit): Idle, Unarmed_Idle, Walking_A/B/C,
Running_A/B, Cheer, Hit_A, Hit_B, Dodge_Backward/Forward/Left/Right, Block, Blocking, Jump_Idle/Start/Land,
Lie_Down/Idle/StandUp, Sit_Chair_Down/Idle/StandUp, Sit_Floor_*, PickUp, Throw, Use_Item, Interact,
Unarmed_Melee_Attack_Punch_A/B, Unarmed_Melee_Attack_Kick, 1H/2H_Melee_Attack_*, Spellcast_*, Death_A/B,
T-Pose… (in đủ bằng `glb_lib.actions_of(rig)`).

## Cách tải

```
python .claude/skills/blender-3d-video/scripts/fetch_assets.py --list
python .claude/skills/blender-3d-video/scripts/fetch_assets.py kaykit_adventurers quaternius_modular_men
python .claude/skills/blender-3d-video/scripts/fetch_assets.py --mirror-folders        # mọi thư mục của mirror Quaternius
python .claude/skills/blender-3d-video/scripts/fetch_assets.py --mirror house_interior_pack --only "Chair_|Houseplant_"
```

Tải vào `models/<pack id>/` (thư mục này trong `.gitignore`), kèm LICENSE của pack. Chỉ dùng `urllib`
chuẩn, header User-Agent, GitHub API không cần token (60 request/giờ đủ dùng).

**Mạng công ty**: chỉ `github.com` / `raw.githubusercontent.com` / `api.github.com` đi được. `kenney.nl`,
`poly.pizza`, `itch.io` lỗi chứng chỉ (cả Python lẫn PowerShell) — không tắt verify SSL để lách; bảo người
dùng tải tay bằng trình duyệt rồi bỏ vào `models/`. Trang `quaternius.com` tải qua widget itch nên cũng
không tự động được; **mirror GitHub `trebeljahr/quaternius-showcase`** có 1.545 GLB của 33 pack Quaternius
(`LICENSES.md` ghi CC0 từng pack) nhưng **đã bỏ animation**. Muốn 24 animation gốc của Modular Men/Women:
tải tay trên quaternius.com. Mixamo cần đăng nhập Adobe — bỏ.

Mô tả pack không tải được thì dùng tool `WebFetch` (đi đường khác, đọc được quaternius.com; kenney.nl vẫn
lỗi) hoặc skill `web-search`. Tìm repo: GitHub search API `search/repositories?q=...` chạy được bằng urllib.

## Dùng trong bpy — các bẫy đã dẫm (xem `scripts/glb_lib.py`)

1. **`rotation_mode` là QUATERNION** sau import → gán `rotation_euler` bị bỏ qua, nhân vật không xoay.
   Và rig/`RootNode` có thể mang sẵn góc −90° X (đổi trục Y-up → Z-up) → **ghi đè rotation là nhân vật nằm
   bẹp**. Cách đúng: không đụng transform đã import; parent object gốc nhất vào một **empty holder** rồi
   di chuyển/xoay/scale holder (`glb_lib.load_character` trả `holder`).
2. **Rác đi kèm**: mesh `Icosphere` (1.9×2×2, không vật liệu) trong mọi GLB của hai nguồn trên; KayKit kèm
   vũ khí/khiên (`1H_Sword`, `Round_Shield`…) parent vào rig. Giữ mesh có prefix `<TênFile>_` (Knight_Body,
   Suit_Head…), ẩn phần còn lại bằng `hide_render` + `hide_viewport` + `hide_set(True)`.
3. **Pose = NLA strip**: importer tạo mỗi animation một NLA track (76 track) và gán action đầu tiên vào
   `animation_data.action`. `set_pose(rig, 'Hit_B', 3)`: `action = None`, mute mọi track trừ track đích,
   `strip.frame_start = SCENE_FRAME - khung_muốn`, extrapolation HOLD, blend REPLACE. Hai nhân vật khác khung
   của cùng action vẫn render ở một `scene.frame` nhờ dịch strip. Action thứ hai import trùng tên có hậu tố
   `.001` → so bằng `name.split('.')[0]`.
4. **Quaternius mirror không có animation** → `animation_data` None hoặc không track. Pose tay bằng
   `pose.bones['UpperArm.L'].rotation_euler`: trục **X**, dấu **âm cho cả hai bên** là hạ tay xuống
   (`arms_down(rig, 72)`); trục Z gập tay ra trước, Y xoay quanh cánh tay. Ngón tay có xương riêng.
5. **Props Quaternius to gấp đôi**, KayKit không. Đặt props: tính bound box world sau `view_layer.update()`,
   dịch sao cho đáy chạm sàn (`load_prop` trả `lo, hi`).
6. **Camera**: nhân vật cao 1.75–1.86 m, đầu to → cam cách ≥4.5 m với lens 45 cho toàn thân hai người;
   ước lượng sai cỡ đã làm hai vòng render đầu bị cắt đầu. Luôn soát preview 640×360 trước.
7. **GLB nhúng texture**, Cycles đọc được ngay; file `.gltf` cần `.bin` + `.png` cạnh nó (KayKit bits).
8. Nhân vật xoay mặt vào nhau trên trục X: người ở −X yaw **+90°**, người ở +X yaw **−90°** (mặt gốc −Y).

## Quy trình chọn pose

1. `--gallery "Action:f1,f2;Action2:f3"` (`kaykit_knock.py`) → một nhân vật, mỗi pose một still 640×360.
2. Ghép bằng `sheet.py`, Read một ảnh, chọn action+frame.
3. Ghép hai nhân vật, thử 3–4 tổ hợp (gap, scale) cũng qua sheet. Ví dụ đã chốt cho "cốc đầu": Knight
   `Unarmed_Melee_Attack_Punch_A:12`, Rogue `Hit_B:3` scale 0.62, gap 0.74 — nắm tay chạm đỉnh đầu.
4. Render thật 1280×720 32 samples (~45 s/ảnh).

Video với nhân vật KayKit: unmute strip và đặt `frame_start` tại khung bắt đầu, nối nhiều strip trên cùng
track (ví dụ Idle → Punch_A → Idle); không cần keyframe tay.
