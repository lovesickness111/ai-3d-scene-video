# Ngách: video đối thoại hai nhân vật (dev ↔ mascot Claude)

Một ứng dụng cụ thể của pipeline — công thức này tái dùng được cho mọi "hai người nói chuyện về X"
(explainer, phỏng vấn, FAQ), chỉ đổi nhân vật, kịch bản và thẻ minh họa.

## Kịch bản: `conversation.json`

```json
[{"speaker": "dev", "text": "Ê Claude ơi, ... là gì được không?"},
 {"speaker": "claude", "text": "À, cái đó là \"**Decision API**\" đó mày. Đây, mày nhìn lên cái hình này nha."},
 {"speaker": "claude", "illustration": "definition", "text": "Nó không ngồi viết văn ... **nhanh và rẻ điên** luôn."}]
```

- `**đậm**` → chữ màu accent của người nói trong bong bóng; không ảnh hưởng TTS.
- `illustration` → turn này ở view **full-explain** và có thẻ minh họa tên đó (vẽ trong `compose.py`,
  `ILLUSTRATIONS = {name: (tiêu đề, hàm vẽ)}`). Chỉ dùng khi phải hiện nhiều thứ cùng lúc (bảng, cột so sánh,
  sơ đồ) — người dùng không muốn slide dài; phần còn lại là bong bóng.
- **Câu nối** trước mỗi thẻ, cùng người nói, là một turn riêng ("Đây, mày nhìn lên bảng so sánh này nha") →
  camera lia trong khoảng lặng giữa hai câu.
- Nhịp: dev phản ứng ngắn giữa các phần ("Ơ, lười mà cũng được việc à?"), kết bằng một cú twist hài
  (dev hỏi sếp có tăng lương không → Claude trả lời kiểu Decision API "Không. Xác suất 99%").
  Người dùng chê bản thiếu phản ứng là "hơi cụt".
- Giọng điệu đã chốt: mày/tao bạn bè, Claude tinh nghịch, dev thoải mái.

## Shot và view

`SHOTS[(speaker, view)] = {'camera': shot_face kwargs, 'bubble': {loc, scale}, 'card': (x0,y0,x1,y1) tỉ lệ}`
với view = `'explain'` nếu turn có `illustration`, còn lại `'talk'`.

- **small-talk**: cận mặt + bong bóng to cạnh đầu. Mặt không quá to, nhân vật thấp trong khung (`low`).
- **full-explain**: nhân vật dạt sang một bên và thấp (`aside`, `low`, `dist` xa hơn), bong bóng nhỏ phía trên,
  thẻ chiếm ~50% chiều ngang phía đối diện (`card = (.47, .1, .97, .82)`). Đã chốt: mascot góc dưới-trái,
  thẻ bên phải (xoay ngược lại thì dev lọt vào vùng thẻ).
- Một bong bóng **cho mỗi shot** (không phải mỗi turn) → giữ dedupe; hiện trong `voice_frame..frame_end`.
- Lia: `--move .65` s = 8 khung @12fps, cùng cặp shot → cùng 8 hình (mặt về nghỉ, bong bóng ẩn).
  Thẻ fade/trượt vào ở 3 khung cuối của cú lia và fade ra ở 3 khung đầu cú lia sau (compose, miễn phí).

## Lịch (`schedule`)

```
frame_start = khung sau frame_end turn trước
voice_frame = frame_start + round(move*fps) nếu shot khác turn trước, else frame_start
frame_end   = voice_frame + ceil((seconds + .25)*fps) - 1
```
Không có audio: ước `max(1.8, len(text)/14)` giây.

## Lip-sync và biểu cảm (không cần phoneme)

- `mouth_levels(wav, fps)`: loudness mỗi 10 ms, chuẩn hóa theo percentile 95; mỗi khung: `closed` nếu < .08,
  `open` nếu to hơn trung bình cửa sổ [t−.17, t+.25], còn lại `half`. Chỉ so với loudness tuyệt đối thì miệng
  mở suốt câu — so với lân cận mới "mấp máy theo âm tiết".
- Pose là scale/lift của mesh miệng (`FACE_POSES`), mascot `closed` = ẩn miệng. Dev: miệng ball, mascot: box.
- Đầu mỗi câu (`beats` từ audio.json): 4 khung nhấn — dev nhướn mày (`lift .012`), mascot mắt to
  (`scale 1.15,1,1.3`); nếu miệng đóng 2 khung trước câu → chớp mắt 1 khung.
- Mọi pose về nghỉ khi turn kết thúc để cú lia giống nhau.

## Overlay 2D (`compose.py`)

- Vẽ ở `SS=2` rồi downscale LANCZOS (Pillow không anti-alias hình). Font Segoe UI (`segoeui.ttf`/`segoeuib.ttf`)
  đủ dấu tiếng Việt.
- Chữ bong bóng: font lớn nhất vừa hộp (3–5% H), không vừa → cắt theo câu thành nhiều "chunk" hiện lần lượt;
  từ xuất hiện theo `cues` (`now = (f − voice_frame + 1)/fps`), vị trí cố định trong chunk (không reflow).
- Thẻ: panel trắng bo góc 26u + bóng mềm, thanh accent + tiêu đề đậm, nội dung do hàm vẽ với đơn vị
  `u = card_w/640`. Kiểu đã có: sơ đồ luồng (câu hỏi → Decision Model → xác suất), bảng chip so sánh (chip
  gạch ngang cho thứ không hỗ trợ), cột ngang (1 cột accent, còn lại trung tính, giá trị bằng mực, footer pill).
- Màu: INK (38,42,51), MUTED, PANEL, TRACK, NEUTRAL_BAR; accent dev xanh (58,104,176), Claude cam (201,94,52).
  Theo skill `dataviz`: chữ không mang màu series, một trục, nhãn giá trị trực tiếp.

## Lệnh một vòng đầy đủ (project tham chiếu)

```
.venv/Scripts/python.exe tts.py conversation.json --out output/qa_demo
python render.py scripts/qa_scene.py --out output/qa_demo --res-x 1280 --res-y 720 --dry-run
python render.py scripts/qa_scene.py --out output/qa_layout --samples 8 --res-x 640 --res-y 360 --only-frames 60,99,150,200
.venv/Scripts/python.exe compose.py output/qa_layout --frames 60,99,150,200
python render.py scripts/qa_scene.py --out output/qa_demo --samples 32 --res-x 1280 --res-y 720
.venv/Scripts/python.exe compose.py output/qa_demo
python make_video.py output/qa_demo/frames_composited --fps 12 --out output/qa_demo/video.mp4 --voices output/qa_demo
```

## Góp ý đạo diễn của người dùng (giữ nguyên cho lần sau)

- **Bong bóng chat không được nhảy/rung trong lúc nói** (2026-11-13): chữ đứng yên mà bong bóng nhún theo nhân
  vật thì xấu. Bong bóng phải parent vào object **không animate** (empty neo tĩnh), không vào đầu/thân đang
  cử động. **Bong bóng to hết mức mà vẫn trọn trong khung** để hiện được nhiều chữ.

- Mặt không quá to; mascot thấp trong khung; tường xanh ngọc + 4 tranh; dev áo sáng.
- Không lạm dụng cảnh dài; hình nhỏ cạnh bong bóng chỉ khi cần hiện nhiều thứ.
- Camera lia mượt khi đổi người nói và đổi view; nhân vật nói phải mấp máy môi, có biểu cảm.
- Có câu nối trước khi hiện hình; kịch bản không cụt, kết bằng điều hài hước/bất ngờ.
