'use strict';
// Saved PixelFlow NPC frames. Names, routes and interactions remain in WORLD_MAP.
(() => {
  let meta = null, fresh = null;
  const sources = new Map(), tinted = new Map();
  let tintZone = null;
  // Keep the current zone's working set. Evicting visible people every frame
  // would continuously allocate full atlases in a busy town.
  const cacheLimit = () => Math.max(24, window.City?.npcs.length || 0);
  const loadMeta = url => fetch(url).then(r => { if (!r.ok) throw Error('NPC artwork unavailable'); return r.json(); });
  // The player-style remake (`assets/npcp.txt`, atlases `npcp_<design>.png`, same frame, anchor, scale and clips) draws every person it has a design for;
  // the saved atlases (`assets/npc.txt`) stay as the fallback (and carry the per-person assignment). Both manifests name a design the same way.
  const ready = Promise.all([loadMeta('assets/npc.txt').catch(() => null), loadMeta('assets/npcp.txt').catch(() => null)]).then(([a, b]) => { meta = a; fresh = b; return a; });
  const assignment = n => meta?.npcs[n.id];
  // Which manifest and atlas draw a person: the player-style one when their species is switched over and it has the design.
  function art(n) {
    const who = assignment(n); if (!who) return null;
    const isNew = !!fresh && !!fresh.sprites[who.art], m = isNew ? fresh : meta;
    return { who, m, isNew, art: who.art, key: (isNew ? 'npcp_' : 'npc_') + who.art };
  }
  function source(key) {
    if (!sources.has(key)) { const img = new Image(); img.src = `assets/${key}.png`; sources.set(key, img); }
    const img = sources.get(key);
    return img.complete && img.naturalWidth ? img : null;
  }
  const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  const shade = (color, amount) => rgb(color).map(v => Math.round(amount < 1 ? v * amount : v + (255 - v) * (amount - 1)));
  function atlas(n, pose, img) {
    const key = pose.key;
    if (!pose.m.designs[pose.art].general) return img;
    const zone = window.Field?.zone ?? 0;
    if (tintZone !== zone) { for (const old of tinted.values()) old.width = old.height = 0; tinted.clear(); tintZone = zone; }
    const who = assignment(n), identity = who.identity, signature = `${key}|${identity.skin}|${identity.hair}|${who.color}`;
    if (tinted.has(signature)) { const canvas = tinted.get(signature); tinted.delete(signature); tinted.set(signature, canvas); return canvas; }
    const remap = new Map(), materials = pose.m.designs[pose.art].materials;
    // The player-style manifest carries each design's own brightness steps (four per group); the saved one used these fixed ones.
    const given = pose.m.designs[pose.art].amounts || {};
    for (const [group, color, amounts] of [['skin', identity.skin, given.skin || [.65, 1, 1.5]], ['hair', identity.hair, given.hair || [.6, 1, 1.4]], ['cloth', who.color, given.cloth || [.45, .7, 1, 1.45]]]) {
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
    const a = art(n); if (!a || !a.m.sprites[a.art]) return null;
    const name = n.moving ? 'walk' : talk ? 'talk' : 'idle', clip = a.m.clips[name];
    // Phase by stable identity, so neighbours do not blink or step together.
    const phase = [...n.id].reduce((sum, char) => sum + char.charCodeAt(0), 0);
    return { key: a.key, art: a.art, m: a.m, isNew: a.isNew, clip: name, row: clip.row, step: Math.floor(t * clip.fps + phase) % clip.n, mirrored: !!n.moving && n.fx - n.fy < 0 };
  }
  // Merfolk swim (MERFOLK-SWIM): drawn from the same saved frames, so nothing but the drawing changes (routes, speed, names, dialogue stay).
  // They float LIFT px above the floor (the shadow stays on it), drift up and down, lean along the way they swim, wave the tail in an S
  // (the frame's lowest rows are sheared sideways, more towards the tip) and, while moving, let a few bubbles rise. A reduced-motion player
  // gets the lift and the lean but no bob, wave or bubbles. The nameplate (`top`) and the costume sockets (`head`) follow the lift.
  // Where the tail starts (frame row), the waist the body leans about, and how far the tail tip swings (source px: moving, standing). The
  // player-style merfolk have a longer tail that starts higher than the saved art's little fin.
  const LIFT = 25, LEAN = .5, GEO = { saved: { tailTop: 66, waist: 62, amp: [4, 1.5], strip: 2 }, fresh: { tailTop: 52, waist: 52, amp: [6, 2.2], strip: 1 } };
  const calm = () => !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const swimmer = n => assignment(n)?.identity?.species === 'merfolk' || n.look?.species === 'merfolk';
  function swimPose(n, t, pose, portrait) {
    if (!swimmer(n)) return null;
    const phase = [...n.id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 628 / 100, still = calm(), moving = pose.clip === 'walk';
    const bob = still || portrait ? 0 : Math.sin(t * 1.7 + phase) * (moving ? 2.5 : 3.5);
    const geo = pose.isNew ? GEO.fresh : GEO.saved;
    return { lift: LIFT + bob, phase, moving, still, geo, angle: moving && !portrait ? (pose.mirrored ? -LEAN : LEAN) : 0,
      amp: still || portrait ? 0 : geo.amp[moving ? 0 : 1] };
  }
  function draw(g, n, t, talk = false, portrait = false) {
    const pose = frame(n, t, talk); if (!pose) return false;
    const img = source(pose.key); if (!img) return false;
    const sheet = atlas(n, pose, img), [w, h] = pose.m.frame, [ax, ay] = pose.m.anchor, scale = pose.m.scale, sw = swimPose(n, t, pose, portrait);
    g.save(); g.imageSmoothingEnabled = false;
    if (sw) {
      g.translate(0, -sw.lift);
      if (sw.angle) { const py = -(ay - sw.geo.waist) * scale; g.translate(0, py); g.rotate(sw.angle); g.translate(0, -py); }
    }
    if (pose.mirrored) g.scale(-1, 1);
    const sx = pose.step * w, sy = pose.row * h, dx = -ax * scale, dy = -ay * scale;
    if (!sw || !sw.amp) g.drawImage(sheet, sx, sy, w, h, dx, dy, w * scale, h * scale);
    else {
      // The body is one piece; the tail is cut into thin strips, each pushed sideways by a travelling sine wave.
      g.drawImage(sheet, sx, sy, w, sw.geo.tailTop, dx, dy, w * scale, sw.geo.tailTop * scale);
      for (let r = sw.geo.tailTop; r < h; r += sw.geo.strip) {
        const off = sw.amp * ((r - sw.geo.tailTop) / (h - sw.geo.tailTop)) * Math.sin(t * 7 - r * .3 + sw.phase) * scale;
        const top = Math.round((r - ay) * scale), bottom = Math.round((r + sw.geo.strip - ay) * scale);
        g.drawImage(sheet, sx, sy + r, w, sw.geo.strip, dx + off, top, w * scale, bottom - top);
      }
    }
    g.restore();
    if (sw?.moving && !sw.still && !portrait) {
      g.save(); g.lineWidth = 1.5; g.strokeStyle = '#d6fbffcc'; g.fillStyle = '#d6fbff33';
      for (let k = 0; k < 3; k++) {
        const u = (t * .45 + k / 3 + sw.phase * .07) % 1;
        g.globalAlpha = (1 - u) * .9; g.beginPath(); g.arc((k % 2 ? 1 : -1) * (26 + Math.sin(u * 9 + k * 2.1) * 5), -(LIFT + 70) - u * 90, 2.2 + (1 - u) * 1.6, 0, Math.PI * 2); g.fill(); g.stroke();
      }
      g.restore();
    }
    return true;
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
      const [w, h] = pose.m.frame, [ax, ay] = pose.m.anchor;
      headCanvas ||= document.createElement('canvas'); headCanvas.width = w; headCanvas.height = h;
      const g = headCanvas.getContext('2d', { willReadFrequently: true });
      g.drawImage(img, pose.step * w, pose.row * h, w, h, 0, 0, w, h);
      const px = g.getImageData(0, 0, w, h).data, materials = pose.m.designs[pose.art].materials;
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
    const scale = pose.m.scale * (n.look?.scale || 1);
    let x = socket.x * scale * (pose.mirrored ? -1 : 1), y = socket.y * scale, collar = socket.collar * scale;
    const sw = swimPose(n, t, pose, false);
    if (sw) {
      const py = -(pose.m.anchor[1] - sw.geo.waist) * scale, c = Math.cos(sw.angle), s = Math.sin(sw.angle), ry = y - py;
      const turnedX = x * c - ry * s, turnedY = py + x * s + ry * c, lift = sw.lift * (n.look?.scale || 1);
      collar += turnedY - y - lift; x = turnedX; y = turnedY - lift;
    }
    return { x, y, width: socket.width * scale, collar };
  }
  window.NpcArt = { ready, draw, frame, head, top(n) { const a = art(n); return a && a.m.tops?.[a.art] ? (a.m.tops[a.art] * a.m.scale + 3 + (swimmer(n) ? LIFT : 0)) * (n.look?.scale || 1) : null; },
    readyFor(npcs) { return !!meta && npcs.every(n => { const a = art(n); return !a || !!source(a.key); }); },
    styleOf(n) { const a = art(n); return a ? (a.isNew ? 'player' : 'saved') : null; },
    get manifest() { return meta; }, get fresh() { return fresh; }, get cacheSize() { return tinted.size; }, get cacheLimit() { return cacheLimit(); } };
})();
