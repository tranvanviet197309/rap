import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Đọc biến môi trường từ file .env
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("CineVaultBot")

# Biến môi trường bắt buộc
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    or os.getenv("SUPABASE_ANON_KEY", "").strip()
)
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://my-cinema.vercel.app").strip().rstrip("/")
ALLOWED_USER_IDS_RAW = os.getenv("ALLOWED_USER_IDS", "").strip()
PORT = int(os.environ.get("PORT", "10000"))

# Danh sách User ID được phép thêm/xoá phim (nếu để trống thì ai cũng dùng được)
ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in ALLOWED_USER_IDS_RAW.split(",")
    if uid.strip().isdigit()
]

# Các trạng thái trong ConversationHandler khi upload phim
ASK_TITLE, ASK_GENRE, ASK_THUMBNAIL = range(3)

# Danh sách thể loại hiển thị trên Inline Keyboard
GENRES = [
    "Hành động",
    "Khoa học viễn tưởng",
    "Kinh dị",
    "Tình cảm",
    "Hoạt hình",
    "Tâm lý",
    "Hài hước",
    "Tài liệu",
    "Khác",
]


def is_authorized(user_id: int) -> bool:
    """Kiểm tra quyền sử dụng Bot nếu ALLOWED_USER_IDS được cấu hình."""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


def supabase_headers() -> Dict[str, str]:
    """Header chuẩn để gọi Supabase REST API (PostgREST)."""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def format_size(num_bytes: int) -> str:
    """Chuyển đổi dung lượng byte sang định dạng dễ đọc (MB/GB)."""
    if not num_bytes or num_bytes <= 0:
        return "Không rõ"
    mb = num_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def format_duration(seconds: int) -> str:
    """Chuyển đổi thời lượng giây sang định dạng giờ:phút:giây."""
    if not seconds or seconds <= 0:
        return "Không rõ"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"


def extract_media_info(message: Message) -> Optional[Dict[str, Any]]:
    """Trích xuất thông tin video hoặc file document video từ tin nhắn Telegram."""
    if message.video:
        video = message.video
        default_title = (
            message.caption
            or video.file_name
            or f"Phim mới {datetime.now().strftime('%d/%m %H:%M')}"
        )
        # Lấy ảnh thumbnail có sẵn của video nếu có
        thumb_id = video.thumbnail.file_id if getattr(video, "thumbnail", None) else None
        return {
            "file_id": video.file_id,
            "file_type": "video",
            "default_title": os.path.splitext(default_title)[0],
            "duration": video.duration or 0,
            "file_size": video.file_size or 0,
            "thumbnail_file_id": thumb_id,
        }

    if message.document:
        doc = message.document
        mime = (doc.mime_type or "").lower()
        file_name = doc.file_name or ""
        video_exts = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v")
        if mime.startswith("video/") or file_name.lower().endswith(video_exts):
            default_title = (
                message.caption
                or file_name
                or f"Phim mới {datetime.now().strftime('%d/%m %H:%M')}"
            )
            thumb_id = doc.thumbnail.file_id if getattr(doc, "thumbnail", None) else None
            return {
                "file_id": doc.file_id,
                "file_type": "document",
                "default_title": os.path.splitext(default_title)[0],
                "duration": 0,
                "file_size": doc.file_size or 0,
                "thumbnail_file_id": thumb_id,
            }

    return None


