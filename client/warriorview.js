'use strict';
/* The Warrior for character creation: one painted image (assets/warrior.webp, cut out of the
   supplied art) brought to life with a WebGL mesh warp, so it moves without ghosting or holes.
     - idle: breathing, head sway that follows the pointer, beard sway, axe drift, rune pulse
     - reactions (click/tap the axe, mug, head, beard, fish or body): attack, cheers, laugh, ...
     - customisation by colour masks (assets/warrior_mask.png: R = hair/beard, G = skin, B = armour)
   Coordinates below are UVs of the cropped image (0,0 top-left). If you swap the art, re-measure the
   feature positions: the region functions exist twice (GLSL for drawing, JS `hit()` for clicks). */
(() => {
  const ASPECT = 900 / 1180;          // texture width / height
  const S = 0.9;                      // how much of the canvas the image fills (room for the swing)
  const YSHIFT = 0.9;

  const OPTS = {
    hairColors: [null, '#e6a83c', '#2b2b34', '#c9d2e0', '#3a7bd5', '#f0609c'],          // null = original red
    hairSwatch: ['#c0501e', '#e6a83c', '#2b2b34', '#c9d2e0', '#3a7bd5', '#f0609c'],
    hairGain: [1, 2.4, 1, 2.0, 1.6, 1.8],
    skinColors: [null, '#f4cbb0', '#d9a070', '#a06a44', '#6a4028'],
    skinSwatch: ['#f0a386', '#f4cbb0', '#d9a070', '#a06a44', '#6a4028'],
    armorHues: [0, 2.58, -2.49],                                                       // radians (YIQ): crimson, azure, verdant
    runeHues: [0, .65, -1.59, 2.5, -2.89],                                                 // cyan, green, violet, gold, red
    runeSwatch: ['#59d9ff', '#5be08a', '#a06bff', '#f5c542', '#ff5f7e'],
    armors: 3,
  };

  // ---- shared GLSL: region shapes in isometric UV space ----
  const COMMON = `
    uniform float uAspect;
    vec2 iso(vec2 p){ return vec2(p.x * uAspect, p.y); }
    float circ(vec2 p, vec2 c, float r0, float r1){ return 1.0 - smoothstep(r0, r1, distance(iso(p), iso(c))); }
    float seg(vec2 p, vec2 a, vec2 b, float r0, float r1){
      vec2 pa = iso(p) - iso(a), ba = iso(b) - iso(a);
      float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
      return 1.0 - smoothstep(r0, r1, length(pa - ba * h));
    }
    float headM(vec2 p){ return circ(p, vec2(.54, .20), .10, .19) * smoothstep(.46, .30, p.y); }
    float beardM(vec2 p){ return seg(p, vec2(.52, .30), vec2(.48, .52), .05, .12) * smoothstep(.27, .55, p.y); }
    float axeM(vec2 p){ return max(seg(p, vec2(.042, .414), vec2(.715, .195), .04, .08), circ(p, vec2(.763, .127), .19, .27)) * (1.0 - .9 * headM(p)); }
    float mugM(vec2 p){ return circ(p, vec2(.632, .536), .085, .13); }
    float fishM(vec2 p){ vec2 q = vec2((p.x - .31) * uAspect / .17, (p.y - .69) / .055); return 1.0 - smoothstep(.8, 1.5, length(q)); }
  `;
  const VERT = `
    precision mediump float;
    attribute vec2 aUv;
    uniform float uT, uSwing, uLean, uLunge, uJump, uSquash, uLaugh, uBeard, uMug, uFish, uS, uYS;
    uniform vec2 uLook;
    varying vec2 vUv;
    ${COMMON}
    vec2 uniso(vec2 d){ return vec2(d.x / uAspect, d.y); }
    vec2 rot(vec2 v, float a){ float c = cos(a), s = sin(a); return vec2(c * v.x - s * v.y, s * v.x + c * v.y); }
    void main(){
      vec2 p = aUv, d = vec2(0.0);
      float stool = (1.0 - smoothstep(.54, .60, p.x)) * smoothstep(.62, .68, p.y);
      float body = smoothstep(.88, .58, p.y) * (1.0 - stool);
      float br = sin(uT * 1.9);
      d.y -= (.86 - p.y) * .007 * br * body;
      d.x += (p.x - .55) * .004 * br * body;
      d.y += (p.y - .86) * uSquash * body;
      d.x -= (p.x - .55) * uSquash * .5 * body;
      d.y -= uJump * body;
      d.x += uLunge * .05 * body * smoothstep(.85, .35, p.y);
      vec2 hip = vec2(.55, .72);
      d += uniso(rot(iso(p) - iso(hip), uLean) - (iso(p) - iso(hip))) * body;
      // head: follows the pointer, shakes when laughing
      float hm = headM(p);
      vec2 neck = vec2(.54, .30);
      float ha = uLook.x * .07 + sin(uT * 1.2) * .012 + sin(uT * 24.0) * uLaugh * .035;
      d += uniso(rot(iso(p) - iso(neck), ha) - (iso(p) - iso(neck))) * hm;
      d.y -= (abs(sin(uT * 13.0)) * uLaugh * .007 + uLook.y * .006) * hm;
      // beard
      float bm = beardM(p);
      d.x += bm * (sin(uT * 2.0 + p.y * 8.0) * .004 + uBeard * sin(uT * 20.0 - p.y * 12.0) * .022 + uLaugh * sin(uT * 22.0) * .006);
      d.y += bm * uLaugh * sin(uT * 20.0) * .004;
      // axe: rotates about the shoulder it rests on
      vec2 pivot = vec2(.66, .28);
      float aa = uSwing + sin(uT * 1.3) * .012;
      d += uniso(rot(iso(p) - iso(pivot), aa) - (iso(p) - iso(pivot))) * axeM(p);
      // mug
      float mm = mugM(p);
      vec2 mp = vec2(.632, .56);
      d += uniso(rot(iso(p) - iso(mp), -.25 * uMug) - (iso(p) - iso(mp))) * mm;
      d += vec2(-.045, -.075) * uMug * mm;
      // fish
      float fm = fishM(p);
      d.y += fm * sin(uT * 18.0 + p.x * 26.0) * .008 * uFish * smoothstep(.45, .12, p.x);
      d.y -= fm * uFish * .012 * abs(sin(uT * 9.0));
      vec2 pp = p + d;
      gl_Position = vec4((pp.x - .5) * 2.0 * uS, -(pp.y - .5) * 2.0 * uS - (1.0 - uS) * uYS, 0.0, 1.0);
      vUv = aUv;
    }`;
  const FRAG = `
    precision mediump float;
    varying vec2 vUv;
    uniform sampler2D uTex, uMask;
    uniform vec3 uHair, uSkin;
    uniform float uHairAmt, uHairGain, uSkinAmt, uArmorHue, uRuneHue, uT, uHover, uFlash, uRuneBoost;
    ${COMMON}
    vec3 hueRot(vec3 c, float a){
      const mat3 toYIQ = mat3(.299, .596, .211, .587, -.274, -.523, .114, -.322, .312);
      const mat3 toRGB = mat3(1.0, 1.0, 1.0, .956, -.272, -1.106, .621, -.647, 1.703);
      vec3 y = toYIQ * c; float cs = cos(a), sn = sin(a);
      y.yz = vec2(y.y * cs - y.z * sn, y.y * sn + y.z * cs);
      return clamp(toRGB * y, 0.0, 1.0);
    }
    void main(){
      vec4 c = texture2D(uTex, vUv);
      if (c.a < .004) { gl_FragColor = vec4(0.0); return; }
      vec3 col = c.rgb / c.a;
      vec3 m = texture2D(uMask, vUv).rgb;
      float lum = dot(col, vec3(.299, .587, .114));
      float mx = max(col.r, max(col.g, col.b)), mn = min(col.r, min(col.g, col.b));
      float sat = (mx - mn) / max(mx, .001);
      float cy = smoothstep(.12, .35, (col.g + col.b) * .5 - col.r) * step(.5, mx) * smoothstep(.3, .5, sat);
      if (uHairAmt > .001) col = mix(col, clamp(uHair * (lum * uHairGain + .06), 0.0, 1.0), m.r * uHairAmt);
      if (uSkinAmt > .001) col = mix(col, clamp(uSkin * (lum / .62), 0.0, 1.0), m.g * uSkinAmt);
      if (abs(uArmorHue) > .001) col = mix(col, hueRot(col, uArmorHue), m.b);
      col = mix(col, hueRot(col, uRuneHue), cy);
      vec3 rc = hueRot(vec3(.35, .9, 1.0), uRuneHue);
      col += rc * cy * (.22 + .22 * sin(uT * 3.0) + uRuneBoost);
      // hover highlight
      float hv = 0.0;
      if (uHover > 4.5) hv = fishM(vUv); else if (uHover > 3.5) hv = mugM(vUv); else if (uHover > 2.5) hv = beardM(vUv) * 1.4; else if (uHover > 1.5) hv = headM(vUv); else if (uHover > .5) hv = axeM(vUv);
      col += vec3(.10, .09, .05) * hv;
      col += uFlash * .45;
      gl_FragColor = vec4(clamp(col, 0.0, 1.0) * c.a, c.a);
    }`;

  const ease = x => x * x * (3 - 2 * x);
  // piecewise-smooth curve through [t, value] keys
  const curve = (keys, t) => {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) { const [t0, v0] = keys[i - 1], [t1, v1] = keys[i]; return v0 + (v1 - v0) * ease((t - t0) / (t1 - t0)); }
    return keys[keys.length - 1][1];
  };

  class WarriorView {
    constructor(canvas, onEvent) {
      this.cv = canvas; this.onEvent = onEvent || (() => {});
      this.cfg = { hairColor: 0, skin: 0, armor: 0, rune: 0 };
      this.look = [0, 0]; this.lookT = [0, 0]; this.hover = 0;
      this.events = []; this.ok = false; this.active = false; this.reduced = false;
      this.swing = 0;
      const gl = canvas.getContext('webgl', { premultipliedAlpha: true, alpha: true, antialias: true }) || canvas.getContext('experimental-webgl');
      if (!gl) return;
      this.gl = gl;
      const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
      try {
        const pr = gl.createProgram();
        gl.attachShader(pr, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FRAG));
        gl.linkProgram(pr);
        if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
        this.pr = pr;
      } catch (e) { console.warn('warrior shader', e); return; }
      gl.useProgram(this.pr);
      this.u = n => gl.getUniformLocation(this.pr, n);
      // mesh
      const NX = 44, NY = 58, uv = [], idx = [];
      for (let y = 0; y <= NY; y++) for (let x = 0; x <= NX; x++) uv.push(x / NX, y / NY);
      for (let y = 0; y < NY; y++) for (let x = 0; x < NX; x++) { const a = y * (NX + 1) + x, b = a + 1, c = a + NX + 1, d = c + 1; idx.push(a, b, c, b, d, c); }
      this.count = idx.length;
      const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(uv), gl.STATIC_DRAW);
      const loc = gl.getAttribLocation(this.pr, 'aUv'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      const ib = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);
      gl.uniform1f(this.u('uAspect'), ASPECT); gl.uniform1f(this.u('uS'), S); gl.uniform1f(this.u('uYS'), YSHIFT);
      gl.clearColor(0, 0, 0, 0);
      this.ok = true;
    }

    load(texUrl, maskUrl) {
      if (!this.ok) return Promise.resolve(false);
      const img = u => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = u; });
      return Promise.all([img(texUrl), img(maskUrl)]).then(([a, m]) => {
        const gl = this.gl;
        const mk = (unit, image, premul) => {
          const t = gl.createTexture(); gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, t);
          gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, premul);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        };
        mk(0, a, true); mk(1, m, false);
        gl.uniform1i(this.u('uTex'), 0); gl.uniform1i(this.u('uMask'), 1);
        // a tiny alpha map so clicks on empty space do nothing
        const c = document.createElement('canvas'); c.width = 90; c.height = 118;
        const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(a, 0, 0, 90, 118);
        this.alpha = x.getImageData(0, 0, 90, 118).data;
        this.loaded = true; this.resize(); this.render(performance.now() / 1000);
        return true;
      });
    }

    set(cfg) { Object.assign(this.cfg, cfg); }

    resize(force) {
      if (!this.ok) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = force ? force[0] : Math.max(2, Math.round(this.cv.clientWidth * dpr)), h = force ? force[1] : Math.max(2, Math.round(this.cv.clientHeight * dpr));
      if (this.cv.width !== w || this.cv.height !== h) { this.cv.width = w; this.cv.height = h; }
      this.gl.viewport(0, 0, w, h);
    }

    // ---- coordinates ----
    uvToClient(u, v) {
      const r = this.cv.getBoundingClientRect();
      const nx = (u - .5) * 2 * S, ny = -(v - .5) * 2 * S - (1 - S) * YSHIFT;
      return [r.left + (nx + 1) / 2 * r.width, r.top + (1 - ny) / 2 * r.height];
    }
    clientToUv(x, y) {
      const r = this.cv.getBoundingClientRect();
      const nx = (x - r.left) / r.width * 2 - 1, ny = 1 - (y - r.top) / r.height * 2;
      return [nx / (2 * S) + .5, -((ny + (1 - S) * YSHIFT) / (2 * S)) + .5];
    }
    anchor(name) {
      const A = { blade: [.76, .13], pivot: [.66, .28], mug: [.632, .47], head: [.54, .2], fish: [.3, .69], feet: [.55, .9], body: [.55, .5] }[name] || [.5, .5];
      let [u, v] = A;
      if (name === 'blade') {             // follow the swing
        const a = this.swing || 0, px = .66 * ASPECT, py = .28, bx = (u - .66) * ASPECT, by = v - .28;
        u = (px + bx * Math.cos(a) - by * Math.sin(a)) / ASPECT; v = py + bx * Math.sin(a) + by * Math.cos(a);
      }
      return this.uvToClient(u, v);
    }
    // the arc the blade sweeps, for the slash effect: centre, radius and start angle in client px
    slashGeometry() {
      const [cx, cy] = this.uvToClient(.66, .28), [bx, by] = this.uvToClient(.76, .13);
      return { cx, cy, r: Math.hypot(bx - cx, by - cy), a0: Math.atan2(by - cy, bx - cx) };
    }

    hit(u, v) {
      const d = (x, y) => Math.hypot((u - x) * ASPECT, v - y);
      const seg = (ax, ay, bx, by) => { const px = (u - ax) * ASPECT, py = v - ay, qx = (bx - ax) * ASPECT, qy = by - ay; const h = Math.max(0, Math.min(1, (px * qx + py * qy) / (qx * qx + qy * qy))); return Math.hypot(px - qx * h, py - qy * h); };
      if (d(.632, .536) < .11) return 'mug';
      if (Math.hypot((u - .31) * ASPECT / .19, (v - .69) / .06) < 1) return 'fish';
      if (d(.54, .21) < .115) return 'head';
      if (seg(.52, .30, .48, .54) < .07) return 'beard';
      if (seg(.042, .414, .715, .195) < .055 || d(.763, .127) < .2) return 'axe';
      if (this.alpha && u >= 0 && u < 1 && v >= 0 && v < 1 && this.alpha[(Math.floor(v * 118) * 90 + Math.floor(u * 90)) * 4 + 3] > 40) return 'body';
      return null;
    }
    static code(n) { return { axe: 1, head: 2, beard: 3, mug: 4, fish: 5 }[n] || 0; }

    // ---- input ----
    bind() {
      const cv = this.cv;
      cv.addEventListener('pointermove', e => {
        const [u, v] = this.clientToUv(e.clientX, e.clientY);
        this.lookT = [Math.max(-1, Math.min(1, (u - .54) * 3)), Math.max(-1, Math.min(1, (v - .2) * 3))];
        const h = this.hit(u, v); this.hover = WarriorView.code(h); cv.style.cursor = h ? 'pointer' : 'default';
      });
      cv.addEventListener('pointerleave', () => { this.lookT = [0, 0]; this.hover = 0; });
      cv.addEventListener('click', e => {
        const [u, v] = this.clientToUv(e.clientX, e.clientY), h = this.hit(u, v);
        if (h) this.play({ axe: 'attack', mug: 'cheers', head: 'laugh', beard: 'beard', fish: 'fish', body: 'flex' }[h]);
      });
    }

    play(type) {
      const dur = { attack: 1.6, cheers: 2.0, laugh: 1.5, beard: 1.3, fish: 1.1, flex: .9 }[type] || 1;
      this.events.push({ type, t0: performance.now() / 1000, dur, fired: {} });
      this.onEvent(type + ':start');
    }

    // ---- per frame ----
    frame(t) {
      const gl = this.gl;
      let swing = 0, lean = 0, lunge = 0, jump = 0, squash = 0, laugh = 0, beard = 0, mug = 0, fish = 0, flash = 0, boost = 0;
      const fire = (ev, key, p, at) => { if (p >= at && !ev.fired[key]) { ev.fired[key] = 1; this.onEvent(ev.type + ':' + key); } };
      this.events = this.events.filter(ev => t - ev.t0 < ev.dur);
      for (const ev of this.events) {
        const p = (t - ev.t0) / ev.dur;
        switch (ev.type) {
          case 'attack':
            swing += curve([[0, 0], [.14, .10], [.30, -.16], [.38, -.18], [.68, -.04], [1, 0]], p);
            lean += curve([[0, 0], [.15, .05], [.31, -.10], [.42, -.09], [.7, -.02], [1, 0]], p);
            lunge += curve([[0, 0], [.16, -.4], [.32, 1], [.6, .2], [1, 0]], p);
            jump += curve([[0, 0], [.3, .012], [.4, 0], [1, 0]], p);
            boost += curve([[0, 0], [.3, .9], [.7, .2], [1, 0]], p);
            flash += p > .28 && p < .5 ? (1 - (p - .28) / .22) * .5 : 0;
            fire(ev, 'shout', p, .1); fire(ev, 'strike', p, .3);
            break;
          case 'cheers':
            mug += curve([[0, 0], [.22, 1], [.6, 1], [.85, 0], [1, 0]], p);
            laugh += curve([[0, 0], [.35, 0], [.45, .9], [.8, .9], [1, 0]], p);
            fire(ev, 'clink', p, .25); fire(ev, 'laugh', p, .4);
            break;
          case 'laugh':
            laugh += Math.sqrt(Math.sin(Math.PI * p)); beard += (1 - p) * .6;
            jump += Math.abs(Math.sin(p * 18)) * .004 * (1 - p);
            fire(ev, 'laugh', p, .02);
            break;
          case 'beard': beard += 1 - p; fire(ev, 'hmm', p, .05); break;
          case 'fish': fish += 1 - p; fire(ev, 'splash', p, .05); break;
          case 'flex':
            squash += curve([[0, 0], [.2, .05], [.45, -.03], [1, 0]], p);
            jump += curve([[0, 0], [.2, 0], [.5, .05], [.85, 0], [1, 0]], p);
            fire(ev, 'grunt', p, .4);
            break;
        }
      }
      if (this.reduced) { swing = lean = lunge = jump = squash = 0; }
      this.swing = swing;
      this.look[0] += (this.lookT[0] - this.look[0]) * .1; this.look[1] += (this.lookT[1] - this.look[1]) * .1;
      const u = this.u;
      gl.uniform1f(u('uT'), this.reduced ? 0 : t % 1000); gl.uniform1f(u('uSwing'), swing); gl.uniform1f(u('uLean'), lean); gl.uniform1f(u('uLunge'), lunge); gl.uniform1f(u('uJump'), jump);
      gl.uniform1f(u('uSquash'), squash); gl.uniform1f(u('uLaugh'), Math.min(1, laugh)); gl.uniform1f(u('uBeard'), Math.min(1.5, beard)); gl.uniform1f(u('uMug'), mug); gl.uniform1f(u('uFish'), fish);
      gl.uniform2f(u('uLook'), this.reduced ? 0 : this.look[0], this.reduced ? 0 : this.look[1]);
      gl.uniform1f(u('uHover'), this.hover); gl.uniform1f(u('uFlash'), flash); gl.uniform1f(u('uRuneBoost'), boost + (this.hover === 1 ? .35 : 0));
      const c = this.cfg, hc = OPTS.hairColors[c.hairColor], sk = OPTS.skinColors[c.skin];
      const rgb = h => { const n = parseInt(h.slice(1), 16); return [(n >> 16) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]; };
      const hv = hc ? rgb(hc) : [1, 1, 1]; gl.uniform3f(u('uHair'), hv[0], hv[1], hv[2]); gl.uniform1f(u('uHairAmt'), hc ? 1 : 0); gl.uniform1f(u('uHairGain'), OPTS.hairGain[c.hairColor] || 1.5);
      const sv = sk ? rgb(sk) : [1, 1, 1]; gl.uniform3f(u('uSkin'), sv[0], sv[1], sv[2]); gl.uniform1f(u('uSkinAmt'), sk ? 1 : 0);
      gl.uniform1f(u('uArmorHue'), OPTS.armorHues[c.armor] || 0); gl.uniform1f(u('uRuneHue'), OPTS.runeHues[c.rune] || 0);
    }
    render(t, force) {
      if (!this.ok || !this.loaded) return;
      this.resize(force); this.frame(t);
      const gl = this.gl; gl.clear(gl.COLOR_BUFFER_BIT); gl.drawElements(gl.TRIANGLES, this.count, gl.UNSIGNED_SHORT, 0);
    }
    setActive(on) {
      if (on === this.active) return; this.active = on;
      if (!on) return;
      const loop = () => { if (!this.active) return; this.render(performance.now() / 1000); requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
    }
    // works while the canvas is hidden (its CSS size is 0 then), so it renders at a fixed size
    snapshot() { this.render(performance.now() / 1000, [600, Math.round(600 / ASPECT)]); return this.cv.toDataURL('image/png'); }
  }

  window.WarriorView = WarriorView;
  window.WARRIOR_OPTS = OPTS;
  window.WARRIOR_GEOM = { ASPECT, S, YSHIFT };
})();
