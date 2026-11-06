/**
 * Vercel Serverless Function: /api/stream/[id].js
 * Nhiệm vụ:
 * 1. Nhận movie ID từ URL (/api/stream/{id}) và tuỳ chọn ?type=thumb (nếu lấy ảnh poster)
 * 2. Truy vấn Supabase REST API để lấy file_id / thumbnail_file_id
 * 3. Gọi Telegram Bot API getFile để lấy file_path tạm thời
 * 4. Redirect 302 trực tiếp đến link tải/stream của Telegram Server
 */

export default async function handler(req, res) {
  // Hỗ trợ CORS cho trình duyệt
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  const { id, type } = req.query;

  if (!id) {
    return res.status(400).json({
      error: "Thiếu tham số id phim.",
    });
  }

  const SUPABASE_URL = (process.env.SUPABASE_URL || "").replace(/\/+$/, "");
  const SUPABASE_KEY =
    process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_ANON_KEY || "";
  const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || "";

  if (!SUPABASE_URL || !SUPABASE_KEY || !TELEGRAM_BOT_TOKEN) {
    return res.status(500).json({
      error:
        "Server chưa cấu hình đầy đủ biến môi trường (SUPABASE_URL, SUPABASE_ANON_KEY, TELEGRAM_BOT_TOKEN).",
    });
  }

  try {
    // Bước 1: Query Supabase lấy file_id và thumbnail_file_id theo id phim
    const supabaseEndpoint = `${SUPABASE_URL}/rest/v1/movies?id=eq.${encodeURIComponent(
      id
    )}&select=id,title,file_id,thumbnail_file_id&limit=1`;

    const dbResponse = await fetch(supabaseEndpoint, {
      method: "GET",
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${SUPABASE_KEY}`,
        Accept: "application/json",
      },
    });

    if (!dbResponse.ok) {
      const errText = await dbResponse.text();
      return res.status(502).json({
        error: "Lỗi khi truy vấn Supabase",
        details: errText,
      });
    }

    const movies = await dbResponse.json();
    if (!Array.isArray(movies) || movies.length === 0) {
      return res.status(404).json({
        error: "Không tìm thấy phim với ID này trong cơ sở dữ liệu.",
      });
    }

    const movie = movies[0];
    const targetFileId =
      type === "thumb" ? movie.thumbnail_file_id : movie.file_id;

    if (!targetFileId) {
      return res.status(404).json({
        error:
          type === "thumb"
            ? "Phim này không có thumbnail_file_id."
            : "Phim này không có file_id hợp lệ.",
      });
    }

    // Bước 2: Gọi Telegram getFile API để lấy file_path
    const tgApiUrl = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getFile?file_id=${encodeURIComponent(
      targetFileId
    )}`;

    const tgResponse = await fetch(tgApiUrl);
    const tgData = await tgResponse.json();

    if (!tgResponse.ok || !tgData.ok || !tgData.result?.file_path) {
      return res.status(502).json({
        error: "Không thể lấy đường dẫn stream từ Telegram API.",
        telegram_description:
          tgData.description ||
          "Lưu ý: Telegram Bot API tiêu chuẩn giới hạn getFile tối đa 20MB. Với file lớn hơn, hãy đọc README.md để cấu hình Local Bot API hoặc nén chuẩn MP4 720p.",
      });
    }

    const filePath = tgData.result.file_path;
    const directTelegramStreamUrl = `https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${filePath}`;

    // Cache nhẹ 10 phút vì link Telegram getFile có hiệu lực tối thiểu 1 giờ
    res.setHeader("Cache-Control", "public, max-age=600, s-maxage=600");

    // Bước 3: Redirect 302 đến link stream của Telegram để trình duyệt tự xử lý Range Request
    return res.redirect(302, directTelegramStreamUrl);
  } catch (error) {
    console.error("Stream proxy error:", error);
    return res.status(500).json({
      error: "Lỗi nội bộ tại Vercel Stream Proxy.",
      message: error instanceof Error ? error.message : String(error),
    });
  }
}
