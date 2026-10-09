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
  // Head, shoulder and glove pieces are worn per class: the look names a tier (or 'none'), and a class only
  // accepts its own tier names (MageSprite.TIERS). A part the atlas does not have is simply not drawn.
  const SLOT_ORDER = ['armor', 'pants', 'shoulders', 'gloves', 'head', 'necklace', 'accessory', 'weapon'];
  // A head, shoulder or glove piece is the class's own tier or the shared generic piece; pants, necklace and ring are generic only.
  const CLASS_SLOTS = ['head', 'shoulders', 'gloves'];
  const pieces = (C, look) => Object.fromEntries(Object.entries(GENERIC).map(([slot, generic]) => {
    const allowed = [...(CLASS_SLOTS.includes(slot) ? [...(C.TIERS || []), generic] : [generic]), ...PROGRESSION];
    return [slot, allowed.includes(resolve(slot, look?.[slot]).art) ? look[slot] : 'none'];
  }));
  class MageSprite {
    constructor(source, look = {}, background = false) { this.source = source; this.background = background; this.meta = source.meta; this.cache = new Map(); this.set(look); }
    set(look) {
      this.look = { ...look }; this.cache.clear();
      // `worn` holds the catalog variants; `equipment` the drawings they use; `partTint` the recolouring of each drawn part.
      this.worn = { ...pieces(this.constructor, look), ...this.constructor.equipment(look) };
      this.equipment = {}; this.partTint = new Map(); this.tintLut = new Map();
      for (const slot of SLOT_ORDER) {
        const { art, tint } = resolve(slot, this.worn[slot]);
        this.equipment[slot] = art;
        if (tint && art !== 'none') { const key = `${slot}_${art}`; this.partTint.set(key, tint); if (!this.tintLut.has(key)) this.tintLut.set(key, { paint: tintMatrix(tint), colours: new Map() }); }
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
      g.scale(scale, scale); g.drawImage(this.frame(clip, dir, i), -ax, -ay); g.restore();
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
