import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { createServer as createViteServer } from 'vite';
import {
  buildSupabaseMovieLookupUrl,
  buildTelegramFileStreamUrl,
} from './src/utils/cinemaLogic.ts';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ORDERED_PROJECT_FILES = [
  'supabase_setup.sql',
  'bot.py',
  'requirements.txt',
  'render.yaml',
  'api/stream/[id].js',
  'vercel.json',
  'index.html',
  'movie.html',
  'style.css',
  '.env.example',
  'README.md',
];

// Minimal valid fMP4 / MP4 header bytes for local offline preview fallback
const MINIMAL_MP4_BASE64 =
  'AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAAu1tZGF0AAACrgYF//+q3EXpvebZSLeWLNgg2SPu73gyNjQgLSBjb3JlIDE0OCByMjc5NSBlY2FhOWI4IC0gSC4yNjQvTVBFRy00 AVCIGNvZGVjIC0gQ29weXJpZ2h0IDIwMDMtMjAxNyAtIGh0dHA6Ly93d3cudmlkZW9sYW4ub3JnL3gyNjQuaHRtbCAtIG9wdGlvbnM6IGNhYmFjPTEgcmVmPTMgZGVibG9jaz0xOjA6MCBhbmFseXNlPTB4MzoweDExMyBtZT1oZXggc3VibWU9NyBwcyk9MSBwc3lfcmQ9MS4wMDowLjAwIG1peGVkX3JlZj0xIG1lX3JhbmdlPTE2IGNocm9tYV9tZT0xIHRyZWxsaXM9MSA4eDhkY3Q9MSBjcW09MCBkZWFkem9uZT0yMSwxMSBmYXN0X3Bza2lwPTEgY2hyb21hX3FwX29mZnNldD0tMiB0aHJlYWRzPTEgbG9va2FoZWFkX3RocmVhZHM9MSBzbGljZWRfdGhyZWFkcz0wIG5yPTAgZGVjaW1hdGU9MSBpbnRlcmxhY2VkPTAgYmx1cmF5X2NvbXBhdD0wIGNvbnN0cmFpbmVkX2ludHJhPTAgYmZyYW1lcz0zIGJfHlyaW1pZD0yIGJfYWRhcHQ9MSBiX2JpYXM9MCBkaXJlY3Q9MSB3ZWlnaHRiPTEgb3Blbl9nb3A9MCB3ZWlnaHRwPTIga2V5aW50PTI1MCBrZXlpbnRfbWluPTI1IHNjZW5lY3V0PTQwIGluY3JlbWVudGFsX3NsaWNlPTAgcmNfZ29wPTAgcmNfbG9va2FoZWFkPTQwIHJjPWNyZiBtYnRyZWU9MSBjcmY9MjMuMCBxY29tcD0wLjYwIHFwbWluPTAgcXBtYXg9NjkgcXBzdGVwPTQgdnZ2X21heHJhdGU9MCB2YnZfYnVmc2l6ZT0wIGNyZl9tYXg9MCBub2lzZV9yZWR1Y3Rpb249MCB0aW1lY29kZT0wAAAB7G1vb3YAAABsbXZoZAAAAAAAAAAAAAAAAKetBlgAAKetBlgAAAPoAAAD6AABAAABAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAABdG10cmsAAABcdGtoZAAAAAdwAAL1gAAAAKetBlgAAAABAAAAAAA5gAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAEAAAAAAygAAAMoAAAAAAAkZXR0cwAAABxlbHN0AAAAAAAAAAEAAAA5gAAAAAAAAAABAAABQ21kaWEAAAAgbWRoZAAAAAAAAAAAAAAAAKetBlgAAKetBlgAAArwAAAAXEAAAAAA1WhkbHIAAAAAAAAAAHZpZGUAAAAAAAAAAAAAAAAAAABWaWRlb0hhbmRsZXIAAAADlG1pbmYAAAAUdm1oZAAAAAEAAAAAAAAAAAAAACRkaW5mAAAAHGRyZWYAAAAAAAAAAQAAAAx1cmwgAAAAAQAAA1RzdGJsAAAArHN0c2QAAAAAAAAAAQAAAJxhdmMxAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAygAAAMoAAABIAAAASAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGP//AAAAMmF2Y0MBZAAe/+EAGGdkAB6s2UCQEmhAAAADAEAAAA8DxYtlgAEABmjr489wA==';

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 3000;

  app.get('/api/config', (_req, res) => {
    const rawUrl = process.env.SUPABASE_URL || '';
    const rawAnon = process.env.SUPABASE_ANON_KEY || '';
    const isValidUrl =
      rawUrl.startsWith('https://') && !rawUrl.includes('your-project-id');
    const isValidAnon =
      rawAnon.length > 20 && !rawAnon.includes('your_anon_public_key');

    res.json({
      supabaseUrl: isValidUrl ? rawUrl : '',
      supabaseAnonKey: isValidAnon ? rawAnon : '',
    });
  });

  app.get('/api/project-files', (_req, res) => {
    const files = ORDERED_PROJECT_FILES.map((relPath) => {
      const fullPath = path.join(__dirname, relPath);
      let content = '';
      try {
        content = fs.readFileSync(fullPath, 'utf-8');
      } catch (err) {
        content = `Không thể đọc file: ${relPath}`;
      }
      return {
        path: relPath,
        content,
      };
    });
    res.json({ files });
  });

  app.get('/api/demo-stream.mp4', (_req, res) => {
    const buffer = Buffer.from(MINIMAL_MP4_BASE64, 'base64');
    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', buffer.length);
    res.setHeader('Accept-Ranges', 'bytes');
    res.status(200).send(buffer);
  });

  // Endpoint tương đương hệt với Vercel Serverless Function /api/stream/[id].js
  app.get('/api/stream/:id', async (req, res) => {
    const { id } = req.params;
    const { type } = req.query;

    const supabaseUrl = (process.env.SUPABASE_URL || '').trim();
    const supabaseKey = (
      process.env.SUPABASE_SERVICE_KEY ||
      process.env.SUPABASE_ANON_KEY ||
      ''
    ).trim();
    const telegramBotToken = (process.env.TELEGRAM_BOT_TOKEN || '').trim();

    const hasRealCredentials =
      supabaseUrl.startsWith('https://') &&
      !supabaseUrl.includes('your-project-id') &&
      supabaseKey.length > 20 &&
      telegramBotToken.length > 15 &&
      !telegramBotToken.includes('your_telegram_bot_token');

    if (!hasRealCredentials) {
      if (type === 'thumb') {
        return res.redirect(
          302,
          '/src/assets/images/poster_crimson_horizon_1793972222936.jpg'
        );
      }
      // Thực hiện chuẩn 302 Redirect sang luồng video MP4
      return res.redirect(302, '/api/demo-stream.mp4');
    }

    try {
      const lookupUrl = buildSupabaseMovieLookupUrl(supabaseUrl, id);
      const dbResp = await fetch(lookupUrl, {
        headers: {
          apikey: supabaseKey,
          Authorization: `Bearer ${supabaseKey}`,
          Accept: 'application/json',
        },
      });

      if (!dbResp.ok) {
        return res.status(502).json({ error: 'Lỗi khi truy vấn Supabase.' });
      }

      const rows = (await dbResp.json()) as Array<{
        file_id?: string;
        thumbnail_file_id?: string;
      }>;
      if (!Array.isArray(rows) || rows.length === 0) {
        return res.status(404).json({ error: 'Không tìm thấy phim.' });
      }

      const targetFileId =
        type === 'thumb' ? rows[0].thumbnail_file_id : rows[0].file_id;
      if (!targetFileId) {
        return res.status(404).json({ error: 'Phim chưa có file_id.' });
      }

      const tgResp = await fetch(
        `https://api.telegram.org/bot${telegramBotToken}/getFile?file_id=${encodeURIComponent(
          targetFileId
        )}`
      );
      const tgJson = (await tgResp.json()) as {
        ok?: boolean;
        result?: { file_path?: string };
        description?: string;
      };

      if (!tgResp.ok || !tgJson.ok || !tgJson.result?.file_path) {
        return res.status(502).json({
          error: 'Không lấy được link từ Telegram getFile API.',
          details: tgJson.description,
        });
      }

      const streamUrl = buildTelegramFileStreamUrl(
        telegramBotToken,
        tgJson.result.file_path
      );
      return res.redirect(302, streamUrl);
    } catch (error) {
      return res.status(500).json({
        error: 'Lỗi nội bộ tại Stream Proxy.',
        message: error instanceof Error ? error.message : String(error),
      });
    }
  });

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'mpa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`CineVault server running at http://localhost:${PORT}`);
  });
}

startServer();
