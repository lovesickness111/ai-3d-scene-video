---
name: threejs-3d-video
description: >-
  Dựng video/ảnh 3D stylized bằng three.js chạy trong Chrome headless (Playwright), mọi khung là hàm
  thuần của số khung: phòng + nhân vật từ primitive hoặc model GLB có rig (Quaternius, KayKit, Kenney…),
  camera lia mượt, lip-sync theo giọng TTS, bong bóng chat và thẻ số liệu bằng HTML/CSS, mux ffmpeg.
  Dùng khi cần video đối thoại/explainer, cảnh 3D minh họa, dùng/tải model 3D có sẵn, hoặc khi vòng lặp
  Blender quá chậm. Đọc trước khi viết dòng three.js đầu tiên, kể cả khi chỉ "chụp thử một khung".
---

# Video 3D bằng three.js + Chrome headless

Cảnh được **viết bằng JavaScript** (three.js), chạy trong **Chrome headless** qua `playwright-core`, mỗi khung
là `renderFrame(f)` — hàm thuần của số khung — rồi chụp màn hình trang. Phần chữ (bong bóng, thẻ minh họa)
là **HTML/CSS** nằm trên canvas nên ảnh chụp đã có đủ, không cần bước ghép 2D. Giọng TTS và mux dùng chung
tool Python của pipeline Blender (`tts.py`, `make_video.py`, `reading_check.py`).

So với Blender/Cycles (skill `blender-3d-video`): **nhanh gấp ~60 lần** (0,3–0,5 s/khung kể cả chụp, so
với ~30 s), chữ/bảng là markup, model GLB nạp trực tiếp; đổi lại look phẳng hơn (không có ánh sáng dội),
bóng cứng hơn. Chọn three.js cho video giải thích, đối thoại, minh họa; chọn Blender cho ảnh cần chất
liệu/ánh sáng mềm.

Bản hiện thực đầy đủ đang chạy: `experiments/threejs/` trong repo `ai-3d-scene-video`. Bộ file để khởi tạo
project khác nằm trong `templates/` của skill này (copy sang `<project>/threejs/`).

## Nguyên tắc

1. **Stills trước, full capture sau.** Mỗi thay đổi → `--frames a,b,c` hoặc `--still <shot> --frame N`
   (vài giây/khung), ghép contact sheet (`sheet.py`), Read ảnh. Chỉ chụp full khi stills đúng.
   Người dùng muốn **xem preview trước** khi chạy full — hỏi/đưa ảnh, đừng tự chạy.
2. **Nêu chi phí.** Full = số khung × ~0,4 s (SwiftShader); 3000 khung ≈ 20–25 phút. Dừng job nền ngay khi
   người dùng bảo "từ từ".
3. **Khung là hàm thuần của `f`.** Không `Clock`, không `requestAnimationFrame`, không random: mọi chuyển
   động là `sin(2π f / (fps·period))`, animation GLB qua `mixer.setTime(f/fps)`. Chạy lại ra đúng ảnh.
4. **Audio quyết định timeline.** TTS trước; `shoot.mjs` lên lịch từ `audio.json` (camera lia trong khoảng
   lặng giữa hai câu); miệng mở theo loudness của wav.
5. **Chữ là DOM.** Bong bóng = div đặt theo bbox màn hình của ellipsoid 3D (chiếu 8 góc bound box); từ hiện
   dần bằng `visibility` để không reflow; thẻ = div có sẵn trong `index.html`.
6. **Model có sẵn ưu tiên hơn dựng tay cho người**; mascot dạng khối thì dựng bằng primitive. Mọi pack phải
   có file LICENSE đi kèm trong thư mục tải về; kiểm license thật, không tin bảng tổng hợp
   (Quaternius pack mới là QAL, pack cũ CC0).
7. **Không nghe được audio** → `respeak_check.py` (kiểm cách đọc: giọng Bắc, từ tiếng Anh đọc đúng và
   nhất quán, không thiếu/thừa chữ; câu trượt thì tự đọc lại) cho mọi clip mới; **bí mật ở `.env`**; **không vượt
   firewall** (nhiều trang asset bị chặn → dùng mirror GitHub, xem `references/assets.md`).

## Cài máy mới

```
node >= 20 (đã dùng 22.14), npm            # bắt buộc
Chrome hoặc Edge cài sẵn                     # playwright-core dùng channel 'chrome' (không tải browser riêng)
ffmpeg trong PATH                            # mux
python 3.11 + .venv (pillow numpy)           # tts.py, make_video.py, reading_check.py, sheet.py
mkdir threejs && cp -r <skill>/templates/* threejs/ && cd threejs && npm install   # three, esbuild, playwright-core
python <skill>/templates/fetch_assets.py --list
python <skill>/templates/fetch_assets.py quaternius_modular_men kenney_furniture --models threejs/assets
```
`.gitignore`: `node_modules/`, `threejs/bundle.js`, `output/`, và các pack chỉ tải về thử rồi bỏ. Model video
**đang dùng** (cùng file license của pack) và ảnh `avatar_*.png` thì commit: dùng chung, clone về chạy được
ngay, không phụ thuộc mirror còn sống (Quaternius CC0 cho phép phát lại). Đừng dùng luật `assets/**/*.png`:
nó chặn luôn ảnh avatar của thẻ tiêu đề.
Mạng công ty: chỉ `github.com`/`raw.githubusercontent.com`/`api.github.com`/npm registry đi được.

