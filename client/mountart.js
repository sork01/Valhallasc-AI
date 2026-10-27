'use strict';
// Mount sprites (scripts/make_mount_sprites.py, assets/mounts_sprites.txt). A mount is one atlas per animal with eight
// facings and two clips (idle, run), drawn in the class sprites' camera and depth encoding, so the rider's frame is laid
// into the mount's frame pixel by pixel on depth: one sheet serves every class and both bodies. The rider is raised onto
// the saddle (raise + the frame's bob) and hidden below `cut` (world height), so the legs vanish into the barrel.
(() => {
  const FW = 160, FH = 160, AY = 119, SHIFT = 64, CH = FH + SHIFT, PX = 1.03, COSE = Math.sqrt(3) / 2;
  const TONES = [.5, .78, 1, 1.18];
  let meta = null, metaJob = null;
  const atlases = new Map();         // id -> { color, depth, width, status }
  const tints = new Map();           // id|tint -> Map(packed colour -> [r,g,b])
  const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const pack = (r, g, b) => r * 65536 + g * 256 + b;
  function pixels(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
        resolve({ data: g.getImageData(0, 0, img.width, img.height).data, width: img.width });
      };
      img.onerror = () => reject(new Error('mount art ' + url));
      img.src = url;
    });
  }
  const loadMeta = () => metaJob || (metaJob = fetch('assets/mounts_sprites.txt').then(r => r.json()).then(m => { meta = m; }).catch(() => { metaJob = null; }));
  function ensure(id) {
    let a = atlases.get(id);
    if (a) return a;
    a = { status: 'loading' }; atlases.set(id, a);
    loadMeta().then(() => {
      const m = meta?.mounts?.[id];
      if (!m) { a.status = 'missing'; return; }
      return Promise.all([pixels('assets/' + m.png), pixels('assets/' + m.depth)]).then(([c, d]) => { a.color = c.data; a.depth = d.data; a.width = c.width; a.status = 'ready'; });
    }).catch(() => { a.status = 'missing'; });
    return a;
  }
  // The coat colours of the reborn tints: each tone of the coat ramp becomes the tint scaled to that tone.
  function tintTable(id, tint) {
    if (!tint) return null;
    const key = id + '|' + tint;
    if (tints.has(key)) return tints.get(key);
    const target = window.Rebirth?.tintColor(tint); let table = null;
    if (target) {
      const to = hex(target); table = new Map();
      meta.mounts[id].coat.forEach((c, i) => { const f = hex(c); table.set(pack(...f), to.map(v => Math.min(255, Math.round(v * TONES[i])))); });
    }
    tints.set(key, table); return table;
  }
  const available = () => !window.__valhallaTestSprites;
  function ready(id) {
    if (!available() || !id) return false;
    const a = ensure(id);
    return a.status === 'ready';
  }
  // The rider's frame (a canvas from MageSprite.frame with _px colours and _z depths) sitting in the mount's frame.
  function compose(rider, id, clip, dir, i, tint) {
    const m = meta.mounts[id], a = atlases.get(id), C = m.clips[clip];
    i = ((i % C.n) + C.n) % C.n;
    // The saved horse run was authored with planted hooves travelling forwards. Play it backwards so they
    // push back against the ground; use the same source frame for colour, depth and the rider's saddle bob.
    if (id === 'horse' && clip === 'run') i = (C.n - i) % C.n;
    const out = new ImageData(FW, CH), z = new Uint16Array(FW * CH).fill(65535);
    const bx = i * FW, by = (C.row0 + dir) * FH, table = tintTable(id, tint);
    for (let y = 0; y < FH; y++) for (let x = 0; x < FW; x++) {
      const p = ((by + y) * a.width + bx + x) * 4;
      if (!a.color[p + 3]) continue;
      const dst = (y + SHIFT) * FW + x;
      z[dst] = a.depth[p] * 256 + a.depth[p + 1];
      const paint = table && table.get(pack(a.color[p], a.color[p + 1], a.color[p + 2]));
      out.data[dst * 4] = paint ? paint[0] : a.color[p]; out.data[dst * 4 + 1] = paint ? paint[1] : a.color[p + 1];
      out.data[dst * 4 + 2] = paint ? paint[2] : a.color[p + 2]; out.data[dst * 4 + 3] = 255;
    }
    const raise = m.raise + (m.bob[clip][i] || 0), shift = Math.round(raise * COSE * PX), lift = raise * 32;
    const px = rider._px, rz = rider._z;
    for (let y = 0; y < FH; y++) {
      const ny = y + SHIFT - shift; if (ny < 0 || ny >= CH) continue;
      const up = (AY - y) / PX;
      for (let x = 0; x < FW; x++) {
        const s = y * FW + x;
        if (!px[s * 4 + 3]) continue;
        const enc = rz[s], world = COSE * up - .5 * (enc / 64 - 512) + raise;
        if (world < m.cut) continue;
        const dst = ny * FW + x, depth = enc - lift;
        if (depth > z[dst]) continue;
        z[dst] = depth;
        out.data[dst * 4] = px[s * 4]; out.data[dst * 4 + 1] = px[s * 4 + 1]; out.data[dst * 4 + 2] = px[s * 4 + 2]; out.data[dst * 4 + 3] = 255;
      }
    }
    const canvas = document.createElement('canvas'); canvas.width = FW; canvas.height = CH;
    canvas.getContext('2d').putImageData(out, 0, 0);
    return canvas;
  }
  const clipFor = (id, moving) => moving ? 'run' : 'idle';
  window.MountArt = {
    FW, FH, SHIFT, ready, compose, clipFor,
    meta: id => meta?.mounts?.[id] || null,
    // Start loading the selected mount before it is ridden.
    preload: id => { if (available() && id) ensure(id); },
  };
})();
