# Nguồn tài nguyên `input/skydive_meme`

| File | Nguồn | License |
|---|---|---|
| `bg_c130.jpg` | Wikimedia Commons, *Kentucky Airmen provide tactical airlift for RAFL26 formation flight (9765121)* — U.S. Air Force photo by Master Sgt. (103AW), C-130J ramp mở trên Phần Lan, 16/6/2026. Crop 3:4 vùng x 380–3398 của ảnh gốc 6048×4024, resize 1536×2048. https://commons.wikimedia.org/wiki/File:Kentcuky_Airmen_provide_tactical_airlift_for_RAFL26_formation_flight_(9765121).jpg | Public domain (tác phẩm của chính phủ liên bang Hoa Kỳ) |
| `audio/wind.wav`, `audio/explosion.wav` | Tổng hợp bằng ffmpeg (`reel25d/tools/make_sfx.py`) | Không có bản quyền bên thứ ba |
| `sprites/*.png` | Cắt từ reel tham chiếu (Facebook 1423487356641922, page Triều Roblox, cre JUNE 12) bằng `reel25d/tools/cut_sprites.py` theo `sprites.json` | **Meme có bản quyền — chỉ dùng nội bộ, không commit.** Tạo lại bằng lệnh trong `sprites.json`. |
| Nhân vật khối (dad, son, stranger), túi dù | Dựng từ primitive trong `reel25d/scene.js` | — |
| `sprites/backpack_kid.png` | Flickr, *Amazing Spiderman Backpack* của CHEJ (ảnh chụp sản phẩm), cắt nền bằng rembg (u2netp), chỉnh sáng/màu nhẹ. https://www.flickr.com/photos/30292698@N00/7845758172 — lưu ý hình in Spider-Man trên sản phẩm là nhân vật có bản quyền Marvel | Ảnh: CC BY-SA 2.0; **chỉ dùng nội bộ, không commit** |
| `sprites/face_smirk.png`, `sprites/face_kid.png` | Vẽ bằng Pillow (`reel25d/tools/draw_face.py`) | Không có bản quyền bên thứ ba |
| `sprites/face_doge_grin.png`, `sprites/face_kid_grin.png` | Ghép từ sprite meme + mặt vẽ bằng `reel25d/tools/compose_face.py` | Theo sprite meme gốc — chỉ dùng nội bộ |
