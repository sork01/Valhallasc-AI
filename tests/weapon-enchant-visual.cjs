// Real class and mount atlases. PREVIEW=1 exports frames for the five class GIFs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const client = path.join(root, 'client');
const out = path.join(root, 'test-results/weapon-enchants');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'world/enchanting.txt'), 'utf8'));
const weapons = catalog.enchants.filter(e => e.kind === 'weapon').map(({ id, name }) => ({ id, name }));
const classes = ['Warrior', 'Mage', 'Assassin', 'Hunter', 'Priest'];
const scripts = ['items', 'weapon-enchant-art', 'magesprite', 'mountart', 'warriorsprite', 'assassinsprite', 'huntersprite', 'priestsprite'];
const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  if (pathname === '/') {
    res.setHeader('Content-Type', 'text/html');
    return res.end(scripts.map(script => '<script src="/' + script + '.js"></script>').join(''));
  }
  const file = path.resolve(client, '.' + decodeURIComponent(pathname));
  if (!file.startsWith(client + path.sep) || !fs.existsSync(file)) {
    res.writeHead(404);
    return res.end();
  }
  const type = { '.js': 'application/javascript', '.png': 'image/png' }[path.extname(file)] || 'text/plain';
  res.setHeader('Content-Type', type);
  fs.createReadStream(file).pipe(res);
});

async function check(page, className) {
  return page.evaluate(async ({ className, weapons, preview }) => {
    const look = { class: className.toLowerCase(), gender: ['Hunter', 'Priest', 'Warrior'].includes(className) ? 'female' : 'male' };
    const Type = window[className + 'Sprite'].variant(look);
    const sprites = await Promise.all(weapons.map(() => Type.load(look)));
    const sprite = sprites[0];
    const part = 'weapon_' + sprite.equipment.weapon;
    await Promise.all([sprite.source.ensure(part), sprite.source.ensure('armor_' + sprite.equipment.armor)]);
    for (const costume of sprites) costume.cache.clear();

    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 240;
    const g = canvas.getContext('2d', { willReadFrequently: true });
    const beginPath = g.beginPath.bind(g);
    let paths = 0;
    g.beginPath = () => { paths++; beginPath(); };
    const paint = (state, time) => {
      g.clearRect(0, 0, canvas.width, canvas.height);
      g.save(); g.translate(120, 182);
      sprite.draw(g, { fx: 1, fy: 1, moving: true, walk: 0, ...state }, time, 1);
      g.restore();
      return g.getImageData(0, 0, canvas.width, canvas.height).data;
    };
    function difference(a, b) {
      let changed = 0;
      for (let i = 0; i < a.length; i += 4) {
        if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2] || a[i + 3] !== b[i + 3]) changed++;
      }
      return changed;
    }
    const plain = paint({}, .4);
    const basePaths = paths;
    const samples = weapons.map(({ id }) => {
      paths = 0;
      const first = paint({ weaponEnchant: id }, .4);
      const next = paint({ weaponEnchant: id }, .9);
      const frame = sprite.frame('walk', 0, 0);
      const art = frame._enchant;
      if (!art) throw Error(className + ' has no glow for ' + id);
      const rgb = art.theme.rgb.join(',');
      return { rgb, glow: difference(first, plain), motion: difference(first, next), paths: paths - 2 * basePaths };
    });
    const removed = difference(plain, paint({ weaponEnchant: null }, .4));
    const death = { dead: true, deadT: .4 };
    const corpse = difference(paint(death, .4), paint({ ...death, weaponEnchant: weapons[0].id }, .4));

    if (!preview) return { samples, removed, corpse };
    const sheet = document.createElement('canvas');
    sheet.width = 960; sheet.height = 248;
    const s = sheet.getContext('2d');
    const frames = [];
    for (let frame = 0; frame < 40; frame++) {
      const t = frame * .08;
      s.fillStyle = '#141a28'; s.fillRect(0, 0, sheet.width, sheet.height);
      s.fillStyle = '#e8eaf5'; s.font = 'bold 19px sans-serif'; s.textAlign = 'left';
      s.fillText('Valhalla Rumble · ' + className, 20, 29);
      for (let i = 0; i < weapons.length; i++) {
        const { id, name } = weapons[i], offset = i * 192, x = offset + 96;
        const theme = WeaponEnchantArt.theme(id), color = 'rgb(' + theme.rgb.join(',') + ')';
        s.fillStyle = i % 2 ? '#252d40' : '#222a3d';
        s.fillRect(offset + 3, 45, 186, 199);
        s.fillStyle = color; s.fillRect(offset + 58, 221, 76, 2);
        s.fillStyle = '#eef0fa'; s.font = 'bold 15px sans-serif'; s.textAlign = 'center';
        s.fillText(name, x, 239);
        const attacking = t >= 1.36 && t < 1.36 + sprites[i].meta.attack.duration;
        s.save(); s.translate(x, 200);
        s.fillStyle = '#161c2b'; s.beginPath(); s.ellipse(0, 2, 22, 7, 0, 0, Math.PI * 2); s.fill();
        sprites[i].draw(s, { fx: t >= 1.92 && t < 2.72 ? 0 : 1, fy: 1,
          atkT: attacking ? t - 1.36 + .01 : 0, weaponEnchant: id }, t + .37, 1.16);
        s.restore();
      }
      frames.push(sheet.toDataURL('image/png').split(',')[1]);
    }
    return { samples, removed, corpse, frames };
  }, { className, weapons, preview: process.env.PREVIEW === '1' });
}

