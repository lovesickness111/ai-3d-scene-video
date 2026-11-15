---
name: reel25d-meme-video
description: >-
  Làm video meme 2.5D kiểu cắt dán (reel 3:4 Facebook/TikTok) bằng engine reel25d: một ảnh nền, sprite PNG
  cắt từ video gốc, nhân vật khối kiểu Roblox, chữ thoại trên đầu, giọng edge-tts, sfx tổng hợp, cắt shot
  và nhịp meme (mặt shock đè màn hình + boom). Dùng khi cần video meme, reel chế, video cắt dán 2.5D,
  nhại lại reel có sẵn, hoặc bất cứ việc gì đụng tới engine reel25d / director JSON của nó. Đọc trước khi
  sửa director hay render, kể cả khi chỉ "chụp thử một still".
---

# Video meme 2.5D bằng reel25d

Engine: `reel25d/` (three.js + Chrome headless qua Playwright, SwiftShader). Mỗi khung là hàm thuần của số
khung; kịch bản là **một file JSON** (`director/<run>.json`): actors, shots, beats. Schema đầy đủ và lệnh
chạy: `reel25d/README.md` — đọc nó trước khi sửa director. Ví dụ sống đã duyệt qua nhiều vòng:
`director/skydive_meme.json`.

So với skill `threejs-3d-video`: reel25d là lớp mỏng chuyên cho meme cắt dán — không viết JS cho từng video,
chỉ viết JSON; nhân vật là hộp bo góc + mặt dán, không GLB. Cần nhân vật có rig, lip-sync, camera lia mượt
→ dùng threejs-3d-video. Cần ảnh đẹp chất liệu → blender-3d-video.

## Quy trình (thứ tự bắt buộc)

```bash
# 0. một lần / sau khi sửa scene.js:  cd reel25d && npm install && npm run build
# 1. tài nguyên vào input/<run>/:  bg.jpg (public domain), sprites/ (cut_sprites.py + rembg), audio/ (make_sfx.py)
# 2. viết director/<run>.json  (bắt đầu từ bản copy của skydive_meme.json)
# 3. giọng đọc (xem mục Tiếng):
PYTHONUTF8=1 timeout 90 .venv/Scripts/python.exe reel25d/voice.py director/<run>.json --out output/<run>
# 4. stills duyệt bố cục TRƯỚC khi render full:
cd reel25d && node shoot.mjs --director ../director/<run>.json --out ../output/<run> --times 0.5,5,11,18
# 5. render bản duyệt 810×1080 (sed đổi size từ bản gốc 1080×1440, giữ nguyên file gốc):
sed 's/"size": \[1080, 1440\]/"size": [810, 1080]/' director/<run>.json > director/<run>_810.json
cd reel25d && node shoot.mjs --director ../director/<run>_810.json --out ../output/<run>_810
# 6. mux (sfx đổi thì chỉ cần mux lại, không render lại):
.venv/Scripts/python.exe reel25d/mux.py output/<run>_810 --director director/<run>_810.json
```

Người dùng duyệt bản 810 (≈0,3–0,6 s/khung ≈ 4–7 phút); chốt rồi mới render 1080×1440 (~1,5 s/khung ≈ 18
phút). Trước render full: kiểm tra RAM trống (máy 7,8 GB hay cạn — job nền từng bị ngắt vì thiếu RAM; đề
nghị người dùng tắt bớt Chrome, app Electron không dùng thì tự tắt được). **Không bao giờ chạy 2 render
song song cùng thư mục.** `--resume` chỉ dùng khi cảnh KHÔNG đổi giữa 2 lần chạy. Thư mục output mới cần
copy `voice/` từ output cũ (giọng không phụ thuộc độ phân giải).

## Luật dàn cảnh — vi phạm là "nhân vật đứng trên trời"

Ảnh nền **dán theo camera** (không nằm trong không gian 3D), nên tư thế camera quyết định nhân vật có
"đứng trên sàn của ảnh" không:

1. **Camera luôn nhìn ngang: `look.y == pos.y` ở mọi shot.** Cúi máy xuống là thế giới 3D trôi lên trong
   khung còn ảnh đứng im → chân nhân vật bay lên trời.
2. **Chân trời của ảnh phải nằm giữa khung**: đo chân trời ảnh (fraction từ mép trên, ví dụ 0.51) →
   `bg.pan[1] = (0.51 − 0.50) × bg.zoom` cho từng shot.
3. **Chân đặt đúng vùng sàn của ảnh.** Kiểm tra nhanh: fraction chân dưới tâm khung ≈ `(pos.y / d) /
   (2·tan(fov/2))` với `d` = khoảng cách camera→nhân vật. Ví dụ fov 50, camera y=2.0, d=6 → chân ở
   50% + 36% = 86% chiều cao khung — phải rơi vào vùng sàn của ảnh (đo trên ảnh nền, vd 76%→100%).
   Nhân vật đứng xa hơn mép sàn xa của ảnh = đứng trên trời.
