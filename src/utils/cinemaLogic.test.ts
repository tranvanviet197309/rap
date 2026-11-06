import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatMovieDuration,
  formatMovieFileSize,
  filterAndSearchMovies,
  buildTelegramFileStreamUrl,
  buildSupabaseMovieLookupUrl,
  type MovieRecord,
} from './cinemaLogic';

const sampleMovies: MovieRecord[] = [
  {
    id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    title: 'Bóng Đêm Sài Gòn: Giao Thức Cuối',
    genre: 'Hành động',
    file_id: 'file_1',
    file_type: 'video',
    thumbnail_file_id: null,
    duration: 8040,
    file_size: 1524713390,
    added_at: '2026-11-06T04:30:00.000Z',
    added_by: 'tranvanviet',
  },
  {
    id: '9c858901-8a57-4791-81fe-4c455b099bc9',
    title: 'Nhật Thực Đỏ Trên Hành Tinh Astraeus',
    genre: 'Khoa học viễn tưởng',
    file_id: 'file_2',
    file_type: 'video',
    thumbnail_file_id: 'thumb_2',
    duration: 2700,
    file_size: 524288000,
    added_at: '2026-11-05T19:15:00.000Z',
    added_by: 'cinema_curator',
  },
];

test('formatMovieDuration formats hours and minutes accurately', () => {
  assert.equal(formatMovieDuration(8040), '2h 14m');
  assert.equal(formatMovieDuration(2700), '45 phút');
  assert.equal(formatMovieDuration(0), 'Chưa rõ thời lượng');
});

test('formatMovieFileSize formats MB and GB accurately', () => {
  assert.equal(formatMovieFileSize(1524713390), '1.42 GB');
  assert.equal(formatMovieFileSize(524288000), '500 MB');
  assert.equal(formatMovieFileSize(0), 'Chưa rõ dung lượng');
});

test('filterAndSearchMovies filters by genre and search keyword', () => {
  const actionOnly = filterAndSearchMovies(sampleMovies, 'Hành động', '');
  assert.equal(actionOnly.length, 1);
  assert.equal(actionOnly[0].title, 'Bóng Đêm Sài Gòn: Giao Thức Cuối');

  const searchMatch = filterAndSearchMovies(sampleMovies, 'ALL', 'astraeus');
  assert.equal(searchMatch.length, 1);
  assert.equal(searchMatch[0].id, '9c858901-8a57-4791-81fe-4c455b099bc9');

  const emptyMatch = filterAndSearchMovies(sampleMovies, 'Kinh dị', '');
  assert.equal(emptyMatch.length, 0);
});

test('buildTelegramFileStreamUrl and buildSupabaseMovieLookupUrl construct clean URLs', () => {
  const tgUrl = buildTelegramFileStreamUrl('123:ABC', '/videos/file_01.mp4');
  assert.equal(
    tgUrl,
    'https://api.telegram.org/file/bot123:ABC/videos/file_01.mp4'
  );

  const sbUrl = buildSupabaseMovieLookupUrl(
    'https://xyz.supabase.co/',
    'f47ac10b-58cc-4372-a567-0e02b2c3d479'
  );
  assert.equal(
    sbUrl,
    'https://xyz.supabase.co/rest/v1/movies?id=eq.f47ac10b-58cc-4372-a567-0e02b2c3d479&select=id,title,file_id,thumbnail_file_id&limit=1'
  );
});
