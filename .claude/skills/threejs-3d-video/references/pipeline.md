# Pipeline three.js: kiến trúc, dữ liệu, lịch khung

```
conversation.json ─► tts.py ─► output/<run>/audio/turn_XX.wav + audio.json {seconds, cues, beats}
                                        │
shoot.mjs (Node) ── đọc audio.json ──► schedule() ──► timeline.json      (frame_start, voice_frame, frame_end, shot)
          │        ── đọc wav ───────► mouthLevels() ('closed'|'half'|'open' mỗi khung, từ voice_frame)
          │        ── Playwright ────► Chrome headless: index.html + bundle.js (esbuild scene.js)
          │                               window.loadAssets(spec) → window.init(timeline) → window.renderFrame(f)
          └── page.screenshot ─────► output/<run>/frames/frame_NNNN.png
make_video.py frames --voices output/<run> ─► video.mp4 (wav đặt tại voice_frame của từng turn)
```

## Hợp đồng dữ liệu

- `conversation.json`: `[{speaker: 'dev'|'claude', text, illustration?}]`. `**đậm**` → màu accent trong bong
  bóng (không ảnh hưởng TTS). `illustration` = id thẻ → shot `<speaker>_explain` + div `#card-<id>`.
- `audio/audio.json` (tts.py): `{ "i": {seconds, cues: [[số ký tự đã hiện trước từ, giây], ...], beats: [giây đầu câu]} }`.
- `timeline.json` (shoot.mjs ghi): mỗi turn + `shot`, `frame_start`, `voice_frame`, `frame_end`, `seconds`,
  `cues`, `beats`. `make_video.py` chỉ cần `voice_frame`.

## Lịch khung (`schedule`, giống qa_scene.py)

```
shot        = speaker + '_' + ('explain' nếu có illustration, else 'talk')
frame_start = khung sau frame_end turn trước (bắt đầu 1)
voice_frame = frame_start + round(move·fps) nếu shot khác turn trước (camera lia trong lúc lặng), else frame_start
frame_end   = voice_frame + ceil((seconds + .25)·fps) − 1
```
`fps` 12, `move` 0,65 s (8 khung). Camera: `placeCamera(f)` nội suy `shotCams[prev] → shotCams[cur]` bằng
ease-in-out bậc 3 khi `f < voice_frame`; các vị trí shot tính một lần ở `init` với mọi người ở pose nghỉ.

## Lip-sync và biểu cảm

- `mouthLevels(wav)`: loudness mỗi 10 ms (trung bình |mẫu|), chuẩn hóa theo percentile 95; mỗi khung:
  `closed` nếu < .08; `open` nếu to hơn trung bình cửa sổ [t−.17 s, t+.25 s]; còn lại `half`.
- `energy` = trung bình ENERGY(level) trên ±2 khung → biên độ cử chỉ (tay, đầu, nhún).
- Đầu câu (`beats`): 4 khung nhấn — mascot mắt to, dev dựng code nhướn mày, dev GLB gật đầu (`emph.dev`).
  Chớp mắt 1 khung ở `beat−2` nếu miệng đang đóng; người nghe chớp mỗi ~3,3 s.
- Mọi pose đều là bước (CONSTANT) theo khung; không có inbetween.

## `shoot.mjs`

| Flag | Ý nghĩa |
|---|---|
| `--conversation`, `--out` | kịch bản và thư mục run (phải có `audio/audio.json`) |
| `--fps 12`, `--move .65` | như trên |
| `--frames 40,250` | chỉ chụp các khung này (soát) |
| `--still <shot> [--frame N]` | một ảnh của shot (`wide`, `dev_talk`, `claude_explain`…) với mọi người ở pose nghỉ, không bong bóng/thẻ → `still_<shot>[_N].png` |
| `--assets <json>` | spec GLB (mặc định `assets/dev_casual.json`; `none` = dev dựng code) |
| `--gpu` | dùng GPU thật thay SwiftShader (máy không GPU: render chậm hơn, đừng dùng) |
| `--title ['{json}']` | thẻ tiêu đề → `<out>/thumbnail.png`: ẩn phòng/bàn, canvas trong suốt trên nền 2D CSS (`#stage.title`), mascot xuống sàn cạnh dev, chữ trong `#title` của `index.html`; tham số `gap, side, mascotScale, mascotTurn, camDist, camSide, camHeight, aim, aimSide, fov` (mặc định = bố cục đã chốt) |

## Thẻ tiêu đề mở đầu video

Xem `thumbnail.md`: `--title` → `thumbnail.png`, rồi ffmpeg xfade 1 s + 0,5 s nối với `video_main.mp4`.

Chụp full tự xóa `frame_NNNN.png` > khung cuối (timeline ngắn lại không để đuôi cũ lọt vào ffmpeg — đã dính:
video 170 s, audio 144 s). Luôn `ffprobe -show_entries stream=codec_type,duration` sau mux.

## Tốc độ (máy người dùng, CPU, SwiftShader)

| | ms |
|---|---|
| `renderer.render` sau khung đầu | 1–45 (khung đầu 300–800 vì biên dịch shader) |
| `page.screenshot` PNG 1280×720 | ~300–500 (phần lớn thời gian) |
| Tổng/khung | 0,33–0,55 s → 3000 khung ≈ 17–27 phút |

Bóng VSM blur nặng từng làm 1,4 s/khung; PCF nhẹ hơn nhiều. Không có dedupe khung (cử động liên tục làm mọi
khung khác nhau) — chi phí tỉ lệ thẳng với độ dài video.

## Thư mục scratch và soát video

Thử asset/bố cục trong `output/asset_test/` (copy `audio/` từ run thật để có cùng timeline). Video cuối: trích
khung giữa mỗi turn + vài khung đang lia bằng `ffmpeg -ss (f-1)/fps -i video.mp4 -frames:v 1`, ghép sheet, Read.
