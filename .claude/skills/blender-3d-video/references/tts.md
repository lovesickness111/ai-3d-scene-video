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

## Chọn giọng giữ được giọng Bắc (kinh nghiệm 2026-11-16)

Gemini TTS mỗi lần gọi có thể đọc ra một giọng miền khác nhau. Thứ tự nên thử:

1. **Giọng tiếng Việt bản địa trong thư viện trước** (`vi-vn-*`, loại prebuilt, dùng thẳng id, không cần tạo
   hay lưu gì): `GET /v1beta/voices?language_code=vi-VN` trả về 40 giọng. Tất cả chỉ gắn `accent: "Vietnamese"`,
   **không ghi Bắc hay Nam**, nên phải tự thử từng giọng. Đã thử với `style` để trống, mỗi giọng 3 lần, chấm
   bằng `reading_check`:

   | Giọng | Mô tả thư viện | Bắc / 3 |
   |---|---|---|
   | `vi-vn-tutor-2` | nam 62 tuổi, khách quan, thẳng | **3** (sếp clip 2) |
   | `vi-vn-tutor-6` | nam 39 tuổi, tự tin, rõ | **3** (dev clip 2) |
   | `vi-vn-tutor-7` | nam 55 tuổi, ấm | **3** |
   | `vi-vn-assistant-1` | nam 43 tuổi | **3** |
   | `vi-vn-tutor-4` | nam 38 tuổi | 0 |
   | `vi-vn-advisor-5` | nam 42 tuổi | 0 |
   | `vi-vn-training-6` | nam 49 tuổi | 0 (cả 3 lần giọng Nam) |

   Cùng nhóm `tutor` mà có giọng Bắc có giọng Nam: không suy theo tên nhóm, phải thử.
2. **`style` để trống hoặc thật ngắn, giữ nguyên cả cuộc hội thoại.** Hướng dẫn của Google: "Avoid putting age,
   gender, names, or permanent accent changes in `speech_metadata.style`", persona dài là "the most common cause
   of voice drift", "extra prompt text increases drift", "most requests need no `style` instruction at all".
   Giọng miền và tuổi để ở chính giọng, không nhét vào `style`. `tts.py` không gửi `speech_metadata` khi `style`
   rỗng. Đổi riêng cho một clip: `--style dev=` (rỗng), `--voice dev=vi-vn-tutor-6`; truyền y nguyên hai cờ này
   cho `respeak_check.py`, để câu đọc lại dùng đúng giọng.
3. **Remix chỉ giữ được giọng miền của giọng gốc** (tài liệu: "Relative remix prompts preserve the baseline
   language and regional accent of the `base_voice`"). Remix từ giọng tiếng Anh (Orus, Charon, Algenib) với chỉ
   dẫn "giọng Hà Nội + già + uy" thì 9 lần đọc có 8 lần trượt Nam. Remix lần hai để "ép" giọng Hà Nội (OrusHanoi)
   qua 3/3 lúc có `style`, nhưng bỏ `style` thì 0/3. Remix từ một giọng **đã là giọng Bắc** (giọng dev) thì giữ được
   3/3. Muốn remix thì lấy gốc là giọng `vi-vn-*` giọng Bắc, mỗi lần chỉ đổi một hai đặc điểm (tuổi, độ trầm).
4. Muốn chắc nhất thì có **Voice replication**: nhân bản giọng từ đoạn ghi âm 10–30 s của một người thật nói
   giọng Hà Nội, kèm câu đồng ý đọc bằng tiếng Việt (`vi-VN` được hỗ trợ). Cần người nói thật và sự đồng ý của họ.
5. Một câu trượt mãi dù đã đổi giọng thì sửa câu chữ, đừng cố đọc lại thêm. Đã gặp: "Được. Còn nhân vật với đồ
   đạc… thì sao?" trượt 10 lần, viết thành "Ừ. Thế còn nhân vật với đồ đạc…?" thì qua ngay lần đầu.

Model `gemini-3.8-flash-tts` (đang dùng) là model Google khuyên cho phương ngữ vùng miền.

### `voice_remix.py`

`voice_remix.py <base> "<chỉ dẫn>" --preview x.wav` trả về id `voice_...`, đưa vào `VOICES['gemini']`. Có thêm
`--list`, `--delete`. Base có thể là id thư viện (`vi-vn-tutor-2`), tên prebuilt hoặc một `voice_...` đã tạo.
Preview API trả về là tiếng Anh, mà người dùng muốn **mẫu tiếng Việt**: đọc 1 câu trong kịch bản bằng giọng mới rồi
gửi file. Giọng remix nào không dùng thì xóa (`--delete`); xóa giọng gốc không ảnh hưởng giọng đã remix từ nó.

## Quy tắc với người dùng

- Người dùng chọn giọng bằng tai, đã đổi nhiều lần: **không tự đổi**, đưa mẫu `.wav/.mp3` để họ nghe.
- Yêu cầu giọng **bắc (Hà Nội)**; dev nam, Claude nữ để dễ phân biệt.
- Key chỉ nằm trong header `x-goog-api-key`, đọc từ `.env` (`load_env()`); không in body lỗi quá 800 ký tự.
- Mux: `make_video.py --voices <run>` đặt mỗi wav tại `voice_frame` (không phải `frame_start`).
