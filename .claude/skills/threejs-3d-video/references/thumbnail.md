# Thumbnail / thẻ tiêu đề mở đầu video

Một ảnh 1280×720 chụp bằng chính pipeline (`node shoot.mjs ... --title`), rồi ghép thành 1 giây đầu video với
hiệu ứng tan vào cảnh. Bố cục đã chốt với người dùng (2026-11-13), dùng làm mặc định:

```
┌───────────────────────────────────────────────────────────────┐
│  (đĩa vàng)                 Giải thích Model quyết định (Jev)  │
│   ┌──────────┐              và ứng dụng trong dựng Video        │  ← h1 54px, cụm nhấn màu accent cam
│   │ mặt + vai│              Cast: Dev xịn và Claude mỏ hỗn      │  ← sub 28px, tên tô màu từng nhân vật
│   │  của dev │                                                  │
│ (đĩa cam)    │                                   ┌──────────┐  │
│   └──────────┘                                   │ mascot 2D│  │  ← avatar_claude.png, góc dưới-phải, không hình nền sau
└──────────────────────────────────────────────────┴──────────┴──┘
```

## Cách nó được dựng (`renderTitle()` trong `scene.js`, CSS/HTML trong `index.html`)

1. **Ẩn phòng**: `roomParts` = mọi object `room()/painting()/desk()` thêm vào scene lúc dựng → `visible=false`.
   Ghế của dev giữ (thuộc nhân vật). Bong bóng, thẻ, chữ hội thoại ẩn.
2. **Canvas trong suốt**: `WebGLRenderer({alpha:true})` + `setClearColor(0x000000, 0)` chỉ trong chế độ title →
   nền là CSS của `#stage.title` (gradient nhạt + vài `radial-gradient` đĩa màu lấy từ bảng màu tranh treo tường:
   cam đất `#c95e34`, vàng `#e0a838`, navy `#21335c`). Chrome chụp DOM + canvas nên ảnh ra đã hoàn chỉnh.
3. **Chân dung dev**: camera đặt trước mặt theo hướng nhìn của nhân vật, cách neo đầu `camDist 1,5 m`, `fov 32`,
   ngắm lệch `aimSide −0,28` để mặt + vai chiếm nửa trái; mắt mascot `wide`, mọi người ở pose nghỉ (`energy 0`).
   Dáng ngồi có đầu quay sang mascot, nên `renderTitle` bỏ góc xoay đó (giữ góc cúi) để dev nhìn thẳng camera.
   Không bỏ thì chân dung trông như ngoảnh mặt đi chỗ khác.
4. **Mascot = ảnh 2D** `<img id="title-mascot" src="assets/avatar_claude.png">` ghim `right 30px; bottom −40px;
   height 380px`, `drop-shadow` nhẹ; mascot 3D bị ẩn (`opts.mascot3d` để bật lại — khi đó nó đứng cạnh ngực dev,
   tham số `gap/side/mascotUp/mascotScale/mascotTurn`).
5. **Chữ**: khối `#title` (h1 + `.sub`) ở `left 660px; top 130px; width 590px`. Sửa nội dung trực tiếp trong HTML.

Lệnh: `node shoot.mjs --out ../../output/<run> --conversation ... --title` → `<run>/thumbnail.png`
(`--title '{"camDist":1.3,"aimSide":-0.22}'` để thử biến thể; `--title '{"mascot3d":true}'`).

## Ảnh 2D của nhân vật (avatar)

`avatar_claude.png` / `avatar_dev.png` (512×512 RGBA) là render Blender cũ với nền trong suốt
(`film_transparent`, camera cận mặt). Làm avatar mới bằng three.js: chế độ title với `mascot3d:true`, ẩn dev
(`dev.root.visible=false`), ngắm vào mascot, rồi `page.screenshot({omitBackground:true})` sau khi bỏ nền CSS —
chưa viết thành flag, làm khi cần.

## Ghép vào video

```
# thẻ tĩnh 1 s, tan 0,5 s vào cảnh đầu; tiếng: 1 s lặng rồi tiếng gốc nguyên vẹn (không crossfade kẻo mất chữ đầu)
ffmpeg -loop 1 -framerate 12 -t 1.5 -i thumbnail.png -f lavfi -t 1.0 -i anullsrc=r=44100:cl=mono -i video_main.mp4 \
  -filter_complex "[0:v]format=yuv420p,setsar=1,fps=12,settb=AVTB[v0];[2:v]fps=12,settb=AVTB[v1];\
[v0][v1]xfade=transition=fade:duration=0.5:offset=1.0[v];[1:a][2:a]concat=n=2:v=0:a=1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart video.mp4
```
- `xfade` đòi hai nguồn cùng timebase → `fps=12,settb=AVTB` cho cả hai, không thì lỗi
  "timebase (1/12) do not match (1/12288)".
- Độ dài ảnh = thời gian hiện + thời gian tan (1,0 + 0,5); `offset` = thời gian hiện.
- Bước này mã hóa lại toàn video (~1 phút cho 4 phút); muốn nối không mã hóa lại thì làm intro thành mp4 cùng
  codec rồi `concat -c copy`, nhưng không có hiệu ứng tan.
- Kiểm bằng cách trích khung 1, 12, 14, 16, 18, 21 từ `video.mp4` ghép sheet: thấy thẻ → mờ dần → cảnh.

## Quy trình chỉnh và những gì người dùng đã góp ý

1. Chụp 2 biến thể tham số mỗi vòng (`--title '{...}'`), ghép sheet 2 ô, Read, chọn; ở góc cận **dịch 5 cm
   là vật rơi khỏi khung** — tính vị trí theo khoảng cách tới camera, đừng đoán.
2. Góp ý đã nhận và áp dụng: **dev chỉ hiện mặt + vai** (như `avatar_dev.png`), không cả người ngồi ghế;
   **mascot ở góc dưới-phải**, dùng ảnh 2D được; **không có hình tròn/đĩa màu sau mascot** để nó nổi; **bỏ dòng
   tag phụ** ("Hỏi – đáp · 4 phút"); thẻ hiện **1 giây** và **có chuyển cảnh** vào video.
3. Chữ: tiêu đề một ý, cụm khóa tô accent; tên nhân vật tô màu của người đó (dev xanh `#3a68b0`, Claude cam).
4. Soát: chữ không chạm đĩa màu đậm (navy) gây khó đọc; mặt dev không bị đĩa vàng cắt ngang mắt; mascot không
   che chữ; mép dưới ảnh 2D được phép tràn khung (bottom âm) để trông như ghé vào.
