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

## Kiểm cách đọc (vì không nghe được)

Model TTS hay đọc từ tiếng Anh lúc thế này lúc thế khác, đọc sai hoặc bỏ chữ, còn giọng thì thỉnh thoảng
trôi về giọng Nam. `reading_check.py conversation.json output/<run>` gửi từng clip cho `gemini-3.8-flash` và
`gemini-3.1-pro-preview`, kèm câu kịch bản và cách phiên âm mong muốn của từng từ (lấy từ `pronunciation.json`;
từ tiếng Anh chưa có trong bảng cũng được hỏi). Model trả về giọng miền, bản chép lại, mỗi từ nghe ra thế nào,
và từ nào bị thiếu, thừa hay đọc sai. Câu **trượt** khi có model nghe ra giọng không phải Bắc, hoặc cả hai
model cùng bắt một từ. Từ chỉ một model bắt thì để người dùng nghe lại. Cuối lượt in bảng "mỗi từ nghe ra thế
nào ở từng câu" để bắt chỗ đọc không nhất quán, báo cáo đầy đủ ghi vào `audio/reading_check.json`.

`respeak_check.py conversation.json output/<run>` chạy bước trên rồi tự đọc lại câu trượt, tối đa 4 lần:
xóa `turn_XX.wav` **và** file raw trong `audio/raw/` (không thì chỉ chạy lại filter) rồi `tts.py --turns i`.
Câu đọc lại 4 lần vẫn trượt thì thường là lỗi phiên âm hay kịch bản, phải sửa `pronunciation.json`.
Bẫy đã gặp: từ khóa viết tắt (`AI`) khớp không phân biệt hoa thường thì ăn luôn chữ "ai" tiếng Việt
("chả ai soi" thành "chả ây ai soi"), nên từ khóa in hoa chỉ khớp khi viết hoa. `accent_check.py
[--transcribe]` giữ lại để hỏi nhanh một clip.

## Voice remix (Gemini)

`voice_remix.py en-us-riko "Give the speaker a Northern Vietnamese (Hanoi) accent" --preview x.wav`
→ in `voice_...` id, đưa vào `VOICES['gemini']`. `--list`, `--delete`. Preview API trả về là tiếng Anh —
người dùng muốn **mẫu tiếng Việt**: đọc 1 câu trong kịch bản bằng voice mới rồi gửi file.

## Quy tắc với người dùng

- Người dùng chọn giọng bằng tai, đã đổi nhiều lần: **không tự đổi**, đưa mẫu `.wav/.mp3` để họ nghe.
- Yêu cầu giọng **bắc (Hà Nội)**; dev nam, Claude nữ để dễ phân biệt.
- Key chỉ nằm trong header `x-goog-api-key`, đọc từ `.env` (`load_env()`); không in body lỗi quá 800 ký tự.
- Mux: `make_video.py --voices <run>` đặt mỗi wav tại `voice_frame` (không phải `frame_start`).