## Quy trình chuẩn

```
1. Kịch bản          conversation.json  [{speaker, text (**đậm**), illustration?}, ...]
2. TTS               .venv/Scripts/python.exe tts.py conversation.json --out output/<run>        (giọng + cues)
                     .venv/Scripts/python.exe respeak_check.py conversation.json output/<run>   (kiểm cách đọc, đọc lại câu trượt)
3. Dựng/sửa cảnh     threejs/scene.js (3D) + threejs/index.html (thẻ HTML) ; npm run build
4. Soát              node shoot.mjs --out ../output/<run> --conversation ../conversation.json --frames 40,250,900
                     node shoot.mjs ... --still wide --frame 1        ; sheet.py → Read
5. Chụp full         node shoot.mjs --out ../output/<run> --conversation ../conversation.json   (nền, báo chi phí)
6. Mux               python make_video.py output/<run>/frames --fps 12 --out output/<run>/video_main.mp4 --voices output/<run>
7. Thumbnail         node shoot.mjs ... --title  → thumbnail.png ; ffmpeg xfade 1 s + 0,5 s → video.mp4   (references/thumbnail.md)
8. Soát video        trích khung từ mp4 (ffmpeg -ss) → sheet → Read; ffprobe so duration video/audio
```
Model GLB đặt vào cảnh qua file spec JSON (`--assets threejs/assets/<spec>.json`, mặc định `dev_casual.json`,
`--assets none` để tắt) — cú pháp trong `references/assets.md`.

## Kiểm chứng bằng mắt (checklist)

Chủ thể không cắt mép; bong bóng **to hết mức nhưng trọn trong khung**, **đứng yên suốt câu** (neo vào phần
không animate — so 2 khung cùng turn) và **đúng phía** (neo xoay cùng hệ trục nhân vật); thẻ không che
mặt; tay nhân vật không đè lên vật khác (đã dính: tay dev đè mặt mascot); chân thẳng xuống sàn; miệng gắn thêm
nằm đúng giữa mặt, không chạm mũi; không sọc bóng trên tường; chữ Việt đủ dấu; `duration` video = audio.

## Tài liệu trong skill

| File | Nội dung |
|---|---|
| `references/pipeline.md` | Kiến trúc, hợp đồng dữ liệu (`audio.json`, `timeline.json`), lịch khung, lip-sync, flag `shoot.mjs`, tốc độ chụp, bẫy khung thừa |
| `references/threejs-gotchas.md` | Đổi trục Blender→three, màu sRGB/AgX, đèn + bóng (PCF/VSM), camera `shotFace` (lens→fov), bbox màn hình, chữ DOM, Chrome flags |
| `references/assets.md` | Nguồn model đã kiểm chứng + license, cách tải qua GitHub, spec JSON (`asIs`, `height`, `pose` theo trục thế giới, `offset`, `animations`, `role`), bẫy GLTFLoader, kỹ thuật dò pose bằng sweep |
| `references/characters.md` | Dev = Quaternius Casual (ngồi, miệng gắn xương Head, cử chỉ thủ tục), mascot Clawd dựng code, neo camera/bong bóng, pose mặt |
| `references/thumbnail.md` | Thẻ tiêu đề/thumbnail: chân dung dev trên nền 2D, mascot ảnh 2D góc dưới-phải, chữ HTML; `--title`, ghép 1 s + xfade vào video; góp ý bố cục của người dùng |
| `templates/scene.js` | Cảnh tham chiếu: phòng, bàn, dev primitive (dự phòng), mascot, bong bóng, SHOTS, nạp GLB, lịch camera, lip-sync, thẻ |
| `templates/index.html` | Khung trang 1280×720 + CSS bong bóng/thẻ + 8 thẻ minh họa mẫu |
| `templates/shoot.mjs` | Lịch từ audio.json, mức mở miệng từ wav, Chrome headless, chụp từng khung, `--frames/--still/--assets/--gpu` |
| `templates/assets/*.json` | Spec dev Quaternius đã chốt; spec thử KayKit + Kenney |
| `templates/fetch_assets.py` | Tải pack từ GitHub (KayKit, mirror Quaternius, Kenney mirror, UBC/UAL) kèm license |
| `templates/sheet.py` | Ghép PNG thành contact sheet có nhãn |
