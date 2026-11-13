---
name: web-search
description: Tìm kiếm thông tin trên internet bằng model deepseek-flash (qua API tương thích OpenAI). Dùng khi cần tra cứu thông tin cập nhật, tìm repo GitHub, tài liệu, tin tức, số liệu... mà không có tool WebSearch gốc khả dụng trong phiên hiện tại.
---

# Web Search qua DeepSeek Flash

Môi trường Claude Code hiện tại không có tool `WebSearch` native (xem lỗi `web_search_20250305` không được backend hỗ trợ). Skill này gọi trực tiếp một API tương thích OpenAI dùng model `deepseek-flash` để lấy câu trả lời có tra cứu internet.

## Cấu hình (đọc từ `.env` ở gốc repo)

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

- `DEEPSEEK_API_KEY`: **placeholder** — người dùng sẽ tự điền key thật vào `.env` (file đã nằm trong `.gitignore`, không commit).
- `DEEPSEEK_BASE_URL`: mặc định là endpoint DeepSeek chính thức. Nếu key/model `deepseek-flash` được cấp qua proxy khác (ví dụ aihub), đổi giá trị này thành base URL tương ứng.
- `DEEPSEEK_MODEL`: tên model, mặc định `deepseek-flash`. Đổi nếu provider dùng tên khác (ví dụ `deepseek/deepseek-flash`).

Nếu thiếu `DEEPSEEK_API_KEY`, script sẽ báo lỗi rõ ràng yêu cầu điền vào `.env` — không tự suy đoán hay dùng key khác.

## Cách dùng

Chạy script bằng Bash tool, truyền câu hỏi/câu lệnh tìm kiếm làm argument:

```
python .claude/skills/web-search/search.py "repo github nào phù hợp cho việc dựng video 3D với AI"
```

Script in ra JSON một dòng dạng:

```json
{"query": "...", "answer": "...", "model": "deepseek-flash"}
```

Đọc field `answer` để lấy nội dung trả lời, rồi tóm tắt/diễn giải lại cho người dùng. Nếu API trả lỗi, script in `{"error": "..."}` ra stderr và exit code khác 0 — đọc thông báo lỗi để biết nguyên nhân (thiếu key, sai base URL, hết quota...).

## Giới hạn

- Script không tự biết "deepseek-flash" có tra cứu internet thật hay không — điều này phụ thuộc vào provider cấp key. Nếu câu trả lời không có thông tin mới/không trích dẫn nguồn, kiểm tra lại với provider xem model có bật web search hay cần tham số bật thêm (ví dụ `extra_body`), rồi chỉnh trong `search.py`.
- Không dùng thư viện ngoài (chỉ `urllib` chuẩn của Python) để tránh phải cài thêm dependency.
