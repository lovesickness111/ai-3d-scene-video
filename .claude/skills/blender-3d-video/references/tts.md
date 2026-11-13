# Lồng tiếng: TTS tiếng Việt cho video

`tts.py conversation.json --out <run> [--engine gemini|piper|gtranslate|edge] [--turns 0,5] [--voice dev=...]`
→ `<run>/audio/turn_XX.wav` (44.1 kHz mono) + `audio.json`. Hai tầng cache theo nội dung: `audio/raw/<key>.wav`
là âm thanh engine trả về (chỉ đọc lại khi text/giọng đổi), `turn_XX.wav` là bản đã qua filter (pitch, tốc độ,
hiệu ứng) — đổi filter chỉ chạy lại ffmpeg. **Tốc độ mặc định `--speed 1.2`** (atempo, giữ pitch): người dùng
thấy giọng TTS gốc chậm (2026-11-13). Đổi tốc độ → timeline đổi → phải render lại scene.

## Engine

| Engine | Giọng | Chi phí/điều kiện | Ghi chú |
|---|---|---|---|
| `gemini` (mặc định) | Gemini TTS, Interactions API, voice remix tùy biến lưu trong project của key | API key trả phí (`.env`: `GEMINI_API_KEY`, `GEMINI_TTS_MODEL`, `GEMINI_BASE_URL`) | Có `style` ("playful and cheeky"). Dev = Riko remix bắc `voice_8dt3hau7h3iq`, Claude = Kore remix bắc nữ `voice_v9whx7m5fzs0`. Accent **vẫn trôi** lác đác (2/18 câu) → kiểm từng clip, đọc lại câu hỏng. |
| `piper` | `vi_VN-vais1000-medium` offline CPU, `models/piper/` | Miễn phí, offline | Chỉ voice này giữ dấu thanh với espeak hiện tại (25hours/vivos mất dấu). Mẫu `output/voice_test/dev.wav` người dùng đã duyệt — giữ engine + model. |
| `gtranslate` | Google Translate read-aloud, 1 giọng nữ bắc | Miễn phí, không key, endpoint không chính thức | ≤ ~190 ký tự/lần → tự cắt theo câu rồi nối MP3. Đọc số/ngày/%/$/@/& tốt, tên lạ (Jev) vẫn sai → cần pronunciation.json. Hai người nói phân biệt bằng pitch (.9 / 1.1). |
| `edge` | Microsoft Edge neural | Miễn phí | **Bị firewall Fortinet chặn** `speech.platform.bing.com` ở máy công ty — không tìm cách vượt. |

Google Cloud TTS (chính thức, nhiều giọng nam/nữ, free tier) chưa thử — cần project GCP bật API.

## Phiên âm tiếng Anh: `pronunciation.json`

Giọng Việt đọc sai từ tiếng Anh/số có định dạng → map sang âm tiết Việt trước khi gửi
(`"Claude": "cờ lau"`, `"Decision API": "đi xi sần ây pi ai"`, `"0,042": "không phẩy không bốn hai"`,
`"99%": "chín mươi chín phần trăm"`). Khớp cụm dài trước, không phân biệt hoa thường, ranh giới từ.
Chữ trên màn hình vẫn là bản gốc; `syllables_read()` đếm số âm tiết thực đọc để canh cues.

## Word cues (TTS không trả timestamp)

`word_cues()` trong `tts.py`: tìm các khoảng lặng ≥ .18 s trong wav, gán vào khe giữa các từ sao cho mỗi
đoạn nói có tốc độ âm tiết/giây gần đều (DP, phạt .2 khi cắt không ở dấu câu), rồi trải từ đều trong đoạn.
Tiếng Việt đơn âm tiết nên cách này khớp 46/49 khoảng lặng. `beats` = giây bắt đầu câu (dùng cho biểu cảm).

## Kiểm accent (vì không nghe được)

`accent_check.py <wav...>`: gửi clip cho `gemini-3.8-flash` và `gemini-3.1-pro-preview`, hỏi
northern/central/southern/foreign + cues. Khớp tai người dùng ở mọi trường hợp đã biết. Quy trình: chạy cho
**mọi** clip, câu nào một model bảo southern → xóa `turn_XX.wav` **và** file raw của nó trong `audio/raw/`
(không thì chỉ chạy lại filter), `tts.py --turns i`, kiểm lại — lặp 1–4 lần là được. `accent_check.py
--transcribe` chép lại y nguyên những gì nghe được, dùng để kiểm số/từ tiếng Anh đọc có đúng không.

## Voice remix (Gemini)

`voice_remix.py en-us-riko "Give the speaker a Northern Vietnamese (Hanoi) accent" --preview x.wav`
→ in `voice_...` id, đưa vào `VOICES['gemini']`. `--list`, `--delete`. Preview API trả về là tiếng Anh —
người dùng muốn **mẫu tiếng Việt**: đọc 1 câu trong kịch bản bằng voice mới rồi gửi file.

## Quy tắc với người dùng

- Người dùng chọn giọng bằng tai, đã đổi nhiều lần: **không tự đổi**, đưa mẫu `.wav/.mp3` để họ nghe.
- Yêu cầu giọng **bắc (Hà Nội)**; dev nam, Claude nữ để dễ phân biệt.
- Key chỉ nằm trong header `x-goog-api-key`, đọc từ `.env` (`load_env()`); không in body lỗi quá 800 ký tự.
- Mux: `make_video.py --voices <run>` đặt mỗi wav tại `voice_frame` (không phải `frame_start`).
