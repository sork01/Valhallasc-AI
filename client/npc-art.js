'use strict';
// Saved PixelFlow NPC frames. Names, routes and interactions remain in WORLD_MAP.
(() => {
  let meta = null;
  const sources = new Map(), tinted = new Map();
  let tintZone = null;
  // Keep the current zone's working set. Evicting visible people every frame
  // would continuously allocate full atlases in a busy town.
  const cacheLimit = () => Math.max(24, window.City?.npcs.length || 0);
  const ready = fetch('assets/npc.txt').then(r => { if (!r.ok) throw Error('NPC artwork unavailable'); return r.json(); }).then(value => { meta = value; return value; }).catch(() => null);
  const assignment = n => meta?.npcs[n.id];
  function source(key) {
    if (!sources.has(key)) { const img = new Image(); img.src = `assets/npc_${key}.png`; sources.set(key, img); }
    const img = sources.get(key);
    return img.complete && img.naturalWidth ? img : null;
  }
  const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  const shade = (color, amount) => rgb(color).map(v => Math.round(amount < 1 ? v * amount : v + (255 - v) * (amount - 1)));
  function atlas(n, key, img) {
    if (!meta.designs[key].general) return img;
    const zone = window.Field?.zone ?? 0;
    if (tintZone !== zone) { for (const old of tinted.values()) old.width = old.height = 0; tinted.clear(); tintZone = zone; }
    const who = assignment(n), identity = who.identity, signature = `${key}|${identity.skin}|${identity.hair}|${who.color}`;
    if (tinted.has(signature)) { const canvas = tinted.get(signature); tinted.delete(signature); tinted.set(signature, canvas); return canvas; }
    const remap = new Map(), materials = meta.designs[key].materials;
    for (const [group, color, amounts] of [['skin', identity.skin, [.65, 1, 1.5]], ['hair', identity.hair, [.6, 1, 1.4]], ['cloth', who.color, [.45, .7, 1, 1.45]]]) {
      if (!/^#[0-9a-f]{6}$/i.test(color || '')) continue;
      amounts.forEach((amount, i) => { const from = rgb(materials[group + i]); remap.set((from[0] << 16) | (from[1] << 8) | from[2], shade(color, amount)); });
    }
    const canvas = document.createElement('canvas'); canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
    const g = canvas.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
    const pixels = g.getImageData(0, 0, canvas.width, canvas.height), data = pixels.data;
    for (let i = 0; i < data.length; i += 4) { if (!data[i + 3]) continue; const to = remap.get((data[i] << 16) | (data[i + 1] << 8) | data[i + 2]); if (to) [data[i], data[i + 1], data[i + 2]] = to; }
    g.putImageData(pixels, 0, 0); tinted.set(signature, canvas);
    while (tinted.size > cacheLimit()) { const oldest = tinted.keys().next().value, old = tinted.get(oldest); old.width = old.height = 0; tinted.delete(oldest); }
    return canvas;
  }
  function frame(n, t, talk = false) {
    const who = assignment(n); if (!who || !meta.sprites[who.art]) return null;
    const name = n.moving ? 'walk' : talk ? 'talk' : 'idle', clip = meta.clips[name];
    // Phase by stable identity, so neighbours do not blink or step together.
    const phase = [...n.id].reduce((sum, char) => sum + char.charCodeAt(0), 0);
    return { key: who.art, clip: name, row: clip.row, step: Math.floor(t * clip.fps + phase) % clip.n, mirrored: !!n.moving && n.fx - n.fy < 0 };
  }
  function draw(g, n, t, talk = false) {
    const pose = frame(n, t, talk); if (!pose) return false;
    const img = source(pose.key); if (!img) return false;
    const sheet = atlas(n, pose.key, img), [w, h] = meta.frame, [ax, ay] = meta.anchor, scale = meta.scale;
    g.save(); g.imageSmoothingEnabled = false; if (pose.mirrored) g.scale(-1, 1);
    g.drawImage(sheet, pose.step * w, pose.row * h, w, h, -ax * scale, -ay * scale, w * scale, h * scale); g.restore(); return true;
  }
  // Costume sockets come from the exported frame, never the tallest held prop.
  // Inspect each source frame once; tinting does not change its silhouette/material mask.
  const heads = new Map();
  let headCanvas = null;
  function head(n, t, talk = false) {
    const pose = frame(n, t, talk); if (!pose) return null;
    const img = source(pose.key); if (!img) return null;
    const key = `${pose.key}|${pose.row}|${pose.step}`;
    if (!heads.has(key)) {
      const [w, h] = meta.frame, [ax, ay] = meta.anchor;
      headCanvas ||= document.createElement('canvas'); headCanvas.width = w; headCanvas.height = h;
      const g = headCanvas.getContext('2d', { willReadFrequently: true });
      g.drawImage(img, pose.step * w, pose.row * h, w, h, 0, 0, w, h);
      const px = g.getImageData(0, 0, w, h).data, materials = meta.designs[pose.key].materials;
      const skin = new Set(Object.entries(materials).filter(([k]) => k.startsWith('skin')).map(([, c]) => parseInt(c.slice(1), 16)));
      const mask = new Uint8Array(w * h);
      for (let y = 0; y < ay; y++) for (let x = Math.max(0, ax - 20); x < Math.min(w, ax + 21); x++) {
        const i = (y * w + x) * 4;
        if (px[i + 3] && skin.has((px[i] << 16) | (px[i + 1] << 8) | px[i + 2])) mask[y * w + x] = 1;
      }
      let face = [];
      for (let i = 0; i < mask.length; i++) if (mask[i]) {
        const component = [i]; mask[i] = 0;
        for (let j = 0; j < component.length; j++) {
          const at = component[j], x = at % w;
          for (const k of [x ? at - 1 : -1, x + 1 < w ? at + 1 : -1, at - w, at + w]) if (k >= 0 && k < mask.length && mask[k]) { mask[k] = 0; component.push(k); }
        }
        if (component.length > face.length) face = component;
      }
      if (face.length < 12) { heads.set(key, null); }
      else {
        const xs = face.map(i => i % w), ys = face.map(i => Math.floor(i / w));
        const left = Math.min(...xs), right = Math.max(...xs), cx = (left + right) / 2;
        const half = Math.max(5, (right - left) * .3); let crown = Math.min(...ys);
        // Follow the connected cap/hair above the face; ignore detached overhead props.
        for (let y = crown - 1; y >= 0; y--) {
          let visible = false;
          for (let x = Math.ceil(cx - half); x <= Math.floor(cx + half); x++) if (px[(y * w + x) * 4 + 3]) { visible = true; break; }
          if (!visible) break; crown = y;
        }
        heads.set(key, { x: cx - ax, y: crown + 1 - ay, width: Math.max(10, (right - left + 1) / 2 + 1), collar: Math.max(...ys) + 2 - ay });
      }
    }
    const socket = heads.get(key); if (!socket) return null;
    const scale = meta.scale * (n.look?.scale || 1);
    return { x: socket.x * scale * (pose.mirrored ? -1 : 1), y: socket.y * scale, width: socket.width * scale, collar: socket.collar * scale };
  }
  window.NpcArt = { ready, draw, frame, head, top(n) { const who = assignment(n); return who && meta.tops?.[who.art] ? (meta.tops[who.art] * meta.scale + 3) * (n.look?.scale || 1) : null; },
    readyFor(npcs) { return !!meta && npcs.every(n => { const who = assignment(n); return !who || !!source(who.art); }); },
    get manifest() { return meta; }, get cacheSize() { return tinted.size; }, get cacheLimit() { return cacheLimit(); } };
})();
