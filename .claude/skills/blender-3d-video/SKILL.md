---
name: blender-3d-video
description: >-
  Dựng ảnh/video 3D hoạt hình bằng Blender chạy headless qua script bpy do AI Agent viết
  (không mở GUI, không MCP): scene stylized từ primitive, nhân vật low-poly, camera, ánh sáng,
  animation, render Cycles/Eevee, overlay 2D bằng Pillow, lồng tiếng TTS, mux ffmpeg; tải và dùng
  model GLB có rig miễn phí (KayKit, Quaternius, Kenney) cho nhân vật người/hài/văn phòng và nội thất.
  Dùng khi cần tạo video 3D, cảnh 3D, nhân vật/mascot, video đối thoại hay explainer,
  parallax ảnh 2D→3D, key visual, tìm/tải model 3D, hoặc bất cứ việc gì điều khiển Blender bằng Python.
  Đọc trước khi viết dòng bpy đầu tiên, kể cả khi chỉ "render thử một hình".
---

# Video 3D bằng Blender headless + script bpy

Toàn bộ cảnh được **viết bằng code** (`bpy`), render **không GUI** (`blender --background`), và chỉ được
kiểm chứng qua **ảnh render trả về**. Claude không "nhìn thấy" scene khi viết — nên quy trình xoay quanh
việc render vài khung tĩnh rẻ để soát, rồi mới render thật. Lợi ích đổi lại: tái lập 100%, chạy batch/CI,
mọi thay đổi là một diff.

Bản hiện thực đầy đủ là repo chứa skill này (`ai-3d-scene-video`): xem `scripts/qa_scene.py`,
`scripts/_scene_lib.py`, `compose.py`, `tts.py`, `make_video.py` ở gốc repo. Bộ khởi tạo cho một project
khác nằm trong `scripts/` của skill này — copy cả thư mục skill sang `.claude/skills/` của project đó.

## Nguyên tắc

1. **Stills trước, full render sau.** Mỗi thay đổi bố cục/ánh sáng/pose → render 1–8 khung ở độ phân giải
   thấp, ít sample (`--only-frames`, 640x360, 8 samples ≈ 2–3 s/khung CPU), ghép contact sheet, xem bằng
   tool Read. Chỉ render full khi stills đã đúng.
2. **Nêu chi phí trước khi render dài, và không tự ý chạy.** Dùng `--dry-run` để đếm số hình thật sự
   phải render; 1280x720/32 samples Cycles CPU ≈ 30 s/hình. Người dùng đã khó chịu vì render lại nhiều
   lần — nói rõ "N hình ≈ M phút" và chỉ chạy khi đã được đồng ý (hoặc đã được bảo "làm luôn").
3. **Tách 3D và 2D.** Chữ, bảng, biểu đồ, thẻ minh họa vẽ bằng Pillow *sau* render (chữ 3D không đọc
   được ở cỡ video, và overlay 2D đổi được mà không render lại). Script Blender chỉ cần ghi ra hộp
   màn hình (pixel bbox) của chỗ cần vẽ.
4. **Khử trùng khung hình.** Hầu hết khung của một video "nói chuyện" là pose giữ nguyên. Băm trạng thái
   ảnh (lens + tên/ẩn/matrix_world mọi object), render mỗi trạng thái một lần, copy phần còn lại
   (2038 khung → 49 hình render). Muốn vậy: seed cố định, không animated seed, mọi chuyển động phải
   là **bước** (CONSTANT) hoặc quay về đúng pose nghỉ.
5. **Audio quyết định timeline.** Chạy TTS trước, độ dài từng câu quyết định số khung; camera di chuyển
   trong khoảng im lặng giữa hai câu.
6. **Không nghe được audio.** Kiểm giọng/accent bằng model audio (Gemini) phân loại từng clip, báo rõ
   "tôi không nghe được, bạn nghe lại giúp". Không tự đổi giọng người dùng đã chọn.
7. **Bí mật ở `.env`**, chỉ đưa key vào header; không in ra log/chat. Không vượt firewall công ty.
8. **Người thật → dùng GLB có rig, không dựng từ primitive.** Primitive chỉ hợp mascot dạng khối. Nhân vật
   người, đồ nội thất, máy tính lấy từ các pack CC0 trên GitHub (`references/assets.md`,
   `scripts/fetch_assets.py`); pose = chọn animation + khung (`scripts/glb_lib.py`), không đặt tay chân.

## Quy trình chuẩn

```
1. Kịch bản/nội dung  → conversation.json (hoặc dữ liệu đầu vào khác)
2. TTS                → <out>/audio/turn_XX.wav + audio.json (giây, cues từng từ)     tts.py
3. Scene script       → python render.py scripts/<scene>.py --out <out> --dry-run   (đếm hình)
                       → ... --only-frames a,b,c --res-x 640 --res-y 360 --samples 8 (soát)
                       → ... --samples 32 --res-x 1280 --res-y 720                   (render thật)
   ghi: frames/, timeline.json, bubbles.json, scene.blend
4. Overlay 2D         → .venv/Scripts/python.exe compose.py <out>  → frames_composited/
5. Mux                → python make_video.py <out>/frames_composited --fps 12 --out <out>/video.mp4 --voices <out>
6. Soát video         → trích khung từ mp4 bằng ffmpeg -ss, ghép contact sheet, xem; báo cáo trung thực
```

Cấu trúc project mới: `render.py`, `make_video.py`, `sheet.py`, `scripts/scene_lib.py`, `scripts/glb_lib.py`
(copy từ `scripts/` của skill), `tools/blender-4.5.x-windows-x64/` hoặc `BLENDER_PATH`, `.venv` có
`pillow numpy` (Blender có Python + numpy riêng, **không** có Pillow → mọi thứ Pillow chạy ngoài Blender),
`ffmpeg` trong PATH, `models/` (GLB tải về bằng `fetch_assets.py`); `output/`, `models/`, `tools/` và `.env`
trong `.gitignore`. Bắt đầu một scene mới từ `scripts/scene_template.py`.