4. Mỗi lần sửa bố cục: render stills các beat chính và **nhìn bằng mắt** trước khi render full; soát cả
   mép khung (nhân vật/tay thò vào nửa vời đọc như "khối lạ" — xoay `look.x` vài độ để đẩy ra).
5. Lời dẫn nói gì, hình phải khớp nấy ("có 4 người" → wide phải thấy đủ 4).

## Mặt cảm xúc & nhịp meme

- Mặt là texture dán trước đầu blocky, đổi bằng `set.face`. **Cảm xúc là GHÉP THÊM lên mặt gốc, không
  thay cả mặt** (người dùng đã chỉnh vụ này): tạo biến thể bằng
  `.venv/Scripts/python.exe reel25d/tools/compose_face.py base.png overlay.png out.png --center 0.57 0.78 --width 0.42`
  (miệng cười dán lên mặt doge, giữ mắt mũi; bo góc + feather sẵn).
- **Khoảnh khắc "ngộ ra" chuẩn meme** = 3 thứ cùng beat: mặt shock `facepop {from 0.2, to 2.4}` (đập vào
  và GIỮ to, không co về), `shake` nhân vật, `sfx` boom. Beat sau mới co mặt về / đổi mặt khác. Mặt to
  che vành mũ: tăng `z` của face đó (vd 0.14) để không bị mũ cắt ngang.
- Sprite lớn (vụ nổ…) muốn che trọn nhân vật: scale `to` 1.2 thay vì 1 (mép ảnh trong PNG thấp hơn khung).
- Mặt vẽ cho blocky: `reel25d/tools/draw_face.py` (preset smirk/kid); nhân vật ĐẦU TỐI MÀU phải thêm arg
  `light` — mực đen trên đầu đen là tàng hình. Nhân vật đội mũ bandana cần `z` ≈ 0.12 cho face (khối tóc che).
- Đồ `attach` vào nhân vật sprite (billboard): offset z ÂM là sau lưng = khuất hẳn khỏi camera; chi tiết
  cần kể chuyện (balo đeo nhầm…) thì gắn trước ngực (z dương, yaw 0).
- Tìm ảnh vật thể thật (balo, đạo cụ…): **Openverse API** `curl "https://api.openverse.org/v1/images/?q=..."`
  với User-Agent tử tế — trả JSON link Flickr/Commons trực tiếp; trang bán hàng (Walmart/Amazon/Shopify)
  chặn bot, khỏi mất công. Ảnh chụp sản phẩm nền phẳng cắt rembg (`u2netp` 4,7 MB là đủ, model mặc định
  rembg nặng 1 GB) rồi ghi nguồn vào `input/<run>/LICENSES.md`.

## Tiếng

- **edge-tts flaky ~50%** (NoAudioReceived) và có khi **treo vô hạn** (file tạm 0 byte 18 phút): luôn chạy
  `PYTHONUTF8=1 timeout 90 ... voice.py ...` trong vòng retry 5–6 lần. `PYTHONUTF8=1` bắt buộc trên
  Windows — print tiếng Việt dưới cp1252 là crash (không phải lỗi mạng, đừng đoán nhầm).
- Đổi 1 câu thoại = đổi hash → voice.py chỉ sinh lại câu đó; câu dài ra thì mọi beat sau tự giãn (vụ nổ
  không bao giờ đè lời).
- SFX tổng hợp tại chỗ: `reel25d/tools/make_sfx.py` (wind, explosion, boom quét 95→42 Hz, whoosh) — boom
  và whoosh port từ `E:/Sourcecode/fitness-workflow-kit/tools/fitness_sfx.py`; cần cue mới thì port tiếp
  từ đó (punch, pop, beep có sẵn). Whoosh gắn vào beat đổi shot, gain ~0.5.
- `mux.py` đã có `alimiter=limit=0.95:level=disabled` sau amix — **giữ nguyên `level=disabled`** (mặc định
  alimiter tự đẩy ngược lên 0 dB, tưởng hết clip mà vẫn kịch trần).
- Soát mix nhanh: `ffmpeg -ss <t> -t 1 -i video.mp4 -map a -af volumedetect -f null -` — boom phải trội
  (mean cao hơn nền ~5 dB) nhưng max ≤ −0.4 dB.

## Soát trước khi đưa người dùng

Trích khung từ mp4 cuối (`ffmpeg -ss <t> -i video.mp4 -frames:v 1 ...`) ở các beat chính và XEM — đừng tin
stills của lần render trước. So độ dài hình/tiếng bằng ffprobe (lệch ≤ 10 ms là đạt). Báo đường dẫn
video + liệt kê gì đã đổi so với bản trước.
