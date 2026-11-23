const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const { requireMemoryLimit } = require('./lib/touch.cjs');

requireMemoryLimit();
const client = path.resolve(__dirname, '../client');
const output = path.resolve(__dirname, '../test-results/valhalla-mothkin-front-and-back.png');
const classes = ['Hunter', 'Warrior', 'Mage', 'Assassin', 'Priest'];
const antennaTest = process.env.MUTATE === 'antennae';
const server = http.createServer((req, res) => {
  if (req.url === '/') {
    res.setHeader('Content-Type', 'text/html');
    const scripts = ['items', 'magesprite', ...classes.filter(name => name !== 'Mage').map(name => name.toLowerCase() + 'sprite')];
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
    for (const name of process.argv.includes('--preview-only') ? ['Hunter'] : classes) {
      for (const gender of process.argv.includes('--preview-only') ? ['female'] : ['female', 'male']) {
        const page = await browser.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        if (antennaTest) {
          const source = fs.readFileSync(path.join(client, 'magesprite.js'), 'utf8');
          assert.ok(source.includes('if (showAntennae && antennae'));
          await page.route('**/magesprite.js', route => route.fulfill({
            contentType: 'text/javascript', body: source.replace('if (showAntennae && antennae', 'if (false && antennae'),
          }));
        }
        await page.goto('http://127.0.0.1:' + server.address().port);
        const result = await page.evaluate(async ({ name, gender }) => {
          const fail = message => { throw Error(name + '/' + gender + ': ' + message); };
          const cls = name.toLowerCase(), Base = window[name + 'Sprite'];
          const look = { name: 'Neris', class: cls, gender, race: 'mothkin', hairColor: cls === 'hunter' ? 5 : 0, skin: 0 };
          const C = Base.variant(look), sprite = await C.load(look);
          if (!sprite.source.mothkin) fail('PixelFlow attachment atlas did not load');
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
          const ordinary = frames(undefined), human = frames('human'), moth = frames('mothkin');
          let marked = 0;
          for (let i = 0; i < ordinary.length; i++) {
            const { clip, dir, i: frame, px } = moth[i], previous = ordinary[i].px, explicit = human[i].px;
            let added = 0, marks = 0;
            for (let j = 0; j < px.length; j += 4) {
              if (explicit[j] !== previous[j] || explicit[j + 1] !== previous[j + 1] ||
                  explicit[j + 2] !== previous[j + 2] || explicit[j + 3] !== previous[j + 3]) fail('legacy look differs from Human');
              if (px[j + 3] && !previous[j + 3]) {
                added++;
                const x = (j / 4) % sprite.meta.frame[0], y = Math.floor(j / 4 / sprite.meta.frame[0]);
                if (x === 0 || y === 0 || x === sprite.meta.frame[0] - 1 || y === sprite.meta.frame[1] - 1)
                  fail(clip + '/' + dir + '/' + frame + ' antenna touches the frame edge');
              }
              if (px[j] === 240 && px[j + 1] === 223 && px[j + 2] === 208 &&
                  (previous[j] !== 240 || previous[j + 1] !== 223 || previous[j + 2] !== 208)) marks++;
            }
            if (added < 12) fail(clip + '/' + dir + '/' + frame + ' has fewer than 12 visible antenna pixels');
            if (clip === 'idle' && dir === 0) marked += marks;
          }
          if (!marked) fail('frontal idle shows no pale cheek markings');
          const helm = C.TIERS[0], headPart = 'head_' + helm;
          sprite.set({ ...look, head: helm });
          await sprite.source.ensure(headPart);
          sprite.cache.clear();
          if (!sprite.source.parts[headPart]) fail('starter headgear did not load');
          const hattedMoth = sprite.frame()._px;
          sprite.set({ ...look, race: 'human', head: helm });
          const hattedHuman = sprite.frame()._px;
          for (let j = 3; j < hattedMoth.length; j += 4) {
            if (hattedMoth[j] !== hattedHuman[j]) fail('antennae protrude through equipped headgear');
          }
          if (name !== 'Hunter' || gender !== 'female') return { poses: moth.length };

          sprite.set(look);
          const canvas = document.createElement('canvas');
          canvas.width = 1000; canvas.height = 620;
          const g = canvas.getContext('2d');
          const background = g.createRadialGradient(500, 300, 30, 500, 300, 600);
          background.addColorStop(0, '#3b3455');
          background.addColorStop(1, '#111523');
          g.fillStyle = background; g.fillRect(0, 0, canvas.width, canvas.height);
          g.fillStyle = '#f1dfeb'; g.font = 'bold 34px Georgia'; g.textAlign = 'center';
          g.fillText('Neris', 500, 56);
          g.fillStyle = '#c6b6d5'; g.font = '16px system-ui';
          g.fillText('Mothkin Hunter · The Moonspore Canopy', 500, 84);
          g.imageSmoothingEnabled = false;
          const [ax, ay] = sprite.meta.anchor;
          for (const [x, direction, label] of [[270, 0, 'Front'], [730, 4, 'Back']]) {
            g.fillStyle = '#181827';
            g.beginPath(); g.ellipse(x, 535, 108, 20, 0, 0, 2 * Math.PI); g.fill();
            g.strokeStyle = '#746387'; g.lineWidth = 2; g.stroke();
            const frame = sprite.frame('idle', direction, 0);
            const scale = 3.55;
            g.drawImage(frame, Math.round(x - ax * scale), Math.round(530 - ay * scale),
              Math.round(frame.width * scale), Math.round(frame.height * scale));
            g.fillStyle = '#ded1e9'; g.fillText(label, x, 588);
          }
          return { poses: moth.length, png: canvas.toDataURL('image/png').split(',')[1] };
        }, { name, gender });
        assert.deepEqual(errors, []);
        poses += result.poses;
        if (result.png) {
          fs.mkdirSync(path.dirname(output), { recursive: true });
          fs.writeFileSync(output, Buffer.from(result.png, 'base64'));
        }
        console.log(name + '/' + gender + ': ' + result.poses + ' poses checked');
        await page.close();
      }
    }
    console.log('Mothkin artwork: ' + poses + ' game poses verified');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
