'use strict';
// Independent equipment, composited once per pose and cached. Camera depth
// puts a staff behind the gripping hand and robes behind hair in every facing.
(() => {
  const HAIR = ['#ac78c4', '#d8c89b', '#723b2b', '#42364e', '#bc685c', '#689bb1'];
  const SKIN = ['#ffceb0', '#f0c8a6', '#bd825d', '#875640'];
  const ARMOR = { none: { name: 'Simple cloth', defense: 0 }, apprentice: { name: 'Apprentice robes', defense: 2 }, runic: { name: 'Runic vestments', defense: 5 } };
  const WEAPON = { none: { name: 'Empty hands', attack: 0 }, ash: { name: 'Ash staff', attack: 4 }, crystal: { name: 'Crystal staff', attack: 9 } };
  const sources = new Map();
  // ---- Loading ------------------------------------------------------------------------------------------------
  // Decoding an atlas is main-thread work, so it is cut into slices of about SLICE_MS that yield to the page, and a
  // load is either foreground (your own character: starts at once) or background (everyone else: one at a time, and
  // only while no foreground load is running, so other players' art never delays yours).
  const SLICE_MS = 6;
  const yielders = [], channel = new MessageChannel();
  channel.port1.onmessage = () => yielders.shift()?.();
  const yieldMain = () => new Promise(resolve => { yielders.push(resolve); channel.port2.postMessage(0); });
  let foreground = 0, backgroundChain = Promise.resolve();
  const foregroundIdle = [];
  const leaveForeground = () => { if (--foreground === 0) for (const wake of foregroundIdle.splice(0)) wake(); };
  const whenForegroundIdle = () => foreground === 0 ? Promise.resolve() : new Promise(resolve => foregroundIdle.push(resolve));
  // `work(slicer)` does the decoding. A background job can be promoted when your own character needs the same art.
  function createJob(background, work) {
    const job = { background, started: false };
    let slicedAt = performance.now();
    job.slicer = {
      due: () => performance.now() - slicedAt > SLICE_MS,
      yield: async () => { await yieldMain(); if (job.background) await whenForegroundIdle(); slicedAt = performance.now(); },
    };
    job.promise = new Promise((resolve, reject) => {
      job.start = () => {
        if (job.started) return;
        job.started = true; slicedAt = performance.now();
        if (!job.background) foreground++;
        work(job.slicer, job).then(resolve, reject).finally(() => { if (!job.background) leaveForeground(); });
      };
    });
    if (background) backgroundChain = backgroundChain.then(whenForegroundIdle).then(() => { job.start(); return job.promise.catch(() => {}); });
    else job.start();
    return job;
  }
  function promote(job) {
    if (!job.background) return;
    job.background = false;
    if (job.started) foreground++; else job.start();
  }
  const bitmap = async url => {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Character sprite art could not be loaded: ' + url);
    return createImageBitmap(await response.blob());
  };
  // Scratch canvases: a frame is copied out one rectangle at a time, so no full-atlas readback ever happens.
  const scratch = {};
  const reader = (name, w, h) => {
    const c = scratch[name] || (scratch[name] = document.createElement('canvas'));
    if (c.width < w || c.height < h) { c.width = Math.max(c.width, w); c.height = Math.max(c.height, h); }
    const g = c.ctx || (c.ctx = c.getContext('2d', { willReadFrequently: true }));
    g.globalCompositeOperation = 'copy';
    return (image, sx, sy, sw, sh) => { g.drawImage(image, sx, sy, sw, sh, 0, 0, sw, sh); return g.getImageData(0, 0, sw, sh).data; };
  };
  // Slow path for a set without a bounds sidecar (scripts/sprite_bounds.py): find the opaque box of one cell.
  function scanBounds(pixels, fw, fh) {
    const alpha = new Uint32Array(pixels.buffer, pixels.byteOffset, fw * fh);
    let x0 = fw, y0 = fh, x1 = -1, y1 = -1;
    for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) {
      if (alpha[y * fw + x] >>> 24 === 0) continue;
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    return x1 < 0 ? [0, 0, 0, 0] : [x0, y0, x1 - x0 + 1, y1 - y0 + 1];
  }
  const bytesOf = text => { const raw = atob(text), out = new Uint8Array(raw.length); for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i); return out; };
  const loadImages = files => Promise.all([bitmap('assets/' + files.png), bitmap('assets/' + files.depth)]);
  // Retain only occupied rectangles. `bounds` (4 bytes per frame, the sidecar's) tells which rectangle to copy.
  async function decodePart(meta, bounds, images, slicer) {
    const [fw, fh] = meta.frame, [color, depth] = images;
    const readColor = reader('color', fw, fh), readDepth = reader('depth', fw, fh);
    const frames = {};
    let n = 0;
    try {
      for (const [clip, C] of Object.entries(meta.clips)) for (let dir = 0; dir < 8; dir++) for (let i = 0; i < C.n; i++, n++) {
        const bx = i * fw, by = (C.row0 + dir) * fh;
        let box = bounds ? [bounds[n * 4], bounds[n * 4 + 1], bounds[n * 4 + 2], bounds[n * 4 + 3]] : scanBounds(readColor(color, bx, by, fw, fh), fw, fh);
        const [x, y, width, height] = box;
        let pixels, z;
        if (!width || !height) { pixels = new Uint8ClampedArray(0); z = new Uint16Array(0); box = [fw, fh, 0, 0]; }
        else {
          pixels = readColor(color, bx + x, by + y, width, height).slice();
          const d = readDepth(depth, bx + x, by + y, width, height);
          z = new Uint16Array(width * height);
          for (let k = 0; k < z.length; k++) z[k] = d[k * 4] * 256 + d[k * 4 + 1];
        }
        frames[`${clip}/${dir}/${i}`] = { x: box[0], y: box[1], w: box[2], h: box[3], pixels, z };
        if (slicer.due()) await slicer.yield();
      }
    } finally { color.close(); depth.close(); }
    return frames;
  }
  // Test mode (window.__valhallaTestSprites, set only by the automated tests): every class gets one tiny static figure
  // built in code, so a page loads without decoding the multi-megapixel atlases. Only the small metadata file is read,
  // so ramps, equipment names and clip counts stay the real ones. Each skin/hair/armour/weapon choice still changes pixels.
  const colour = text => { let h = 0; for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return [64 + (h & 127), 64 + ((h >> 7) & 127), 64 + ((h >> 14) & 127)]; };
  const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  function stubSource(meta) {
    const [ax, ay] = meta.anchor, solid = (x, y, w, h, rows, z) => {
      const pixels = new Uint8ClampedArray(w * h * 4), depth = new Uint16Array(w * h).fill(z);
      for (let i = 0; i < w * h; i++) pixels.set([...rows(Math.floor(i / w)), 255], i * 4);
      return { x, y, w, h, pixels, z: depth };
    };
    const hair = rgb(meta.ramps.hair[2]), skin = rgb(meta.ramps.skin[2]);
    const parts = {};
    for (const part of Object.keys(meta.parts)) {
      const frame = part === 'body' ? solid(ax - 3, ay - 14, 6, 14, row => row < 4 ? hair : skin, 1000)
        : part.startsWith('armor_') ? solid(ax - 3, ay - 9, 6, 6, () => colour(part), 500)
        : part.startsWith('head_') ? solid(ax - 3, ay - 17, 6, 3, () => colour(part), 480)
        : part.startsWith('shoulders_') ? solid(ax - 5, ay - 12, 10, 2, () => colour(part), 470)
        : part.startsWith('gloves_') ? solid(ax - 5, ay - 7, 10, 2, () => colour(part), 460)
        : part.startsWith('pants_') ? solid(ax - 4, ay - 8, 8, 4, () => colour(part), 520)
        : part.startsWith('necklace_') ? solid(ax - 2, ay - 12, 4, 1, () => colour(part), 450)
        : part.startsWith('accessory_') ? solid(ax - 6, ay - 7, 2, 1, () => colour(part), 440)
        : solid(ax + 3, ay - 15, 2, 12, () => colour(part), 400);
      parts[part] = new Proxy({}, { get: () => frame });   // the same still figure for every clip, direction and frame
    }
    return { meta, parts, ensure: () => Promise.resolve() };
  }
  // The class-independent pieces (scripts/generic_gear.py) are rarely worn, so their atlases are decoded only when a
  // look asks for them: `source.ensure(part)` starts the load once and resolves when the frames are in `source.parts`.
  const GENERIC = { head: 'ironhide', shoulders: 'ironhide', gloves: 'duelist', pants: 'wayfarer', necklace: 'moonstone', accessory: 'amber' };
  const LAZY = new Set(Object.entries(GENERIC).map(([slot, variant]) => `${slot}_${variant}`));
  async function loadBounds(url, meta) {
    try {
      const response = await fetch(url.replace(/_sprites\.txt$/, '_bounds.txt'));
      if (!response.ok) return {};
      const sidecar = await response.json(), frames = Object.values(meta.clips).reduce((sum, C) => sum + C.n, 0) * 8;
      return sidecar.version === 1 && sidecar.frames === frames ? sidecar.parts : {};
    } catch (error) { return {}; }
  }
  async function loadSource(url, job) {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Character sprite metadata could not be loaded');
    const meta = await response.json(), parts = {}, loading = new Map();
    if (window.__valhallaTestSprites === true) return stubSource(meta);
    const sidecar = await loadBounds(url, meta), frames = Object.values(meta.clips).reduce((sum, C) => sum + C.n, 0) * 8;
    const boundsOf = part => { const text = sidecar[part]; const bytes = text ? bytesOf(text) : null; return bytes && bytes.length === frames * 4 ? bytes : null; };
    const lazy = new Set([...LAZY, ...(meta.lazyParts || [])]);
    const names = Object.keys(meta.parts).filter(part => !lazy.has(part));
    // Your own character's next atlas downloads while this one is copied; background loads stay one atlas at a time.
    let next = null;
    try {
      for (let k = 0; k < names.length; k++) {
        const images = await (next || loadImages(meta.parts[names[k]]));
        next = k + 1 < names.length && !job.background ? loadImages(meta.parts[names[k + 1]]) : null;
        parts[names[k]] = await decodePart(meta, boundsOf(names[k]), images, job.slicer);
      }
    } catch (error) { next?.then(images => images.forEach(image => image.close()), () => {}); throw error; }
    const ensure = (part, background = false) => {
      if (parts[part] || !meta.parts[part]) return Promise.resolve();
      let entry = loading.get(part);
      if (!entry) {
        entry = createJob(background, async slicer => {
          try { parts[part] = await decodePart(meta, boundsOf(part), await loadImages(meta.parts[part]), slicer); }
          catch (error) { console.warn('Equipment art could not be loaded', part, error); }
        });
        loading.set(part, entry);
      } else if (!background) promote(entry);
      return entry.promise;
    };
    return { meta, parts, ensure };
  }
  // The catalog names every worn piece by a unique variant. An original piece is drawn as itself; a recolouring (items
  // with `art` and `tint`, built by scripts/gear_levels.py) is its base drawing painted with the tint, which uses the
  // terms of the CSS filters the inventory icon gets: hue-rotate degrees, saturate, brightness.
  const KIND = { armor: 'armor', weapon: 'weapon', head: 'headgear', shoulders: 'shoulders', gloves: 'gloves', pants: 'pants', necklace: 'necklace', accessory: 'accessory' };
  let catalog = null, catalogSize = -1;
  const gearIndex = () => {
    const items = window.WORLD_ITEMS || [];
    if (!catalog || catalogSize !== items.length) { catalog = new Map(items.filter(i => i.variant).map(i => [`${i.kind}|${i.variant}`, i])); catalogSize = items.length; }
    return catalog;
  };
  const PROGRESSION = ['regearl25', 'regearl30', 'regearl35', 'regearl40', 'regearl45', 'regearl50', 'regearcloister', 'regearreliquary', 'regearnave'];
  const hasGear = (table, kind, variant) => Object.hasOwn(table, variant) || PROGRESSION.includes(variant) || gearIndex().has(`${kind}|${variant}`);
  const resolve = (slot, variant) => {
    const i = variant && variant !== 'none' ? gearIndex().get(`${KIND[slot]}|${variant}`) : null;
    return { art: i?.art || variant, tint: i?.tint || null };
  };
  const clamp = v => v < 0 ? 0 : v > 255 ? 255 : v;
  // The CSS filter matrices (hue-rotate, then saturate, then brightness), clamped after each step like the filter is.
  function tintMatrix({ hue = 0, saturate = 1, brightness = 1 }) {
    const c = Math.cos(hue * Math.PI / 180), n = Math.sin(hue * Math.PI / 180);
    const H = [[.213 + c * .787 - n * .213, .715 - c * .715 - n * .715, .072 - c * .072 + n * .928], [.213 - c * .213 + n * .143, .715 + c * .285 + n * .14, .072 - c * .072 - n * .283], [.213 - c * .213 - n * .787, .715 - c * .715 + n * .715, .072 + c * .928 + n * .072]];
    const S = [[.213 + .787 * saturate, .715 - .715 * saturate, .072 - .072 * saturate], [.213 - .213 * saturate, .715 + .285 * saturate, .072 - .072 * saturate], [.213 - .213 * saturate, .715 - .715 * saturate, .072 + .928 * saturate]];
    const apply = (M, v) => M.map(row => clamp(row[0] * v[0] + row[1] * v[1] + row[2] * v[2]));
    return (r, g, b) => apply([[brightness, 0, 0], [0, brightness, 0], [0, 0, brightness]], apply(S, apply(H, [r, g, b]))).map(Math.round);
  }
  const equipment = look => ({
    armor: hasGear(ARMOR, 'armor', look?.mageArmor) ? look.mageArmor : 'apprentice',
    weapon: hasGear(WEAPON, 'weapon', look?.mageWeapon) ? look.mageWeapon : 'ash',
  });
  // Head, shoulder and glove pieces use the class's tier, shared gear, or a catalog art layer.
  // A part missing from the class atlas is simply not drawn.
  const SLOT_ORDER = ['armor', 'pants', 'shoulders', 'gloves', 'head', 'necklace', 'accessory', 'weapon'];
  // A dungeon set needs a silhouette at field scale, not only a different tint on
  // the same 160px equipment rig. These marks sit behind the animated figure and
  // follow it in every pose/facing. One piece shows the origin; more pieces make
  // the mark brighter. They are drawn from the equipped server-approved look.
  const DUNGEON_MARKS = {
    regearvault: { name: 'Undervault', dark: '#123840', bright: '#58f5d4' },
    regearcloister: { name: 'Cloister', dark: '#806e39', bright: '#fff1a2' },
    regearreliquary: { name: 'Reliquary', dark: '#681e59', bright: '#ff78c6' },
    regearnave: { name: 'Nave', dark: '#913e16', bright: '#ffbd42' },
    regearmoonwell: { name: 'Moonwell', dark: '#423983', bright: '#ccb6ff' },
    regeareye: { name: 'Eye Below', dark: '#281a43', bright: '#95ebf4' },
    regearelder: { name: 'Elder Hollow', dark: '#29432a', bright: '#d9ef8b' },
    regearpavilion: { name: 'Thousandfold', dark: '#644036', bright: '#fff0cf' },
    regearrain: { name: 'Rain Crown', dark: '#244b71', bright: '#b8f5ff' },
    regearseed: { name: 'Seed Vault', dark: '#235338', bright: '#c0ff83' },
    regearastro: { name: 'Astrolabe', dark: '#544a3a', bright: '#ffe0a0' },
    regearthunder: { name: 'Thunderheart', dark: '#4a2676', bright: '#f9e582' },
    regearbloom: { name: 'Blooming', dark: '#813a69', bright: '#ffe0f1' },
    regearsolar: { name: 'Solar', dark: '#8c3c24', bright: '#fff0a2' },
    regearamber: { name: 'Amber Archive', dark: '#7c542a', bright: '#ffe1a4' },
    regearsolstice: { name: 'Solstice', dark: '#263c6e', bright: '#d9f8ff' },
  };
  const DUNGEON_PALETTES = {
    regearvault: ['#071d25', '#164d57', '#36bcb0', '#b7fff0'],
    regearcloister: ['#342d25', '#7e7049', '#d3bf7f', '#fff5c8'],
    regearreliquary: ['#2a193a', '#71396e', '#ca64aa', '#ffe0ef'],
    regearnave: ['#381d1d', '#a64425', '#ee993d', '#fff0aa'],
    regearmoonwell: ['#22284b', '#56569a', '#aaa3db', '#f0e8ff'],
    regeareye: ['#1a1834', '#543775', '#a865ad', '#c6f9f6'],
    regearelder: ['#202d23', '#5b5734', '#8ea75e', '#e2f4a8'],
    regearpavilion: ['#231c20', '#70463c', '#d9c59e', '#fff5da'],
    regearrain: ['#102b43', '#38657e', '#80b5c3', '#e1f7ef'],
    regearseed: ['#183827', '#477248', '#7eba69', '#e7f6a8'],
    regearastro: ['#1e2944', '#715f51', '#d3ac63', '#cdeffc'],
    regearthunder: ['#23183c', '#6a398f', '#b188d5', '#f8e485'],
    regearbloom: ['#341c39', '#9a466e', '#e494b4', '#d5ffe2'],
    regearsolar: ['#3a1b1b', '#ad5432', '#edaa56', '#fff0ab'],
    regearamber: ['#38281b', '#986d39', '#d6aa5c', '#fff0bf'],
    regearsolstice: ['#141f3b', '#38567a', '#89b8d8', '#effbff'],
  };
  const dungeonPaint = art => {
    const palette = DUNGEON_PALETTES[art].map(hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)));
    return (r, g, b) => {
      const level = Math.min(2.999, Math.max(0, ((r * .25 + g * .65 + b * .1) / 255 - .1) / .82 * 3));
      const index = Math.floor(level), mix = level - index;
      return palette[index].map((channel, k) => Math.round(channel * (1 - mix) + palette[index + 1][k] * mix));
    };
  };
  function dungeonMark(equipment) {
    const counts = {};
    for (const art of Object.values(equipment)) if (DUNGEON_MARKS[art]) counts[art] = (counts[art] || 0) + 1;
    const [theme, count] = Object.entries(counts).sort((a, b) => b[1] - a[1])[0] || [];
    return theme ? { theme, count } : null;
  }
  function dungeonAura(g, mark, t) {
    const { theme, count } = mark, { dark, bright } = DUNGEON_MARKS[theme];
    const sway = Math.sin(t * 2.3) * 1.5;
    const diamond = (x, y, w, h, fill, stroke = bright) => {
      g.beginPath(); g.moveTo(x, y - h); g.lineTo(x + w, y); g.lineTo(x, y + h); g.lineTo(x - w, y);
      g.closePath(); g.fillStyle = fill; g.fill(); g.strokeStyle = stroke; g.lineWidth = 1.8; g.stroke();
    };
    const blade = (points, fill, stroke = bright) => {
      g.beginPath(); points.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y));
      g.closePath(); g.fillStyle = fill; g.fill(); g.strokeStyle = stroke; g.lineWidth = 1.7; g.stroke();
    };
    g.save();
    g.globalAlpha *= Math.min(.92, .48 + count * .085);
    // The broken circle is a common field-scale cue; each dungeon then has its
    // own large profile so the sets cannot be mistaken for progression gear.
    g.strokeStyle = dark; g.lineWidth = 8;
    g.beginPath(); g.ellipse(0, -62, 36, 49, 0, .2, Math.PI * 1.81); g.stroke();
    g.strokeStyle = bright; g.lineWidth = 2.2; g.stroke();
    if (theme === 'regearvault') {
      for (const side of [-1, 1]) {
        for (let n = 0; n < 3; n++) {
          const y = -88 + n * 20;
          blade([[side * 10, y + 10], [side * (38 + n * 6), y - 10 + sway],
                 [side * (49 + n * 7), y - 17 + sway], [side * (31 + n * 5), y + 7]], dark);
          diamond(side * (43 + n * 6), y - 9 + sway, 3, 5, bright, dark);
        }
      }
      diamond(0, -111 + sway, 9, 14, dark);
    } else if (theme === 'regearcloister') {
      for (const side of [-1, 1]) {
        for (let n = 0; n < 4; n++) {
          const y = -91 + n * 14;
          blade([[side * 13, y + 18], [side * (48 + n * 5), y - 16 + sway],
                 [side * (53 + n * 5), y - 11 + sway], [side * (27 + n * 3), y + 25]], '#dfd9b2');
        }
      }
      g.beginPath(); g.ellipse(0, -122 + sway, 22, 5, 0, 0, Math.PI * 2);
      g.fillStyle = dark; g.fill(); g.strokeStyle = bright; g.lineWidth = 2.5; g.stroke();
    } else if (theme === 'regearreliquary') {
      for (const side of [-1, 1]) {
        blade([[side * 17, -106], [side * 34, -131 + sway], [side * 54, -93],
               [side * 34, -63], [side * 20, -75]], dark);
        diamond(side * 36, -95 + sway, 11, 20, '#a74388');
        diamond(side * 55, -56 - sway, 7, 15, dark);
        diamond(side * 50, -32 + sway, 5, 10, bright, dark);
      }
      diamond(0, -125 + sway, 8, 17, bright, dark);
    } else if (theme === 'regearnave') {
      for (const side of [-1, 1]) {
        for (let n = 0; n < 5; n++) {
          const x = side * (16 + n * 9), y = -93 + n * 10;
          blade([[side * 13, -70], [x, y - 24 + sway], [x + side * 7, y - 7],
                 [x + side * 5, y + 17]], n % 2 ? '#e7762d' : dark);
        }
      }
      for (let n = 0; n < 9; n++) {
        const angle = (n / 9) * Math.PI * 1.55 + Math.PI * .73;
        const x = Math.cos(angle), y = Math.sin(angle);
        blade([[x * 23, -113 + y * 23], [x * 33, -113 + y * 33],
               [x * 26, -113 + y * 26]], bright, dark);
      }
      diamond(0, -113 + sway, 7, 9, bright, dark);
    } else if (theme === 'regearmoonwell') {
      g.beginPath(); g.ellipse(0, -75, 57, 65, -.2, .23, Math.PI * 1.66);
      g.strokeStyle = dark; g.lineWidth = 12; g.stroke();
      g.strokeStyle = bright; g.lineWidth = 3.5; g.stroke();
      for (const side of [-1, 1]) {
        for (let n = 0; n < 3; n++) {
          const x = side * (36 + n * 10), y = -96 + n * 26;
          blade([[side * 17, -75], [x, y - 19 + sway], [x + side * 6, y],
                 [x, y + 18 + sway]], n % 2 ? '#8178bb' : dark);
          diamond(x + side * 3, y + sway, 4, 7, bright, dark);
        }
      }
      diamond(0, -135 + sway, 8, 12, bright, dark);
    } else if (theme === 'regeareye') {
      for (const side of [-1, 1]) {
        for (let n = 0; n < 3; n++) {
          const x = side * (37 + n * 13), y = -113 + n * 25;
          blade([[side * 13, -76], [x, y - 13 + sway], [x + side * 8, y],
                 [x - side * 4, y + 16 + sway]], dark);
        }
      }
      g.beginPath(); g.ellipse(0, -99 + sway, 27, 15, 0, 0, Math.PI * 2);
      g.fillStyle = dark; g.fill(); g.strokeStyle = bright; g.lineWidth = 3; g.stroke();
      diamond(0, -99 + sway, 8, 13, bright, dark);
    } else if (theme === 'regearelder') {
      for (const side of [-1, 1]) {
        blade([[side * 15, -65], [side * 30, -116 + sway], [side * 39, -140 + sway],
               [side * 42, -118], [side * 64, -126], [side * 52, -108],
               [side * 48, -63], [side * 29, -43]], dark);
        for (let n = 0; n < 3; n++) {
          const x = side * (43 + n * 7), y = -112 + n * 24;
          blade([[x - side * 5, y + 10], [x + side * 8, y - 10 + sway],
                 [x + side * 14, y + sway], [x + side * 5, y + 13]], '#729a55');
        }
      }
      diamond(0, -116 + sway, 7, 12, bright, dark);
    } else if (theme === 'regearpavilion') {
      for (const side of [-1, 1]) for (let n = 0; n < 4; n++) {
        const x = side * (26 + n * 13);
        blade([[side * 10, -83], [x, -135 + n * 17 + sway],
               [x + side * 10, -122 + n * 18 + sway], [side * 19, -52]],
              n % 2 ? '#efe3c6' : dark);
      }
      blade([[-18, -122], [0, -145 + sway], [18, -122], [0, -129]], bright, dark);
    } else if (theme === 'regearrain') {
      blade([[-55, -114], [-31, -141 + sway], [0, -126], [31, -141 + sway],
             [55, -114], [37, -103], [-37, -103]], dark);
      for (const side of [-1, 1]) for (let n = 0; n < 4; n++) {
        const x = side * (25 + n * 12);
        blade([[x, -110], [x + side * 4, -62 + n * 9 + sway],
               [x - side * 3, -50 + n * 9], [x - side * 5, -88]], '#5297bd');
        diamond(x, -44 + n * 10 + sway, 3, 7, bright, dark);
      }
    } else if (theme === 'regearseed') {
      for (const side of [-1, 1]) {
        blade([[side * 8, -92], [side * 26, -137 + sway], [side * 55, -127],
               [side * 62, -79], [side * 37, -31], [side * 18, -48]], dark);
        blade([[side * 21, -91], [side * 42, -117], [side * 50, -78],
               [side * 35, -50]], '#69a75d');
      }
      diamond(0, -117 + sway, 11, 17, bright, dark);
    } else if (theme === 'regearastro') {
      for (const radius of [45, 60]) {
        g.beginPath(); g.ellipse(0, -83, radius, radius * .8, -.23, 0, Math.PI * 2);
        g.strokeStyle = radius === 45 ? bright : dark; g.lineWidth = radius === 45 ? 3 : 7; g.stroke();
      }
      for (let n = 0; n < 8; n++) {
        const a = n * Math.PI / 4;
        diamond(Math.cos(a) * 55, -83 + Math.sin(a) * 45,
                n % 2 ? 5 : 7, n % 2 ? 8 : 12, n % 2 ? bright : dark);
      }
    } else if (theme === 'regearthunder') {
      for (const side of [-1, 1]) for (let n = 0; n < 3; n++) {
        const x = side * (21 + n * 13);
        blade([[side * 12, -105], [x, -144 + n * 8 + sway],
               [x - side * 7, -104], [x + side * 10, -111],
               [x - side * 3, -42 + n * 6], [x + side * 2, -86]],
              n === 1 ? bright : dark);
      }
      diamond(0, -129 + sway, 9, 13, bright, dark);
    } else if (theme === 'regearbloom') {
      for (let n = 0; n < 8; n++) {
        const a = n * Math.PI / 4;
        const x = Math.cos(a), y = Math.sin(a);
        blade([[x * 22, -91 + y * 20], [x * 48 - y * 12, -91 + y * 48 + x * 12],
               [x * 67, -91 + y * 60 + sway],
               [x * 48 + y * 12, -91 + y * 48 - x * 12]],
              n % 2 ? '#c875a6' : dark);
      }
      diamond(0, -91 + sway, 12, 17, bright, dark);
    } else if (theme === 'regearsolar') {
      for (let n = 0; n < 12; n++) {
        const a = n * Math.PI / 6;
        const x = Math.cos(a), y = Math.sin(a);
        blade([[x * 30, -89 + y * 26], [x * 68 - y * 8, -89 + y * 63 + x * 8 + sway],
               [x * 68 + y * 8, -89 + y * 63 - x * 8 + sway]],
              n % 2 ? '#ef9c49' : dark);
      }
      g.beginPath(); g.ellipse(0, -89, 31, 31, 0, 0, Math.PI * 2);
      g.fillStyle = dark; g.fill(); g.strokeStyle = bright; g.lineWidth = 3; g.stroke();
    } else if (theme === 'regearamber') {
      for (const side of [-1, 1]) {
        blade([[side * 13, -125], [side * 52, -133 + sway],
               [side * 62, -44], [side * 17, -55]], '#bb8b4b');
        blade([[side * 20, -119], [side * 46, -124 + sway],
               [side * 53, -53], [side * 22, -61]], dark);
        for (let n = 0; n < 4; n++)
          blade([[side * 23, -109 + n * 16], [side * 47, -112 + n * 16],
                 [side * 47, -109 + n * 16], [side * 23, -106 + n * 16]], bright, dark);
      }
      diamond(0, -136 + sway, 8, 10, bright, dark);
    } else if (theme === 'regearsolstice') {
      for (const side of [-1, 1]) {
        blade([[side * 10, -70], [side * 26, -130 + sway],
               [side * 45, -148 + sway], [side * 58, -119],
               [side * 41, -67], [side * 22, -36]], dark);
        for (let n = 0; n < 3; n++)
          diamond(side * (35 + n * 9), -112 + n * 30 + sway,
                  5, 11, n % 2 ? bright : '#8ac2dd');
      }
      diamond(0, -139 + sway, 8, 15, bright, dark);
    }
    g.restore();
  }
  // Catalog art includes the later progression sets; pants, necklace and ring also have shared generic pieces.
  const CLASS_SLOTS = ['head', 'shoulders', 'gloves'];
  const pieces = (C, look) => Object.fromEntries(Object.entries(GENERIC).map(([slot, generic]) => {
    const allowed = [...(CLASS_SLOTS.includes(slot) ? [...(C.TIERS || []), generic] : [generic]), ...PROGRESSION,
      ...(window.WORLD_ITEMS || []).filter(i => i.kind === KIND[slot] && i.art).map(i => i.art),
      ...(window.WORLD_ITEMS || []).filter(i => i.source === 'orange_pool' && i.kind === KIND[slot]).map(i => i.variant),
      // The game master's golden pieces: a class-independent item with variant gm (drawn only where the class atlas has the layer).
      ...(window.WORLD_ITEMS || []).filter(i => i.rarity === 'gm' && i.kind === KIND[slot]).map(i => i.variant)];
    return [slot, allowed.includes(resolve(slot, look?.[slot]).art) ? look[slot] : 'none'];
  }));
  // Orange icons are inventory art. On a character, reuse the class's animated gear layers so the
  // chest, helm, hands and weapon follow every pose and facing at the correct depth.
  const ORANGE_PALETTES = [
    ['#33191b', '#89512f', '#f2a347', '#ffe39a'],
    ['#183424', '#426d38', '#84b95b', '#dbf4a2'],
    ['#182842', '#396f9a', '#83c9e0', '#ecfaff'],
    ['#162536', '#2d6380', '#65b5b6', '#d2fbef'],
    ['#14172d', '#363b70', '#7c88c7', '#e6eaff'],
    ['#44301c', '#bc7931', '#f6c55f', '#fff2b2'],
    ['#391b25', '#8e3537', '#e67842', '#ffe2a2'],
    ['#19263c', '#617895', '#c0d6e5', '#f7fcff'],
    ['#352419', '#987044', '#d7ae68', '#fff0bb'],
    ['#1d3027', '#576c39', '#a2be6d', '#e9f4bd'],
  ];
  const orangeFamily = variant => {
    const match = /^orange_(0[1-9]|[1-4][0-9]|50)$/.exec(variant || '');
    return match ? Math.floor((Number(match[1]) - 1) / 5) : -1;
  };
  const orangeBase = (C, meta, slot) => {
    const choices = slot === 'armor' || slot === 'weapon'
      ? Object.keys(slot === 'armor' ? C.ARMOR : C.WEAPON).filter(name => name !== 'none')
      : C.TIERS || [];
    const candidates = [choices[1], choices[0], GENERIC[slot]];
    return candidates.find(name => name && meta.parts[`${slot}_${name}`]) || 'none';
  };
  const orangePaint = family => {
    const palette = ORANGE_PALETTES[family].map(rgb);
    return (r, g, b) => {
      const light = (r * .25 + g * .65 + b * .1) / 255;
      const scaled = Math.min(2.999, Math.max(0, (light - .1) / .82 * 3));
      const index = Math.floor(scaled), mix = scaled - index;
      return palette[index].map((channel, k) => Math.round(channel * (1 - mix) + palette[index + 1][k] * mix));
    };
  };
  class MageSprite {
    constructor(source, look = {}, background = false) { this.source = source; this.background = background; this.meta = source.meta; this.cache = new Map(); this.set(look); }
    set(look) {
      this.look = { ...look }; this.cache.clear();
      // `worn` holds catalog variants; `equipment` holds the pose-matched atlas drawings.
      this.worn = { ...pieces(this.constructor, look), ...this.constructor.equipment(look) };
      this.equipment = {}; this.tintLut = new Map();
      for (const slot of SLOT_ORDER) {
        const family = orangeFamily(this.worn[slot]);
        const { art: catalogArt, tint } = resolve(slot, this.worn[slot]);
        const art = family >= 0 ? orangeBase(this.constructor, this.meta, slot) : catalogArt;
        this.equipment[slot] = art;
        if ((family >= 0 || tint || DUNGEON_PALETTES[art]) && art !== 'none') {
          const key = `${slot}_${art}`;
          const paint = family >= 0 ? orangePaint(family) : DUNGEON_PALETTES[art] ? dungeonPaint(art) : tintMatrix(tint);
          this.tintLut.set(key, { paint, colours: new Map() });
        }
      }
      for (const slot of SLOT_ORDER) {      // a layer still being decoded appears (and the frames are rebuilt) as soon as it arrives
        const part = slot + '_' + this.equipment[slot];
        if (this.equipment[slot] !== 'none' && !this.source.parts[part]) this.source.ensure?.(part, this.background).then(() => { if (this.source.parts[part]) this.cache.clear(); });
      }
      this.tint = new Map();
      const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
      const lum = c => c[0] * .299 + c[1] * .587 + c[2] * .114;
      const hair = this.constructor.HAIR, skin = this.constructor.SKIN;
      for (const [role, target] of [['hair', hair[look.hairColor || 0]], ['brow', hair[look.hairColor || 0]], ['skin', skin[look.skin || 0]]]) {
        const ramp = this.meta.ramps[role], to = hex(target || (role === 'skin' ? skin[0] : hair[0]));
        const base = lum(hex(this.meta.ramps[role === 'brow' ? 'hair' : role][2]));
        for (const color of ramp) {
          const from = hex(color), k = lum(from) / base, ratio = k < 1 ? k : 1 + (k - 1) * .35;
          this.tint.set(from[0] * 65536 + from[1] * 256 + from[2], to.map(v => Math.min(255, Math.round(v * ratio))));
        }
      }
    }
    frame(clip = 'idle', dir = 0, i = 0) {
      const C = this.meta.clips[clip]; i = Math.max(0, Math.min(C.n - 1, i)); dir = ((dir % 8) + 8) % 8;
      const key = `${clip}/${dir}/${i}`;
      if (this.cache.has(key)) return this.cache.get(key);
      const [fw, fh] = this.meta.frame, canvas = document.createElement('canvas'); canvas.width = fw; canvas.height = fh;
      const g = canvas.getContext('2d'), out = g.createImageData(fw, fh), nearest = new Uint16Array(fw * fh); nearest.fill(65535);
      const chosen = ['body'];
      for (const slot of SLOT_ORDER) if (this.equipment[slot] && this.equipment[slot] !== 'none' && this.source.parts[slot + '_' + this.equipment[slot]]) chosen.push(slot + '_' + this.equipment[slot]);
      for (const part of chosen) {
        const f = this.source.parts[part][key];
        for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
          const pixel = y * f.w + x, src = pixel * 4, dst = (f.y + y) * fw + f.x + x;
          if (!f.pixels[src + 3] || f.z[pixel] > nearest[dst]) continue;
          nearest[dst] = f.z[pixel];
          const packed = f.pixels[src] * 65536 + f.pixels[src + 1] * 256 + f.pixels[src + 2];
          const tint = part === 'body' && this.tint.get(packed);
          const lut = this.tintLut.get(part);
          if (lut) {   // a recoloured piece: every colour is painted once and remembered
            let painted = lut.colours.get(packed);
            if (!painted) { painted = [...lut.paint(f.pixels[src], f.pixels[src + 1], f.pixels[src + 2]), 255]; lut.colours.set(packed, painted); }
            out.data.set(painted, dst * 4);
          } else out.data.set(tint ? [...tint, 255] : f.pixels.subarray(src, src + 4), dst * 4);
        }
      }
      g.putImageData(out, 0, 0);
      if (this.cache.size >= 96) this.cache.delete(this.cache.keys().next().value);
      this.cache.set(key, canvas); return canvas;
    }
    draw(g, h, t, scale = 1.3) {
      scale *= this.meta.displayScale || 1;
      const C = this.meta.clips;
      let clip = 'idle', i = Math.floor(t * C.idle.fps) % C.idle.n;
      if (h.dead) { clip = 'die'; i = Math.floor(h.deadT * C.die.fps); }
      else if (h.hurtT > 0) { clip = 'hurt'; i = Math.floor((1 - h.hurtT / .25) * C.hurt.n); }
      else if (h.atkT > 0) { clip = 'attack'; i = Math.floor(h.atkT / this.meta.attack.duration * C.attack.n); }
      else if (h.moving) { clip = 'walk'; i = Math.floor(h.walk) % C.walk.n; }
      const dir = MageSprite.direction(h.fx, h.fy), [ax, ay] = this.meta.anchor;
      g.save(); g.imageSmoothingEnabled = false;
      if (h.dead) g.globalAlpha *= Math.max(0, Math.min(1, (3.2 - h.deadT) / .6));
      g.scale(scale, scale);
      const mark = !h.dead && dungeonMark(this.equipment);
      if (mark) dungeonAura(g, mark, t);
      g.drawImage(this.frame(clip, dir, i), -ax, -ay); g.restore();
    }
    portrait() {
      const c = document.createElement('canvas'); c.width = c.height = 128;
      const g = c.getContext('2d'); g.imageSmoothingEnabled = false;
      g.drawImage(this.frame(), ...(this.meta.portrait || [56, 18, 48, 48]), 0, 0, 128, 128); return c.toDataURL();
    }
    static direction(fx, fy) { return ((Math.round(-Math.atan2(fx - fy, fx + fy) / (Math.PI / 4)) % 8) + 8) % 8; }
    // `background` is for other players' sprites: they load one at a time, after your own, without blocking the page.
    static async load(look, { background = false } = {}) {
      const url = this.METADATA;
      let job = sources.get(url);
      if (!job) {
        job = createJob(background, (slicer, self) => loadSource(url, self));
        sources.set(url, job);
        job.promise.catch(() => { if (sources.get(url) === job) sources.delete(url); });
      } else if (!background) promote(job);
      return new this(await job.promise, look, background);
    }
  }
  MageSprite.GENERIC = GENERIC; MageSprite.hasGear = hasGear; MageSprite.resolveGear = resolve; MageSprite.tintMatrix = tintMatrix;
  MageSprite.DUNGEON_PALETTES = DUNGEON_PALETTES; MageSprite.dungeonMark = dungeonMark; MageSprite.dungeonAura = dungeonAura;
  MageSprite.HAIR = HAIR; MageSprite.SKIN = SKIN; MageSprite.ARMOR = ARMOR; MageSprite.WEAPON = WEAPON;
  MageSprite.equipment = equipment; MageSprite.TIERS = ['apprentice', 'runic'];
  MageSprite.METADATA = 'assets/mage_sprites.txt';
  // Every class has a second atlas set for a female character. `Base.Female` is the same class reading
  // `<class>_f_sprites.txt`, and `Base.variant(look)` picks the one that matches look.gender, so the usual check
  // "is this sprite the right class for this look?" (constructor === class) notices a change of gender as well.
  MageSprite.female = (Base, url) => { const Female = class extends Base {}; Female.METADATA = url; Base.Female = Female; return Female; };
  MageSprite.variant = function (look) { return look?.gender === 'female' && Object.hasOwn(this, 'Female') ? this.Female : this; };
  MageSprite.female(MageSprite, 'assets/mage_f_sprites.txt');
  window.MageSprite = MageSprite;
})();
