export interface MovieRecord {
  id: string;
  title: string;
  genre: string;
  file_id: string;
  file_type: 'video' | 'document';
  thumbnail_file_id: string | null;
  duration: number;
  file_size: number;
  added_at: string;
  added_by: string;
}

export function formatMovieDuration(seconds: number): string {
  const s = Number(seconds) || 0;
  if (s <= 0) return 'Chưa rõ thời lượng';
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}m`;
  }
  return `${minutes} phút`;
}

export function formatMovieFileSize(bytes: number): string {
  const b = Number(bytes) || 0;
  if (b <= 0) return 'Chưa rõ dung lượng';
  const mb = b / (1024 * 1024);
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`;
  }
  return `${mb.toFixed(0)} MB`;
}

export function filterAndSearchMovies(
  movies: MovieRecord[],
  selectedGenre: string,
  searchQuery: string
): MovieRecord[] {
  const normalizedGenre = (selectedGenre || 'ALL').trim().toLowerCase();
  const normalizedQuery = (searchQuery || '').trim().toLowerCase();

  return movies.filter((movie) => {
    const matchGenre =
      normalizedGenre === 'all' ||
      (movie.genre || '').toLowerCase() === normalizedGenre;

    if (!normalizedQuery) {
      return matchGenre;
    }

    const inTitle = (movie.title || '').toLowerCase().includes(normalizedQuery);
    const inGenre = (movie.genre || '').toLowerCase().includes(normalizedQuery);
    const inAuthor = (movie.added_by || '').toLowerCase().includes(normalizedQuery);
    return matchGenre && (inTitle || inGenre || inAuthor);
  });
}

export function buildTelegramFileStreamUrl(
  botToken: string,
  filePath: string
): string {
  const cleanToken = botToken.trim();
  const cleanPath = filePath.replace(/^\/+/, '');
  return `https://api.telegram.org/file/bot${cleanToken}/${cleanPath}`;
}

export function buildSupabaseMovieLookupUrl(
  supabaseUrl: string,
  movieId: string
): string {
  const baseUrl = supabaseUrl.trim().replace(/\/+$/, '');
  return `${baseUrl}/rest/v1/movies?id=eq.${encodeURIComponent(
    movieId
  )}&select=id,title,file_id,thumbnail_file_id&limit=1`;
}
