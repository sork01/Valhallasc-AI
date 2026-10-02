'use strict';
// Independent equipment, composited once per pose and cached. Camera depth
// puts a staff behind the gripping hand and robes behind hair in every facing.
(() => {
  const HAIR = ['#ac78c4', '#d8c89b', '#723b2b', '#42364e', '#bc685c', '#689bb1'];
  const SKIN = ['#ffceb0', '#f0c8a6', '#bd825d', '#875640'];
  const ARMOR = { none: { name: 'Simple cloth', defense: 0 }, apprentice: { name: 'Apprentice robes', defense: 2 }, runic: { name: 'Runic vestments', defense: 5 } };
  const WEAPON = { none: { name: 'Empty hands', attack: 0 }, ash: { name: 'Ash staff', attack: 4 }, crystal: { name: 'Crystal staff', attack: 9 } };
  const sources = new Map();
  const imageData = async url => {
    const img = new Image(); img.src = url; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
    return g.getImageData(0, 0, c.width, c.height);
  };
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
        : solid(ax + 3, ay - 15, 2, 12, () => colour(part), 400);
      parts[part] = new Proxy({}, { get: () => frame });   // the same still figure for every clip, direction and frame
    }
    return { meta, parts };
  }
  async function loadSource(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Character sprite metadata could not be loaded');
    const meta = await response.json(), [fw, fh] = meta.frame, parts = {};
    if (window.__valhallaTestSprites === true) return stubSource(meta);
    // Retain only occupied rectangles; release the large decoded atlases.
    for (const [part, files] of Object.entries(meta.parts)) {
      const [color, depth] = await Promise.all([imageData('assets/' + files.png), imageData('assets/' + files.depth)]);
      const frames = {};
      for (const [clip, C] of Object.entries(meta.clips)) for (let dir = 0; dir < 8; dir++) for (let i = 0; i < C.n; i++) {
        const bx = i * fw, by = (C.row0 + dir) * fh;
        let x0 = fw, y0 = fh, x1 = -1, y1 = -1;
        for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) {
          if (!color.data[((by + y) * color.width + bx + x) * 4 + 3]) continue;
          x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
        }
        const width = Math.max(0, x1 - x0 + 1), height = Math.max(0, y1 - y0 + 1);
        const pixels = new Uint8ClampedArray(width * height * 4), z = new Uint16Array(width * height);
        for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
          const src = ((by + y0 + y) * color.width + bx + x0 + x) * 4, dst = (y * width + x) * 4;
          pixels.set(color.data.subarray(src, src + 4), dst); z[dst / 4] = depth.data[src] * 256 + depth.data[src + 1];
        }
        frames[`${clip}/${dir}/${i}`] = { x: x0, y: y0, w: width, h: height, pixels, z };
      }
      parts[part] = frames;
    }
    return { meta, parts };
  }
  const equipment = look => ({
    armor: Object.hasOwn(ARMOR, look?.mageArmor) ? look.mageArmor : 'apprentice',
    weapon: Object.hasOwn(WEAPON, look?.mageWeapon) ? look.mageWeapon : 'ash',
  });
  class MageSprite {
    constructor(source, look = {}) { this.source = source; this.meta = source.meta; this.cache = new Map(); this.set(look); }
    set(look) {
      this.look = { ...look }; this.equipment = this.constructor.equipment(look); this.cache.clear();
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
      if (this.equipment.armor !== 'none') chosen.push('armor_' + this.equipment.armor);
      if (this.equipment.weapon !== 'none') chosen.push('weapon_' + this.equipment.weapon);
      for (const part of chosen) {
        const f = this.source.parts[part][key];
        for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
          const pixel = y * f.w + x, src = pixel * 4, dst = (f.y + y) * fw + f.x + x;
          if (!f.pixels[src + 3] || f.z[pixel] > nearest[dst]) continue;
          nearest[dst] = f.z[pixel];
          const tint = part === 'body' && this.tint.get(f.pixels[src] * 65536 + f.pixels[src + 1] * 256 + f.pixels[src + 2]);
          out.data.set(tint ? [...tint, 255] : f.pixels.subarray(src, src + 4), dst * 4);
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
    static async load(look) {
      const url = this.METADATA;
      if (!sources.has(url)) sources.set(url, loadSource(url).catch(error => { sources.delete(url); throw error; }));
      return new this(await sources.get(url), look);
    }
  }
  MageSprite.HAIR = HAIR; MageSprite.SKIN = SKIN; MageSprite.ARMOR = ARMOR; MageSprite.WEAPON = WEAPON;
  MageSprite.equipment = equipment;
  MageSprite.METADATA = 'assets/mage_sprites.txt';
  window.MageSprite = MageSprite;
})();