async function checkPoseAndMount(page) {
  return page.evaluate(async () => {
    const look = { class: 'warrior', gender: 'female', race: 'gnome' };
    const sprite = await WarriorSprite.variant(look).load(look);
    await sprite.source.ensure('weapon_' + sprite.equipment.weapon);
    const g = document.createElement('canvas').getContext('2d');
    const actor = { fx: 1, fy: 1, weaponEnchant: 'lightning_rod' };
    sprite.draw(g, actor, 0);
    const attack = sprite.frame('attack', 2, 2), idle = sprite.frame('idle', 0, 0);
    const overlap = idle._enchant.mask.reduce((count, pixel, i) => count + Number(pixel && attack._enchant.mask[i]), 0);
    const points = idle._enchant.mask.reduce((sum, pixel) => sum + pixel, 0);
    const { glow, left, top, mask } = idle._enchant;
    const aura = glow.getContext('2d').getImageData(0, 0, glow.width, glow.height).data;
    let bleed = 0;
    for (let y = 0; y < glow.height; y++) for (let x = 0; x < glow.width; x++) {
      const p = (y + top) * idle.width + x + left;
      if (!mask[p] && idle._px[p * 4 + 3] && aura[(y * glow.width + x) * 4 + 3]) bleed++;
    }
    const timeout = performance.now() + 12000;
    while (!MountArt.ready('horse') && performance.now() < timeout) await new Promise(resolve => setTimeout(resolve, 40));
    if (!MountArt.ready('horse')) throw Error('horse atlas never loaded');
    const mounted = { ...actor, mounted: true, mount: 'horse' };
    sprite.draw(g, mounted, 0);
    const saddle = sprite.cache.get('mount/horse/0/idle/0/0/0');
    const mountedPoints = saddle?._enchant?.points.length || 0;
    sprite.draw(g, { ...mounted, weaponEnchant: null }, 0);
    const removed = sprite.cache.get('mount/horse/0/idle/0/0/0')?._enchant == null;
    return { overlap, points, bleed, mountedPoints, removed };
  });
}

(async () => {
  assert.match(fs.readFileSync(path.join(client, 'index.html'), 'utf8'), /<script src="weapon-enchant-art\.js"><\/script>/);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = 'http://127.0.0.1:' + server.address().port;
  try {
    const requested = process.env.CLASS ? [process.env.CLASS] : classes;
    for (const className of requested) {
      assert.ok(classes.includes(className), 'unknown class ' + className);
      const browser = await chromium.launch({ headless: true });
      try {
        const page = await browser.newPage({ reducedMotion: 'no-preference' });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        if (process.env.MUTATE === 'particles') {
          const source = fs.readFileSync(path.join(client, 'weapon-enchant-art.js'), 'utf8');
          const body = source.replace('if (!still) {', 'if (false) {');
          assert.notEqual(body, source);
          await page.route('**/weapon-enchant-art.js', route => route.fulfill({ contentType: 'application/javascript', body }));
        }
        await page.goto(origin);
        const result = await check(page, className);
        assert.ok(result.samples.every(sample => sample.glow > 150), className + ' shows all weapon glows');
        assert.equal(new Set(result.samples.map(sample => sample.rgb)).size, weapons.length);
        if (className === 'Warrior') {
          await page.emulateMedia({ reducedMotion: 'reduce' });
          const reduced = await page.evaluate(async id => {
            const sprite = await WarriorSprite.load({ class: 'warrior' });
            await sprite.source.ensure('weapon_' + sprite.equipment.weapon);
            const c = document.createElement('canvas'); c.width = c.height = 200;
            const g = c.getContext('2d', { willReadFrequently: true });
            const pose = { fx: 1, fy: 1, moving: true, walk: 0, weaponEnchant: id };
            const draw = t => {
              g.clearRect(0, 0, 200, 200); g.save(); g.translate(100, 175);
              sprite.draw(g, pose, t, 1);
              g.restore(); return c.toDataURL();
            };
            const initial = draw(.4), next = draw(.9);
            pose.weaponEnchant = null;
            return { static: initial === next, visible: initial !== draw(.4) };
          }, weapons[0].id);
          assert.deepEqual(reduced, { static: true, visible: true }, 'reduced motion keeps the glow steady');
          const pose = await checkPoseAndMount(page);
          assert.ok(pose.overlap < pose.points * .7, 'glow moves to the weapon in the attack facing');
          assert.equal(pose.bleed, 0, 'halo stays off armor and skin');
          assert.ok(pose.mountedPoints > 0 && pose.removed, 'mounted glow follows the rider and clears on removal');
        }
        assert.ok(result.samples.every(sample => sample.motion > 100 && sample.paths > 0), className + ' shows animated particles');
        assert.equal(result.removed, 0, className + ' clears the glow when the enchant is removed');
        assert.equal(result.corpse, 0, className + ' clears the glow on death');
        assert.deepEqual(errors, []);
        if (result.frames) {
          const dir = path.join(out, className.toLowerCase());
          fs.mkdirSync(dir, { recursive: true });
          result.frames.forEach((frame, i) => {
            fs.writeFileSync(path.join(dir, String(i).padStart(3, '0') + '.png'), Buffer.from(frame, 'base64'));
          });
        }
        console.log(className + ' weapon enchant effects passed');
      } finally {
        await browser.close();
      }
    }
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