Máy mới, chưa có model: `python <skill>/scripts/fetch_assets.py --list` rồi tải pack cần
(`kaykit_adventurers` cho nhân vật hài có 76 animation; `quaternius_modular_men/women` cho người văn
phòng; `quaternius_house_interior` cho nội thất). Chỉ cần mạng tới github.com. Soát pack bằng
`glb_lineup.py --preview` trước khi dựng cảnh.

## Kiểm chứng bằng mắt

- Ghép nhiều khung thành một contact sheet (Pillow, mỗi ô ~427x240) rồi Read một ảnh — rẻ hơn mở từng khung.
- Soát theo checklist: chủ thể có bị cắt mép không; đủ khoảng trống cho overlay; bong bóng/thẻ trong khung;
  không vật thể xuyên nhau; đèn không lọt vào ống kính; mặt không quá to; nhân vật thấp trong khung
  (người dùng thích vậy); chữ Việt đủ dấu; màu overlay theo quy tắc `dataviz` (1 cột nhấn màu accent,
  còn lại trung tính, giá trị ghi bằng mực tối).
- Video cuối: trích khung giữa mỗi đoạn + vài khung lúc camera đang di chuyển từ **chính file mp4**.

## Các ngách đã làm (ví dụ, không phải giới hạn)

| Ngách | Điểm chính | Tham chiếu |
|---|---|---|
| Video đối thoại 2 nhân vật (dev ↔ mascot) với bong bóng chat, thẻ minh họa, lip-sync, giọng TTS | `references/dialogue-video.md` | `qa_scene.py`, `compose.py` |
| Ảnh tĩnh stylized / key visual từ primitive (phòng, bàn, nhân vật) | `references/characters.md`; `scene_lib.py` (room, desk, programmer, mascot) | `photo_cartoon_scene.py`, `demo_head_knock.py` |
| Nhân vật/đồ vật GLB có sẵn (KayKit chibi hài, Quaternius văn phòng, nội thất, máy tính); pose từ animation trong file; gallery pose → sheet → chốt | `references/assets.md`; `glb_lib.py`, `fetch_assets.py`, `glb_lineup.py` | `kaykit_knock.py` (2 nhân vật cốc đầu, `--gallery`), `kaykit_lineup.py`, `props_lineup.py` |
| Parallax 2.5D từ một ảnh + depth map (Depth-Anything → Displace modifier) | `depth.py` + `photo_parallax.py` | |
| Chuyển động liên tục (lắc đầu, thở) bằng driver sin, không keyframe | `sway()` | `demo_programmer_mascot.py` |

Hướng mở rộng tự nhiên với cùng pipeline: explainer sản phẩm (object quay + thẻ số liệu), biểu đồ 3D
theo dữ liệu, intro/logo reveal, nhiều nhân vật/nhiều cảnh (mỗi cảnh một scene script, mux nối),
voice-over cho slide 3D, thumbnail hàng loạt từ JSON.

## Tài liệu trong skill

| File | Nội dung |
|---|---|
| `references/pipeline.md` | Kiến trúc, hợp đồng dữ liệu (timeline/bubbles/audio.json), khử trùng khung, chi phí, flag chuẩn của scene script |
| `references/bpy-gotchas.md` | Những cái bẫy bpy đã dẫm phải và cách né (hide_render, matrix_world, Euler, keyframe CONSTANT, đèn…) |
| `references/characters.md` | Nhân vật dev + mascot Claude là **code** (`programmer()`, `mascot()` trong `scene_lib.py`), không có file asset: cách gọi, điểm neo, bộ phận mặt, màu, pose, cách thêm nhân vật |
| `references/dialogue-video.md` | Công thức video đối thoại: shot/view, bong bóng, câu nối, lip-sync, biểu cảm, thẻ minh họa, góp ý đạo diễn của người dùng |
| `references/tts.md` | Các engine TTS (Gemini remix, Piper, Google Translate, edge), phiên âm tiếng Anh, word cues, kiểm accent |
| `references/assets.md` | Pack GLB CC0 đã kiểm chứng (nội dung, scale, hướng, có animation hay không), cách tải qua GitHub trong mạng công ty, 8 bẫy khi import GLB bằng bpy, quy trình chọn pose |
| `scripts/fetch_assets.py` | Tải pack vào `models/<pack>/` (KayKit, mirror Quaternius, Kenney) bằng urllib + GitHub API; `--list`, `--mirror-folders`, `--only` |
| `scripts/glb_lib.py` | `load_character` (holder empty, ẩn rác), `set_pose`/`play_action` (NLA strip), `arms_down`/`bone_rotate`, `load_prop` (bound, đặt lên sàn, scale) |
| `scripts/glb_lineup.py` | Xếp hàng nhân vật GLB để xem pack / soát pose |
| `scripts/sheet.py` | Ghép nhiều PNG thành contact sheet có nhãn (Pillow, chạy bằng `.venv`) |
| `scripts/render.py` | Chạy script trong Blender headless |
| `scripts/scene_lib.py` | Primitive, vật liệu, phòng/bàn/nhân vật mẫu, camera `shot_face`, `hold`, `key_pose`, `toggle`, `sway`, đèn |
| `scripts/scene_template.py` | Khung scene script mới: args, dựng cảnh, camera 2 shot, render loop có dedupe, `--preview/--only-frames/--dry-run` |
| `scripts/make_video.py` | PNG → MP4 bằng ffmpeg, lồng giọng theo `voice_frame` |
