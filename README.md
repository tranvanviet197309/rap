# 🍿 CineVault — Hệ Thống Rạp Chiếu Phim Cá Nhân 100% MIỄN PHÍ

Hệ thống biến **Telegram** thành kho lưu trữ video không giới hạn dung lượng, **Supabase** làm cơ sở dữ liệu quản lý danh mục phim, **Render.com** chạy Bot Telegram tự động 24/7 và **Vercel** làm giao diện Web kiểu Netflix kèm Serverless Streaming Proxy.

---

## 🏗 Kiến trúc hoạt động

1. **Người dùng gửi hoặc Forward phim** (video hoặc file `.mp4`, `.mkv`) vào **Bot Telegram**.
2. **Bot Telegram (`bot.py`)** hỏi tên phim (có nút bỏ qua để lấy tên file gốc), hiển thị bảng nút bấm chọn **Thể loại** và hỏi **Ảnh bìa (Thumbnail)**.
3. **Bot lưu metadata** (`id`, `title`, `genre`, `file_id`, `thumbnail_file_id`, `duration`, `file_size`, `added_at`, `added_by`) vào **Supabase** và trả về đường dẫn xem phim: `https://my-cinema.vercel.app/movie.html?id={id}`.
4. **Trang web (`index.html`, `movie.html`)** gọi trực tiếp **Supabase REST API** để hiển thị poster, lọc thể loại, tìm kiếm phim.
5. Khi người dùng bấm **Xem Phim**, thẻ `<video>` gọi đến **Vercel Proxy (`/api/stream/[id].js`)** ➔ Proxy truy vấn `file_id` từ Supabase ➔ gọi Telegram `getFile` API ➔ trả về **HTTP 302 Redirect** sang link stream của Telegram để trình duyệt tự phát và tua phim mượt mà.

---

## 📂 Danh sách 11 File trong Hệ thống

1. `supabase_setup.sql` — Câu lệnh SQL tạo bảng `movies`, Index tìm kiếm nhanh và chính sách bảo mật RLS.
2. `bot.py` — Mã nguồn Python hoàn chỉnh của Bot Telegram (kèm HTTP Health Check để chạy miễn phí trên Render).
3. `requirements.txt` — Danh sách thư viện Python cần cài đặt.
4. `render.yaml` — Cấu hình tự động hoá triển khai (Blueprint) trên Render.com.
5. `api/stream/[id].js` — Serverless Function trên Vercel chuyển đổi `movie_id` thành luồng video Telegram.
6. `vercel.json` — Cấu hình định tuyến URL `/api/stream/:id` trên Vercel.
7. `index.html` — Trang chủ rạp phim giao diện chuẩn Netflix (Hero banner, bộ lọc thể loại, thanh tìm kiếm).
8. `movie.html` — Trang xem phim với trình phát HTML5 `<video>` và bảng thông số kỹ thuật.
9. `style.css` — Giao diện Dark Mode (`#0a0a0a`) + Đỏ Điện Ảnh (`#e50914`), tương thích hoàn hảo điện thoại & máy tính.
10. `.env.example` — Mẫu cấu hình tất cả biến môi trường.
11. `README.md` — Tài liệu hướng dẫn triển khai chi tiết từng bước từ A–Z.

---

## 🚀 HƯỚNG DẪN DEPLOY TỪ A–Z (Dành cho người không biết lập trình)

