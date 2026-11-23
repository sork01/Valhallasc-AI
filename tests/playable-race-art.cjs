const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const { requireMemoryLimit } = require('./lib/touch.cjs');

requireMemoryLimit();
const client = path.resolve(__dirname, '../client');
const output = path.resolve(__dirname, '../test-results');
const classes = ['Mage', 'Hunter', 'Warrior', 'Assassin', 'Priest'];
const designs = [
  { race: 'mothkin', name: 'Neris', label: 'Mothkin Hunter · The Moonspore Canopy', job: 'Hunter', body: 'female',
    marking: [240, 223, 208], colors: ['#3b3455', '#111523', '#f1dfeb', '#c6b6d5', '#181827', '#746387', '#ded1e9'] },
  { race: 'tidekin', name: 'Eydan', label: 'Tidekin Mage · Rán’s Deep', job: 'Mage', body: 'male',
    marking: [241, 243, 223], colors: ['#244852', '#0d1c28', '#e4f6ec', '#a8cfc5', '#122730', '#5e8a85', '#d0e6e1'] },
  { race: 'gnome', name: 'Tavi', label: 'Assassin · The Obsidian Orrery', job: 'Assassin', body: 'female',
    marking: [234, 182, 102], size: [.76, .67] },
];
const selected = designs.filter(design => process.argv.includes('--' + design.race));
const races = selected.length ? selected : designs;
const previewOnly = process.argv.includes('--preview-only');
const server = http.createServer((req, res) => {
  if (req.url === '/') {
    res.setHeader('Content-Type', 'text/html');
    const scripts = ['items', 'magesprite', 'mountart', ...classes.filter(name => name !== 'Mage').map(name => name.toLowerCase() + 'sprite')];
    return res.end('<!doctype html>' + scripts.map(name => '<script src="' + name + '.js"></script>').join(''));
  }
  const file = path.resolve(client, '.' + req.url);
  if (!file.startsWith(client + path.sep) || !fs.existsSync(file)) return res.writeHead(404).end();
  res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  const stream = fs.createReadStream(file);
  stream.once('error', error => res.destroy(error));
  stream.pipe(res);
});

