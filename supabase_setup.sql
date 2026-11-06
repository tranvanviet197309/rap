-- =============================================================================
-- CINEVAULT: SUPABASE DATABASE SETUP (100% FREE TIER)
-- Hướng dẫn: Copy toàn bộ nội dung file này vào Supabase Dashboard -> SQL Editor -> Run
-- =============================================================================

-- 1. Kích hoạt extension tạo UUID tự động
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Tạo bảng lưu trữ thông tin phim (movies)
CREATE TABLE IF NOT EXISTS public.movies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    genre TEXT NOT NULL DEFAULT 'Khác',
    file_id TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'video' CHECK (file_type IN ('video', 'document')),
    thumbnail_file_id TEXT,
    duration INTEGER DEFAULT 0,
    file_size BIGINT DEFAULT 0,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    added_by TEXT NOT NULL
);

-- 3. Tạo các Index để tối ưu tốc độ truy vấn, lọc thể loại và tìm kiếm
CREATE INDEX IF NOT EXISTS idx_movies_added_at ON public.movies (added_at DESC);
CREATE INDEX IF NOT EXISTS idx_movies_genre ON public.movies (genre);
CREATE INDEX IF NOT EXISTS idx_movies_title_search ON public.movies USING gin (to_tsvector('simple', title));

-- 4. Bật Row Level Security (RLS) để bảo mật dữ liệu
ALTER TABLE public.movies ENABLE ROW LEVEL SECURITY;

-- 5. Xoá policy cũ nếu chạy lại script nhiều lần
DROP POLICY IF EXISTS "Cho phép tất cả mọi người xem danh sách phim" ON public.movies;
DROP POLICY IF EXISTS "Cho phép Bot hoặc Service Role thêm phim" ON public.movies;
DROP POLICY IF EXISTS "Cho phép Bot hoặc Service Role cập nhật phim" ON public.movies;
DROP POLICY IF EXISTS "Cho phép Bot hoặc Service Role xoá phim" ON public.movies;

-- 6. Tạo RLS Policies:
-- Policy 1: Frontend (dùng SUPABASE_ANON_KEY) được phép đọc (SELECT) danh sách phim công khai
CREATE POLICY "Cho phép tất cả mọi người xem danh sách phim"
    ON public.movies
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Policy 2: Cho phép thêm/sửa/xoá từ Bot (dùng SUPABASE_SERVICE_KEY hoặc anon khi bật chế độ cá nhân)
CREATE POLICY "Cho phép Bot hoặc Service Role thêm phim"
    ON public.movies
    FOR INSERT
    TO anon, authenticated, service_role
    WITH CHECK (true);

CREATE POLICY "Cho phép Bot hoặc Service Role cập nhật phim"
    ON public.movies
    FOR UPDATE
    TO anon, authenticated, service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Cho phép Bot hoặc Service Role xoá phim"
    ON public.movies
    FOR DELETE
    TO anon, authenticated, service_role
    USING (true);

-- 7. Ghi chú hoàn tất
COMMENT ON TABLE public.movies IS 'Bảng lưu trữ metadata phim từ Telegram Bot cho hệ thống Rạp Chiếu Phim Cá Nhân';