def build_genre_keyboard() -> InlineKeyboardMarkup:
    """Tạo bảng nút bấm Inline Keyboard chọn thể loại phim."""
    keyboard = []
    row = []
    for genre in GENRES:
        row.append(InlineKeyboardButton(genre, callback_data=f"genre:{genre}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /start và hướng dẫn sử dụng."""
    user = update.effective_user
    welcome_text = (
        f"🎬 *Xin chào {user.first_name}! Chào mừng đến với Rạp Chiếu Phim Cá Nhân.*\n\n"
        "📌 *Cách thêm phim mới:*\n"
        "Chỉ cần gửi trực tiếp hoặc *Forward* bất kỳ video / file phim nào vào cuộc trò chuyện này.\n\n"
        "🛠 *Các lệnh quản lý:*\n"
        "• `/list` — Xem 10 phim mới nhất\n"
        "• `/search <từ khoá>` — Tìm kiếm phim theo tên\n"
        "• `/delete <id>` — Xoá phim khỏi hệ thống\n"
        "• `/cancel` — Huỷ thao tác đang thực hiện\n\n"
        f"🌐 *Trang chủ rạp phim:* {WEB_APP_URL}"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bước 1: Nhận video hoặc document gửi thẳng / forward từ người dùng."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("⛔ Bạn không có quyền thêm phim vào hệ thống này.")
        return ConversationHandler.END

    media_info = extract_media_info(update.message)
    if not media_info:
        await update.message.reply_text(
            "⚠️ File này không phải định dạng video hợp lệ (.mp4, .mkv, .webm, .mov)."
        )
        return ConversationHandler.END

    context.user_data["pending_movie"] = {
        **media_info,
        "added_by": user.username or user.full_name or str(user.id),
    }

    skip_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Giữ tên mặc định", callback_data="skip_title")]]
    )

    await update.message.reply_text(
        f"✅ Đã nhận file phim!\n"
        f"📄 *Tên mặc định:* `{media_info['default_title']}`\n"
        f"📦 *Dung lượng:* {format_size(media_info['file_size'])}\n\n"
        f"👉 Hãy nhập *Tên phim* bạn muốn hiển thị, hoặc bấm nút bên dưới để dùng tên mặc định:",
        parse_mode="Markdown",
        reply_markup=skip_keyboard,
    )
    return ASK_TITLE


async def receive_title_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bước 2A: Người dùng nhập tên phim bằng văn bản."""
    title = update.message.text.strip()
    if title.lower() == "/skip":
        title = context.user_data["pending_movie"]["default_title"]

    context.user_data["pending_movie"]["title"] = title
    await update.message.reply_text(
        f"🏷 Tên phim: *{title}*\n\n👉 Hãy chọn *Thể loại phim* bên dưới:",
        parse_mode="Markdown",
        reply_markup=build_genre_keyboard(),
    )
    return ASK_GENRE


async def skip_title_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bước 2B: Người dùng bấm nút 'Giữ tên mặc định'."""
    query = update.callback_query
    await query.answer()

    default_title = context.user_data["pending_movie"]["default_title"]
    context.user_data["pending_movie"]["title"] = default_title

    await query.edit_message_text(
        f"🏷 Tên phim: *{default_title}*\n\n👉 Hãy chọn *Thể loại phim* bên dưới:",
        parse_mode="Markdown",
        reply_markup=build_genre_keyboard(),
    )
    return ASK_GENRE


async def receive_genre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bước 3: Nhận thể loại từ Inline Keyboard và hỏi ảnh Thumbnail."""
    query = update.callback_query
    await query.answer()

    genre = query.data.replace("genre:", "")
    context.user_data["pending_movie"]["genre"] = genre

    skip_thumb_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Bỏ qua ảnh bìa (Lưu ngay)", callback_data="skip_thumb")]]
    )

    await query.edit_message_text(
        f"🎭 Thể loại: *{genre}*\n\n"
        "🖼 Bạn có muốn gửi thêm *Ảnh bìa (Poster/Thumbnail)* cho phim không?\n"
        "• Gửi 1 bức ảnh ngay bây giờ để làm poster.\n"
        "• Hoặc bấm *Bỏ qua ảnh bìa* để lưu phim ngay lập tức.",
        parse_mode="Markdown",
        reply_markup=skip_thumb_kb,
    )
    return ASK_THUMBNAIL


async def receive_thumbnail_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bước 4A: Người dùng gửi ảnh làm thumbnail."""
    photos = update.message.photo
    if photos:
        # Lấy bức ảnh có độ phân giải cao nhất (phần tử cuối cùng)
        best_photo = photos[-1]
        context.user_data["pending_movie"]["thumbnail_file_id"] = best_photo.file_id

    return await save_movie_to_supabase(update, context, is_callback=False)


async def skip_thumbnail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bước 4B: Người dùng bỏ qua gửi ảnh thumbnail riêng."""
    query = update.callback_query
    await query.answer()
    return await save_movie_to_supabase(update, context, is_callback=True)


async def save_movie_to_supabase(
    update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool
) -> int:
    """Lưu thông tin phim vào bảng movies trên Supabase và trả về link xem."""
    movie_data = context.user_data.get("pending_movie")
    if not movie_data:
        msg = "⚠️ Không tìm thấy dữ liệu phim tạm. Vui lòng gửi lại video."
        if is_callback:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return ConversationHandler.END

    payload = {
        "title": movie_data["title"],
        "genre": movie_data.get("genre", "Khác"),
        "file_id": movie_data["file_id"],
        "file_type": movie_data["file_type"],
        "thumbnail_file_id": movie_data.get("thumbnail_file_id"),
        "duration": movie_data.get("duration", 0),
        "file_size": movie_data.get("file_size", 0),
        "added_at": datetime.now(timezone.utc).isoformat(),
        "added_by": movie_data.get("added_by", "TelegramUser"),
    }

    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/movies",
            headers=supabase_headers(),
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        saved_rows = response.json()
        movie_record = saved_rows[0] if isinstance(saved_rows, list) and saved_rows else payload
        movie_id = movie_record.get("id", "unknown")

        watch_link = f"{WEB_APP_URL}/movie.html?id={movie_id}"
        result_text = (
            "🎉 *ĐÃ LƯU PHIM THÀNH CÔNG!*\n\n"
            f"🎬 *Tên phim:* {movie_record.get('title')}\n"
            f"🎭 *Thể loại:* {movie_record.get('genre')}\n"
            f"⏱ *Thời lượng:* {format_duration(movie_record.get('duration', 0))}\n"
            f"📦 *Dung lượng:* {format_size(movie_record.get('file_size', 0))}\n"
            f"🆔 *ID:* `{movie_id}`\n\n"
            f"🍿 *Link xem trực tiếp:*\n{watch_link}"
        )

        watch_kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Xem Phim Ngay", url=watch_link)]]
        )

        if is_callback:
            await update.callback_query.edit_message_text(
                result_text, parse_mode="Markdown", reply_markup=watch_kb
            )
        else:
            await update.message.reply_text(
                result_text, parse_mode="Markdown", reply_markup=watch_kb
            )
    except Exception as exc:
        logger.error("Lỗi khi lưu vào Supabase: %s", exc)
        err_msg = f"❌ Lỗi khi lưu vào Supabase: `{str(exc)}`"
        if is_callback:
            await update.callback_query.edit_message_text(err_msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(err_msg, parse_mode="Markdown")
    finally:
        context.user_data.pop("pending_movie", None)

    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Huỷ quy trình thêm phim hiện tại."""
    context.user_data.pop("pending_movie", None)
    await update.message.reply_text("🛑 Đã huỷ thao tác thêm phim hiện tại.")
    return ConversationHandler.END


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /list: Hiển thị danh sách 10 phim mới nhất."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/movies?select=id,title,genre,file_size,added_at&order=added_at.desc&limit=10",
            headers=supabase_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        movies = resp.json()

        if not movies:
            await update.message.reply_text("📭 Kho phim hiện đang trống. Hãy gửi video để thêm phim!")
            return

        lines = ["🍿 *DANH SÁCH 10 PHIM MỚI NHẤT:*\n"]
        for idx, m in enumerate(movies, start=1):
            watch_url = f"{WEB_APP_URL}/movie.html?id={m['id']}"
            lines.append(
                f"{idx}. *{m['title']}* ({m['genre']} • {format_size(m.get('file_size', 0))})\n"
                f"   🆔 `{m['id']}`\n"
                f"   🔗 [Xem phim]({watch_url})"
            )

        await update.message.reply_text(
            "\n\n".join(lines),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.error("Lỗi khi lấy danh sách phim: %s", exc)
        await update.message.reply_text(f"❌ Không thể tải danh sách phim: {exc}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /search {từ khoá}: Tìm phim theo tên."""
    if not context.args:
        await update.message.reply_text("🔍 Cú pháp: `/search <từ khoá tên phim>`", parse_mode="Markdown")
        return

    keyword = " ".join(context.args).strip()
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/movies",
            params={
                "select": "id,title,genre,file_size",
                "title": f"ilike.*{keyword}*",
                "order": "added_at.desc",
                "limit": "10",
            },
            headers=supabase_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        movies = resp.json()

        if not movies:
            await update.message.reply_text(f"🔍 Không tìm thấy phim nào khớp với từ khoá: *{keyword}*", parse_mode="Markdown")
            return

        lines = [f"🔎 *KẾT QUẢ TÌM KIẾM CHO:* `{keyword}`\n"]
        for idx, m in enumerate(movies, start=1):
            watch_url = f"{WEB_APP_URL}/movie.html?id={m['id']}"
            lines.append(
                f"{idx}. *{m['title']}* [{m['genre']}]\n"
                f"   🆔 `{m['id']}`\n"
                f"   🔗 [Xem ngay]({watch_url})"
            )

        await update.message.reply_text(
            "\n\n".join(lines),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.error("Lỗi khi tìm kiếm phim: %s", exc)
        await update.message.reply_text(f"❌ Lỗi tìm kiếm: {exc}")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /delete {id}: Xoá phim theo UUID."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("⛔ Bạn không có quyền xoá phim.")
        return

    if not context.args:
        await update.message.reply_text("🗑 Cú pháp: `/delete <id_phim>`", parse_mode="Markdown")
        return

    movie_id = context.args[0].strip()
    try:
        resp = requests.delete(
            f"{SUPABASE_URL}/rest/v1/movies",
            params={"id": f"eq.{movie_id}"},
            headers=supabase_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        deleted = resp.json()

        if not deleted:
            await update.message.reply_text(f"⚠️ Không tìm thấy phim có ID: `{movie_id}`", parse_mode="Markdown")
            return

        deleted_title = deleted[0].get("title", movie_id)
        await update.message.reply_text(
            f"🗑 Đã xoá phim *{deleted_title}* (`{movie_id}`) khỏi rạp chiếu phim!",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Lỗi khi xoá phim: %s", exc)
        await update.message.reply_text(f"❌ Không thể xoá phim: {exc}")


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP Server nhỏ giúp Render Web Service (Free tier) kiểm tra port mở."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","service":"cinevault-telegram-bot"}')

    def log_message(self, format, *args):
        return


def start_health_server() -> None:
    """Chạy HTTP healthcheck server trên background thread cho Render.com."""
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    logger.info("Health check server đang lắng nghe tại port %s", PORT)
    server.serve_forever()


def main() -> None:
    """Khởi chạy Bot Telegram và Health Check Server."""
    if not TELEGRAM_BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Thiếu biến môi trường bắt buộc! Vui lòng kiểm tra TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY trong file .env"
        )

    # Khởi động HTTP Server phụ để Render Free Web Service không bị timeout port
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.VIDEO | filters.Document.ALL, receive_video),
        ],
        states={
            ASK_TITLE: [
                CallbackQueryHandler(skip_title_callback, pattern="^skip_title$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title_text),
                CommandHandler("skip", receive_title_text),
            ],
            ASK_GENRE: [
                CallbackQueryHandler(receive_genre_callback, pattern="^genre:"),
            ],
            ASK_THUMBNAIL: [
                MessageHandler(filters.PHOTO, receive_thumbnail_photo),
                CallbackQueryHandler(skip_thumbnail_callback, pattern="^skip_thumb$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(conv_handler)

    logger.info("🚀 CineVault Telegram Bot đã sẵn sàng nhận phim!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
