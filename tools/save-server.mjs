// Static server that also accepts writes, for the three.js render rigs.
//
//   node tools/save-server.mjs [port]
//
// GET  /any/path        serves it from the repo root
// POST /save?name=x.png writes assets/3d/x.png (subdirectories are created)
//
// The rigs render in a real browser because they need WebGL and canvas 2D;
// this is the other half, so a rig can hand finished pixels back to disk.

import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, extname, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const port = Number(process.argv[2]) || 8124;

const TYPES = {
  '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript',
  '.css': 'text/css', '.json': 'application/json', '.png': 'image/png',
  '.webp': 'image/webp', '.webm': 'video/webm', '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml', '.mp4': 'video/mp4',
};

const BACKSLASH = String.fromCharCode(92);

// keep a rig from escaping assets/3d via ../ in the name
const safe = name => {
  let clean = normalize(name).split(BACKSLASH).join('/');
  while (clean.startsWith('/')) clean = clean.slice(1);
  if (clean.split('/').includes('..')) throw new Error('bad name: ' + name);
  return clean;
};

let written = 0;

createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');

  if (req.method === 'POST' && url.pathname === '/save') {
    try {
      const rel = safe(url.searchParams.get('name') || '');
      if (!rel) throw new Error('missing name');
      const dest = join(root, 'assets/3d', rel);
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const body = Buffer.concat(chunks);
      await mkdir(dirname(dest), { recursive: true });
      await writeFile(dest, body);
      written++;
      console.log(`wrote ${written}: ${rel} (${(body.length / 1024).toFixed(0)} KB)`);
      res.writeHead(200, { 'access-control-allow-origin': '*' });
      res.end('ok');
    } catch (e) {
      res.writeHead(400); res.end(String(e.message));
    }
    return;
  }

  try {
    const rel = safe(decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname));
    const body = await readFile(join(root, rel));
    res.writeHead(200, { 'content-type': TYPES[extname(rel)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404); res.end('not found');
  }
}).listen(port, () => console.log(`save-server on http://localhost:${port} - writes land in assets/3d/`));