Bạn chỉ cần chuẩn bị:
- 1 tài khoản **Telegram**
- 1 tài khoản **GitHub** (miễn phí tại [github.com](https://github.com))
- 1 tài khoản **Supabase** (miễn phí tại [supabase.com](https://supabase.com))
- 1 tài khoản **Render** (miễn phí tại [render.com](https://render.com))
- 1 tài khoản **Vercel** (miễn phí tại [vercel.com](https://vercel.com))

---

### BƯỚC 1: Tạo Bot Telegram lấy `TELEGRAM_BOT_TOKEN` (2 phút)

1. Mở ứng dụng Telegram, tìm kiếm **`@BotFather`** (có dấu tích xanh) và bấm **Start**.
2. Gõ lệnh `/newbot` và gửi.
3. Nhập **Tên hiển thị** cho Bot (ví dụ: `Rạp Phim Cá Nhân`).
4. Nhập **Username** cho Bot, bắt buộc có đuôi `bot` (ví dụ: `my_cinevault_2026_bot`).
5. `@BotFather` sẽ trả về một đoạn mã dưới dòng chữ *Use this token to access the HTTP API:* có dạng:
   ```text
   7123456789:AAHxyz1234567890abcdefGHIJKLMN
   ```
   👉 **Lưu lại mã này**, đây chính là `TELEGRAM_BOT_TOKEN`.
6. *(Tuỳ chọn bảo mật)* Để chỉ mình bạn được phép thêm/xoá phim: tìm **`@userinfobot`** trên Telegram, bấm **Start**, nó sẽ báo `Id: 123456789`. Lưu số này làm `ALLOWED_USER_IDS`.

---

### BƯỚC 2: Khởi tạo Database trên Supabase (3 phút)

1. Truy cập [https://supabase.com](https://supabase.com) ➔ Đăng nhập ➔ Bấm **New Project**.
2. Điền tên Project (ví dụ: `cinevault`), đặt mật khẩu Database bất kỳ, chọn Region gần nhất (**Singapore / Southeast Asia**) ➔ Bấm **Create new project** (chờ khoảng 1 phút để hệ thống khởi tạo).
3. Nhìn thanh menu bên trái, bấm vào biểu tượng **SQL Editor** (hình ký hiệu `>_`) ➔ Bấm **+ New query**.
4. Mở file **`supabase_setup.sql`** trong bộ code này, **Copy toàn bộ nội dung** và dán vào ô SQL Editor trên Supabase ➔ Bấm nút **Run** (góc dưới bên phải).
5. Khi màn hình báo `Success. No rows returned`, bảng `movies` đã được tạo thành công!
6. Bây giờ lấy thông tin kết nối:
   - Nhìn menu trái, chọn **Project Settings** (biểu tượng bánh răng dưới cùng) ➔ chọn mục **API**.
   - Tại mục **Project URL**, bấm Copy ➔ Đây là `SUPABASE_URL` (ví dụ: `https://abcdefgh.supabase.co`).
   - Tại mục **Project API keys**:
     - Dòng `anon` `public`: Bấm Copy ➔ Đây là `SUPABASE_ANON_KEY`.
     - Dòng `service_role` `secret`: Bấm **Reveal** rồi Copy ➔ Đây là `SUPABASE_SERVICE_KEY`.

---

### BƯỚC 3: Đẩy bộ code lên GitHub (3 phút)

1. Đăng nhập vào [https://github.com](https://github.com), bấm dấu **`+`** ở góc phải trên cùng ➔ chọn **New repository**.
2. Đặt tên repository là `my-cinema`, chọn **Private** (Riêng tư) hoặc **Public** tuỳ ý ➔ Bấm **Create repository**.
3. Trước khi upload file **`index.html`** và **`movie.html`**, bạn mở 2 file này bằng trình soạn thảo bất kỳ (như Notepad) và điền `SUPABASE_URL` cùng `SUPABASE_ANON_KEY` vào 2 dòng đầu trong thẻ `<script>`:
   ```javascript
   const DEFAULT_SUPABASE_URL = "https://abcdefgh.supabase.co";
   const DEFAULT_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
   ```
   *(Hoặc sau khi mở trang web lên, bạn cũng có thể bấm nút **"Kết nối Supabase"** ngay trên thanh menu góc phải để dán 2 thông số này mà không cần sửa code!)*
4. Trên trang GitHub vừa tạo, bấm vào dòng chữ **uploading an existing file** ➔ Kéo thả toàn bộ các file và thư mục (`supabase_setup.sql`, `bot.py`, `requirements.txt`, `render.yaml`, `api/stream/[id].js`, `vercel.json`, `index.html`, `movie.html`, `style.css`, `.env.example`, `README.md`) vào ➔ Bấm **Commit changes**.

---

### BƯỚC 4: Deploy Web & Stream Proxy lên Vercel (3 phút)

1. Truy cập [https://vercel.com](https://vercel.com) và đăng nhập bằng tài khoản **GitHub** của bạn.
2. Tại màn hình chính, bấm **Add New...** ➔ chọn **Project**.
3. Tìm đến kho chứa `my-cinema` vừa tạo trên GitHub và bấm **Import**.
4. Tại mục **Environment Variables** (Biến môi trường), bạn lần lượt thêm 4 biến sau (nhập Key ở ô trái, Value ở ô phải rồi bấm **Add**):
   - `TELEGRAM_BOT_TOKEN` = *(Token lấy ở Bước 1)*
   - `SUPABASE_URL` = *(URL lấy ở Bước 2)*
   - `SUPABASE_ANON_KEY` = *(Anon Key lấy ở Bước 2)*
   - `SUPABASE_SERVICE_KEY` = *(Service Role Key lấy ở Bước 2)*
5. Bấm nút **Deploy** và chờ khoảng 30 giây.
6. Khi pháo hoa chúc mừng hiện ra, Vercel sẽ cấp cho bạn địa chỉ trang web (ví dụ: `https://my-cinema.vercel.app`). Hãy copy lại đường dẫn này làm `WEB_APP_URL`.

---

### BƯỚC 5: Deploy Bot Telegram lên Render.com (3 phút)

1. Truy cập [https://render.com](https://render.com) và đăng nhập bằng tài khoản **GitHub**.
2. Bấm nút **New +** (góc trên bên phải) ➔ chọn **Web Service**.
3. Chọn kết nối tới repository `my-cinema` của bạn và bấm **Connect**.
4. Điền các thông số cấu hình:
   - **Name**: `cinevault-bot`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: Chọn gói **Free** ($0/month).
5. Kéo xuống mục **Environment Variables**, bấm **Add Environment Variable** và điền 5 biến sau:
   - `TELEGRAM_BOT_TOKEN` = *(Token lấy ở Bước 1)*
   - `SUPABASE_URL` = *(URL lấy ở Bước 2)*
   - `SUPABASE_SERVICE_KEY` = *(Service Role Key lấy ở Bước 2)*
   - `WEB_APP_URL` = *(Link Vercel lấy ở Bước 4, ví dụ `https://my-cinema.vercel.app`, không có dấu `/` ở cuối)*
   - `ALLOWED_USER_IDS` = *(ID Telegram của bạn lấy ở Bước 1, hoặc để trống)*
6. Bấm **Create Web Service**. Chờ khoảng 2 phút cho đến khi dòng chữ **Live** màu xanh hiện lên.

---

## 🎬 Cách sử dụng hàng ngày

1. Mở Bot Telegram của bạn lên và gõ `/start`.
2. **Gửi thẳng một video** từ máy hoặc **Forward bất kỳ bộ phim nào** từ các kênh/nhóm Telegram khác vào Bot.
3. Bot sẽ hỏi:
   - **Tên phim**: Nhập tên bạn muốn hoặc bấm **⏭ Giữ tên mặc định**.
   - **Thể loại**: Chạm vào nút thể loại tương ứng trên màn hình (*Hành động, Khoa học viễn tưởng, Kinh dị, Tình cảm...*).
   - **Ảnh bìa (Thumbnail)**: Gửi 1 tấm ảnh poster hoặc bấm **⏭ Bỏ qua ảnh bìa (Lưu ngay)**.
4. Ngay lập tức, Bot trả về link xem phim trực tiếp:
   `https://my-cinema.vercel.app/movie.html?id=...`
5. Mở trang chủ `https://my-cinema.vercel.app` trên TV, iPad, điện thoại hoặc máy tính để thưởng thức như Netflix!

---

## 💡 Mẹo nhỏ để Bot chạy 24/7 và phát video mượt nhất

- **Giữ Render Free không bị ngủ đông**: Gói miễn phí của Render sẽ tạm nghỉ nếu sau 15 phút không có truy cập HTTP. Bạn có thể tạo tài khoản miễn phí tại [cron-job.org](https://cron-job.org) hoặc [UptimeRobot](https://uptimerobot.com) và cài đặt ping vào đường dẫn `.onrender.com` của Bot mỗi 10 phút — Bot sẽ thức 24/7 hoàn toàn miễn phí!
- **Định dạng video tương thích trình duyệt**: Trình duyệt web (Chrome, Safari, Edge) phát trực tiếp mượt nhất với định dạng **MP4 (H.264 + AAC)**.
- **Lưu ý giới hạn Telegram Bot API**: Bot API tiêu chuẩn của Telegram (`api.telegram.org`) cho phép Bot tải/stream qua `getFile` tối đa 20MB mỗi file. Để stream các bộ phim dài hàng GB, bạn có thể trỏ Bot sang [Telegram Bot API Server tự host](https://github.com/tdlib/telegram-bot-api) (nâng giới hạn lên **2000MB / 2GB** mỗi file) hoặc chia nhỏ tập phim.