(async () => {
  let browser;
  try {
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    browser = await chromium.launch({ headless: true });
    let poses = 0;
    for (const name of classes) {
      for (const gender of ['female', 'male']) {
        const chosen = races.filter(design => !previewOnly || (design.job === name && design.body === gender));
        if (!chosen.length) continue;
        const page = await browser.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const faults = {
          features: ['if (showFeatures && features', 'if (false && features'],
          antennae: ['if (showFeatures && features', 'if (false && features'],
          scale: ['g.scale(...this.bodyScale);', 'g.scale(1, 1);'],
          mount: ['h.mountTint || 0, this.bodyScale);', 'h.mountTint || 0);'],
        };
        const fault = faults[process.env.MUTATE];
        if (fault) {
          const source = fs.readFileSync(path.join(client, 'magesprite.js'), 'utf8');
          assert.ok(source.includes(fault[0]));
          await page.route('**/magesprite.js', route => route.fulfill({
            contentType: 'text/javascript', body: source.replace(...fault),
          }));
        }
        await page.goto('http://127.0.0.1:' + server.address().port);
        const result = await page.evaluate(async ({ name, gender, chosen }) => {
          const fail = message => { throw Error(name + '/' + gender + ': ' + message); };
          const cls = name.toLowerCase(), Base = window[name + 'Sprite'];
          const look = { class: cls, gender, hairColor: (cls === 'hunter' || cls === 'mage') ? 5 : 0, skin: 0 };
          const C = Base.variant(look), sprite = await C.load(look);
          for (const slot of ['armor', 'weapon']) {
            const part = slot + '_' + sprite.equipment[slot];
            await sprite.source.ensure(part);
            if (!sprite.source.parts[part]) fail('missing starter layer ' + part);
          }
          const frames = (race, head = 'none') => {
            const pixels = [];
            sprite.set({ ...look, race, head });
            for (const [clip, info] of Object.entries(sprite.meta.clips)) {
              for (let dir = 0; dir < 8; dir++) for (let i = 0; i < info.n; i++)
                pixels.push({ clip, dir, i, px: sprite.frame(clip, dir, i)._px });
            }
            return pixels;
          };
          const ordinary = frames(undefined), human = frames('human');
          for (let i = 0; i < ordinary.length; i++) {
            const previous = ordinary[i].px, explicit = human[i].px;
            for (let j = 0; j < previous.length; j++) {
              if (explicit[j] !== previous[j]) fail('legacy look differs from Human');
            }
          }
          const helm = C.TIERS[0], headPart = 'head_' + helm;
          sprite.set({ ...look, race: 'human', head: helm });
          await sprite.source.ensure(headPart);
          sprite.cache.clear();
          if (!sprite.source.parts[headPart]) fail('starter headgear did not load');
          const hattedHuman = sprite.frame()._px;

          const hero = (dir, state = {}) => {
            const angle = dir * Math.PI / 4;
            return { fx: Math.cos(angle) - Math.sin(angle), fy: Math.cos(angle) + Math.sin(angle), ...state };
          };

          function verifySize(race, size) {
            const canvas = document.createElement('canvas'), g = canvas.getContext('2d');
            const [ax, ay] = sprite.meta.anchor, display = sprite.meta.displayScale || 1;
            let draws = 0;
            g.drawImage = (frame, x, y) => {
              const { a, d, e, f } = g.getTransform();
              if (Math.abs(a - display * size[0]) > 1e-6 || Math.abs(d - display * size[1]) > 1e-6)
                fail(race + ' equipped sprite has the wrong scale');
              if (x !== -ax || y !== -ay || e !== 0 || f !== 0) fail(race + ' sprite shifted from its feet');
              if (g.imageSmoothingEnabled) fail(race + ' scaling blurred the sprite');
              draws++;
            };
            sprite.set({ ...look, race });
            const states = [{}, { moving: true, walk: 3 }, { atkT: .22 }, { hurtT: .12 }, { isCorpse: true }];
            for (let dir = 0; dir < 8; dir++) for (const state of states) sprite.draw(g, hero(dir, state), 0, 1);
            if (draws !== 40) fail(race + ' did not draw all five clips in all eight directions');
          }

          async function verifyMounts(design) {
            const art = window.MountArt, [fw, fh] = sprite.meta.frame;
            const blank = { _px: new Uint8ClampedArray(fw * fh * 4), _z: new Uint16Array(fw * fh) };
            const pixels = canvas => new Uint32Array(canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data.buffer);
            const topOfRider = (bare, composite) => Math.floor(composite.findIndex((value, i) => value !== bare[i]) / fw);
            let checked = 0;
            sprite.set({ ...look, race: design.race });
            for (const id of ['horse', 'seahorse']) {
              const start = performance.now();
              while (!art.ready(id)) {
                if (performance.now() - start > 15000) fail(id + ' mount did not load');
                await new Promise(resolve => setTimeout(resolve, 50));
              }
              for (const [clip, frame] of [['idle', 0], ['run', 3]]) for (let dir = 0; dir < 8; dir++) {
                const rider = sprite.frame('idle', dir, 0);
                const bare = pixels(art.compose(blank, id, clip, dir, frame, 0));
                const adjusted = pixels(art.compose(blank, id, clip, dir, frame, 0, design.size));
                if (!adjusted.every((value, i) => value === bare[i])) fail(id + ' mount changed size with no rider');
                const normal = pixels(art.compose(rider, id, clip, dir, frame, 0));
                const short = pixels(art.compose(rider, id, clip, dir, frame, 0, design.size));
                const normalTop = topOfRider(bare, normal), shortTop = topOfRider(bare, short);
                if (normalTop < 0 || shortTop < normalTop + 6)
                  fail(id + '/' + clip + '/' + dir + ' rider was missing or the height did not shrink around the saddle');
                checked++;
              }
            }
            const compose = art.compose;
            const g = document.createElement('canvas').getContext('2d');
            let drawn = false;
            g.drawImage = () => {
              const { a, d } = g.getTransform(), display = sprite.meta.displayScale || 1;
              if (a !== display || d !== display) fail('the mounted drawing scaled the mount along with its rider');
              drawn = true;
            };
            art.compose = (...args) => {
              if (!design.size.every((value, i) => args[6]?.[i] === value))
                fail('mounted drawing did not pass the race scale to the rider compositor');
              return compose(...args);
            };
            try { sprite.draw(g, hero(0, { mounted: true, mount: 'horse' }), 0, 1); }
            finally { art.compose = compose; }
            if (!drawn) fail('mounted sprite was not drawn');
            return checked;
          }

          function renderComparison(design) {
            const canvas = document.createElement('canvas');
            canvas.width = 1216; canvas.height = 568;
            const g = canvas.getContext('2d');
            const background = g.createRadialGradient(608, 286, 50, 608, 286, 660);
            background.addColorStop(0, '#352a44'); background.addColorStop(1, '#181524');
            g.fillStyle = background; g.fillRect(0, 0, canvas.width, canvas.height);
            g.textAlign = 'center'; g.fillStyle = '#f8e6d1'; g.font = 'bold 34px Georgia';
            g.fillText(design.name + ', Gnome of the Obsidian Orrery', 608, 52);
            g.fillStyle = '#ccb6ab'; g.font = '16px system-ui';
            g.fillText('Assassin · matching equipment', 608, 82);
            g.strokeStyle = '#66526f'; g.beginPath(); g.moveTo(608, 110); g.lineTo(608, 500); g.stroke();
            for (const [dir, left, right, label] of [[0, 174, 430, 'Front'], [4, 786, 1042, 'Back']]) {
              g.fillStyle = '#ead2b1'; g.font = 'bold 18px system-ui';
              g.fillText(label, (left + right) / 2, 124);
              for (const [race, x, caption] of [['human', left, 'Human'], ['gnome', right, 'Gnome']]) {
                g.fillStyle = '#141321'; g.beginPath(); g.ellipse(x, 473, 99, 17, 0, 0, 2 * Math.PI); g.fill();
                g.strokeStyle = '#594961'; g.stroke();
                sprite.set({ ...look, race });
                g.save(); g.translate(x, 471); sprite.draw(g, hero(dir), 0, 3.55); g.restore();
                g.fillStyle = '#e7d5e1'; g.font = '16px system-ui'; g.fillText(caption, x, 526);
              }
            }
            return canvas.toDataURL('image/png').split(',')[1];
          }

          function render(design) {
            sprite.set({ ...look, race: design.race });
            const canvas = document.createElement('canvas');
            canvas.width = 1000; canvas.height = 620;
            const g = canvas.getContext('2d');
            const background = g.createRadialGradient(500, 300, 30, 500, 300, 600);
            const [inner, outer, title, subtitle, base, ring, caption] = design.colors;
            background.addColorStop(0, inner); background.addColorStop(1, outer);
            g.fillStyle = background; g.fillRect(0, 0, canvas.width, canvas.height);
            g.fillStyle = title; g.font = 'bold 34px Georgia'; g.textAlign = 'center';
            g.fillText(design.name, 500, 56);
            g.fillStyle = subtitle; g.font = '16px system-ui';
            g.fillText(design.label, 500, 84);
            g.imageSmoothingEnabled = false;
            const [ax, ay] = sprite.meta.anchor;
            for (const [x, direction, label] of [[270, 0, 'Front'], [730, 4, 'Back']]) {
              g.fillStyle = base;
              g.beginPath(); g.ellipse(x, 535, 108, 20, 0, 0, 2 * Math.PI); g.fill();
              g.strokeStyle = ring; g.lineWidth = 2; g.stroke();
              const frame = sprite.frame('idle', direction, 0);
              const scale = 3.55;
              g.drawImage(frame, Math.round(x - ax * scale), Math.round(530 - ay * scale),
                Math.round(frame.width * scale), Math.round(frame.height * scale));
              g.fillStyle = caption; g.fillText(label, x, 588);
            }
            return canvas.toDataURL('image/png').split(',')[1];
          }

          const results = [];
          for (const design of chosen) {
            const { race, marking } = design;
            if (!sprite.source.traits?.get(race)) fail(race + ' PixelFlow attachment atlas did not load');
            const custom = frames(race);
            const [fw, fh] = sprite.meta.frame;
            let marked = 0;
            for (let i = 0; i < custom.length; i++) {
              const { clip, dir, i: frame, px } = custom[i], previous = human[i].px;
              let added = 0;
              for (let j = 0; j < px.length; j += 4) {
                if (px[j + 3] && !previous[j + 3]) {
                  added++;
                  const x = (j / 4) % fw, y = Math.floor(j / 4 / fw);
                  if (x === 0 || y === 0 || x === fw - 1 || y === fh - 1)
                    fail(race + ' ' + clip + '/' + dir + '/' + frame + ' trait touches the frame edge');
                }
                if (clip === 'idle' && dir === 0 && px[j + 3] &&
                    marking.every((channel, k) => px[j + k] === channel) &&
                    marking.some((channel, k) => previous[j + k] !== channel)) marked++;
              }
              if (added < 12) fail(race + ' ' + clip + '/' + dir + '/' + frame + ' has fewer than 12 visible trait pixels');
            }
            if (!marked) fail(race + ' frontal idle shows no pale markings');
            sprite.set({ ...look, race, head: helm });
            const hatted = sprite.frame()._px;
            for (let j = 3; j < hatted.length; j += 4) {
              if (hatted[j] !== hattedHuman[j]) fail(race + ' traits protrude through equipped headgear');
            }
            const preview = design.job === name && design.body === gender;
            if (design.size) {
              verifySize('human', [1, 1]);
              verifySize(race, design.size);
            }
            results.push({
              race, poses: custom.length, mountPoses: design.size && preview ? await verifyMounts(design) : 0,
              png: preview ? (design.size ? renderComparison(design) : render(design)) : null,
            });
          }
          return results;
        }, { name, gender, chosen });
        assert.deepEqual(errors, []);
        for (const { race, poses: count, mountPoses, png } of result) {
          poses += count;
          if (png) {
            fs.mkdirSync(output, { recursive: true });
            fs.writeFileSync(path.join(output, 'valhalla-' + race + '-front-and-back.png'), Buffer.from(png, 'base64'));
          }
          console.log(race + '/' + name + '/' + gender + ': ' + count + ' poses checked');
          if (mountPoses) console.log(race + ': ' + mountPoses + ' real mounted poses checked');
        }
        await page.close();
      }
    }
    console.log('Playable race artwork: ' + poses + ' game poses verified');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
