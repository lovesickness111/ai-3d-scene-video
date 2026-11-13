# Kiến trúc pipeline và hợp đồng dữ liệu

## Các tầng

```
conversation.json ──► tts.py ──► audio/turn_XX.wav, audio/audio.json
        │                                   │ (giây mỗi câu, cues từng từ, beats đầu câu)
        ▼                                   ▼
render.py scripts/<scene>.py  (Blender headless, bpy)
        │  frames/frame_NNNN.png   timeline.json   bubbles.json   scene.blend
        ▼
compose.py  (Pillow, ngoài Blender)  → frames_composited/
        ▼
make_video.py  (ffmpeg)  → video.mp4 (+ video_voices.wav)
```

Mỗi tầng chạy độc lập và có thể chạy lại riêng: đổi chữ/thẻ → chỉ chạy lại compose + mux (vài chục giây);
đổi giọng → tts + scene (timeline đổi) ; đổi bố cục → scene (render).

## Hợp đồng dữ liệu

- **`timeline.json`** = `conversation.json` + các trường scene script thêm vào từng turn:
  `frame_start` (khung đầu, gồm cả lúc camera đang lia tới), `voice_frame` (giọng + bong bóng bắt đầu),
  `frame_end`, và `card` = `[x0, y0, x1, y1]` pixel cho thẻ minh họa nếu có. Khung tính từ 1.
- **`bubbles.json`**: `{ "frame": [x0, y0, x1, y1] }` bbox màn hình của thân bong bóng ở khung đó
  (`world_to_camera_view` trên 8 góc `bound_box`, y lật xuống). Compose vẽ chữ vào hình chữ nhật nội tiếp
  ellipse (`0.64 w × 0.58 h`).
- **`audio/audio.json`**: `{ "i": {key, speaker, voice, seconds, spoken, cues, beats} }`;
  `cues = [[số ký tự đã hiện trước từ, giây], ...]`, `beats = [giây bắt đầu mỗi câu]`.
  `key` = sha1(engine, cfg, filters, text) → cache theo nội dung, đổi thứ tự turn không phải đọc lại.
- Mọi lệnh nhận `--fps` phải cùng giá trị (mặc định 12 — đủ mượt cho hoạt hình stylized, rẻ gấp đôi 24).

## Scene script: flag chuẩn

`--conversation --out --engine {cycles,eevee} --samples --fps --res-x --res-y --move (giây camera lia)
--turns N --preview (chỉ khung 1) --only-frames a,b,c --dry-run`

Thứ tự trong `main()`: parse args sau `--` → `read_factory_settings(use_empty=True)` → vật liệu → hình học
→ đèn → `view_layer.update()` → camera → `configure_render` → đọc audio.json → `schedule()` → bong bóng/
animation → `save_as_mainfile(scene.blend)` → ghi timeline.json → vòng render.

## Vòng render có khử trùng khung

```python
rendered = {}
for frame in frame_range:
    scene.frame_set(frame)
    state = picture_state(scene)          # (lens, *(name, hide_render, matrix_world làm tròn 6) mọi object)
    if args.dry_run: rendered.setdefault(state, path); continue
    if state in rendered: shutil.copy2(rendered[state], path)
    else: scene.render.filepath = str(path); bpy.ops.render.render(write_still=True); rendered[state] = path
```

Điều kiện để dedupe có tác dụng: `scene.cycles.seed = 1`, `use_animated_seed = False`; mọi pose là bước
(CONSTANT) với số pose hữu hạn; nhân vật về pose nghỉ trước khi camera lia để mọi lần lia giữa cùng hai shot
giống nhau hệt; bong bóng ẩn trong lúc lia. `--dry-run` in `N pictures to render, M held copies` — đây là
con số để báo chi phí.

## Chi phí tham khảo (CPU, máy người dùng, Cycles + denoise)

| Cỡ | Samples | Giây/hình |
|---|---|---|
| 640x360 | 8 | ≈ 2.5 |
| 1280x720 | 8 | ≈ 9 |
| 1280x720 | 32 | ≈ 27–30 |

Video 170 s @12 fps = 2038 khung → 49 hình thật ≈ 25 phút. Không dedupe sẽ là 17 giờ.
Eevee Next (`BLENDER_EEVEE_NEXT`) nhanh hơn nhiều nhưng khác màu/bóng — chỉ dùng khi chấp nhận đổi look.

## Thư mục scratch

Thử bố cục trong `output/<tên>_layout/` riêng (copy `audio/` sang để timeline giống thật), xóa khi xong.
Không ghi đè `frames/` của bản render thật khi đang thử; `--only-frames` ghi thẳng vào `--out` nên trỏ
`--out` sang thư mục scratch. Giữ video cũ bằng cách đổi tên (`video_bubbles_only.mp4`) trước khi render lại.

## Khung thừa từ lần render trước

ffmpeg lấy **mọi** `frame_%04d.png` trong thư mục. Khi timeline ngắn đi (giọng nhanh hơn, bớt câu) mà
`frames/`/`frames_composited/` còn đuôi của lần trước, video sẽ dài hơn audio và kết bằng hình cũ (đã dính
một lần: video 169,8 s, audio 144 s). Scene script và compose phải xóa các khung > `frame_end` cuối khi chạy
đủ; luôn so `duration` của stream video và audio bằng ffprobe sau khi mux.

## Soát video cuối

```python
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{(f-1)/fps:.3f}', '-i', 'video.mp4', '-frames:v', '1', out])
```
cho khung giữa mỗi turn + vài khung đang lia, ghép sheet 3 cột, Read. Kiểm `ffprobe -show_entries
stream=codec_type,width,height,nb_frames,duration` để chắc có cả stream audio.
