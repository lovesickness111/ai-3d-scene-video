# three.js headless: những gì đã dẫm phải

## Trục và đơn vị

- Cảnh gốc viết cho Blender (Z up). Trong `scene.js` mọi helper nhận **tọa độ Blender** và đổi
  `v3([x,y,z]) = (x, z, −y)`; kích thước/scale `sz([x,y,z]) = (x, z, y)`; Euler XYZ Blender → three
  `(rx, rz, −ry)`; yaw quanh Z Blender = `rotation.y` three (cùng dấu). Nhờ vậy số liệu bố cục dùng chung
  với `_scene_lib.py`. Mặt trước nhân vật = −Y Blender = +Z three (đúng với mọi GLB Quaternius/KayKit).
- Đơn vị mét. Blender lens → fov dọc: `hfov = 2·atan(18/lens)` (sensor 36 mm theo cạnh rộng),
  `fov = 2·atan(tan(hfov/2)·H/W)`.

## Vật liệu và màu

- Màu sRGB trong bảng `MATERIALS` → `new Color().setRGB(r,g,b, SRGBColorSpace)`;
  `renderer.outputColorSpace = SRGBColorSpace`, `toneMapping = AgXToneMapping` (giống Blender 4.x) → màu
  khớp bản Cycles khá sát.
- Bevel = `RoundedBoxGeometry(w,h,d, 3, radius)` — bắt sáng mép như bevel modifier.
- Emission: `emissive = color, emissiveIntensity = n`.

## Đèn và bóng

- Area light Cycles ≈ `SpotLight` góc 55°, penumbra .6, decay 1.2 + `HemisphereLight` (trời xanh ngọc /
  sàn be) thay cho ánh sáng dội mà three.js không tính. Đèn `distance 0`.
- **Bóng**: `PCFShadowMap` + `shadow.radius 5`, `bias −.0004`, `normalBias .02`. `VSMShadowMap` cho bóng mềm
  hơn nhưng **sọc chéo trên tường** và nặng; `PCFSoftShadowMap` đã bị bỏ ở r187. Thiếu `normalBias` → acne.
- Mọi mesh `castShadow = receiveShadow = true`; SkinnedMesh thêm `frustumCulled = false` (bone đi xa bị cull).

## Camera và neo

- `shotFace(cam, anchor, {offset, lens, dist, side, low, aside})`: camera = target + normalize(side)·dist;
  `lookAt(target)` rồi `lookAt(target + right·dist·aside + up·dist·low)` để chủ thể dạt sang/tụt xuống trong
  khung. **Phải `cam.updateMatrixWorld(true)` sau khi đặt** nếu dùng `project()` trước lúc render — không thì
  bbox bong bóng tính bằng ma trận cũ (đã dính: chữ bay lên đầu khung).
- Neo của nhân vật GLB: `Group` **tĩnh** tại vị trí đầu lúc nghỉ, xoay `rotation.y = yaw + 22°` (cùng hệ trục
  với đầu dev dựng code) — bong bóng là con của neo nên không rung theo đầu và vẫn nằm đúng phía.
- **Quy tắc người dùng: bong bóng chat không được nhảy/rung trong lúc nói** — chữ đứng yên mà bong bóng nhún
  theo nhân vật thì "xấu lắm". Neo của bong bóng (và camera) phải treo vào phần **không animate**: với mascot là
  `root` chứ không phải nhóm `body` đang nhún (đã dính lỗi này), với dev GLB là neo tĩnh ở đầu. Kiểm bằng cách
  chụp 2 khung cùng turn cách nhau ~6 khung và so vị trí bong bóng.
- **Bong bóng to hết mức mà vẫn nằm trọn trong khung** ở mọi shot (người dùng muốn hiện nhiều chữ): dev_talk
  scale 1,9, claude_talk 1,7, các shot explain 1,42–1,95; vùng chữ = 0,68 w × 0,62 h của bbox. Quá cỡ thì bbox
  tràn khung và chữ bị cắt mép (đã dính ở scale 2,1) — soát cả 4 shot sau mỗi lần đổi.
- Camera các shot tính một lần ở `init` (pose nghỉ), lưu `{pos, quat, fov}`; mỗi khung chỉ nội suy.

## Chữ và thẻ (DOM)

- Bong bóng: `screenBox(mesh)` chiếu 8 góc `Box3` → bbox pixel; div có `width = .64·w, height = .58·h`
  (hình chữ nhật nội tiếp ellipse), `display:flex; align-items:center`. Chữ bọc trong **một `<span>`** —
  nhiều node con trong flex sẽ xếp thành cột (đã dính). Mỗi từ `<span class="w" data-t="giây">`,
  `visibility:hidden` → `.on` khi `t ≤ now`: không reflow. Cỡ chữ: thử từ 5 %H xuống 3 %H đến khi
  `scrollHeight/Width` vừa; không vừa → tách theo câu thành chunk, chunk hiện khi từ đầu của nó được nói.
- Thẻ: div `.card` sẵn trong `index.html`, hiện theo `card_frames` (fade .25/.5/.75 ở 3 khung cuối cú lia
  vào và 3 khung đầu cú lia ra, kèm `translateY`). Màu accent theo người nói qua CSS variable `--accent`.
- Font Segoe UI có sẵn Windows đủ dấu Việt; máy khác cần đổi `font-family` hoặc nhúng font.

## Chrome headless / Playwright

- `chromium.launch({channel: 'chrome'})` dùng Chrome đã cài, không tải browser (mạng công ty).
- Args: `--allow-file-access-from-files` (GLTFLoader `fetch` file .glb cạnh index.html — thiếu là
  `ERR_FILE_NOT_FOUND`), `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader` (WebGL phần
  mềm, ổn định). `--gpu` trên máy không có GPU rời rơi vào "Microsoft Basic Render Driver" chậm hơn.
- `page.evaluate` chỉ truyền JSON: `Vector3` phải truyền mảng rồi dựng lại trong trang.
- Module ES từ `file://` bị CORS → bundle bằng esbuild (`npm run build`, 150 ms) thành IIFE.
- Log trong trang: `page.on('console')`, `page.on('pageerror')` — bật luôn, lỗi JS trong trang không tự nổi lên Node.

## Node

- Đọc wav bằng `Buffer` (duyệt chunk `fmt `/`data`, Int16 LE) — không cần thư viện.
- Chạy `node shoot.mjs` **từ thư mục threejs** (đường dẫn `../../output` tương đối); tool Bash đổi cwd theo
  `cd` nên lệnh sau phải `cd` về.
