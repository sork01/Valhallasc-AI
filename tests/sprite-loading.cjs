// How the client loads the layered class sprites (client/magesprite.js): the other players' art loads in the
// background, one set at a time and after your own, in slices that leave the page responsive; and the precomputed frame
// bounds (scripts/sprite_bounds.py) are current. Needs only Chromium and the static client folder, no game server.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..'), client = path.join(root, 'client');
let checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
const TYPES = { '.png': 'image/png', '.js': 'text/javascript', '.html': 'text/html' };
const PAGE = '<!doctype html><script src="items.js"></script><script src="magesprite.js"></script><script src="assassinsprite.js"></script><script src="priestsprite.js"></script><script src="huntersprite.js"></script><script src="warriorsprite.js"></script>';
(async () => {
  // The sidecars must match the PNGs: a stale one clips sprites instead of failing.
  execFileSync('python3', [path.join(root, 'scripts/sprite_bounds.py'), '--check'], { stdio: 'pipe' });
  check(true, 'bounds sidecars are current');
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    if (url === '/p.html') { res.setHeader('Content-Type', 'text/html'); return res.end(PAGE); }
    fs.readFile(path.join(client, url), (error, data) => {
      if (error) { res.statusCode = 404; return res.end(); }
      res.setHeader('Content-Type', TYPES[path.extname(url)] || 'text/plain'); res.end(data);
    });
  }).listen(0);
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage(); page.on('pageerror', e => { throw e; });
    await page.goto(`http://127.0.0.1:${server.address().port}/p.html`);
    const r = await page.evaluate(async () => {
      let longest = 0;
      new PerformanceObserver(list => { for (const e of list.getEntries()) longest = Math.max(longest, e.duration); }).observe({ entryTypes: ['longtask'] });
      let frames = 0, worstGap = 0, last = performance.now();
      const tick = now => { worstGap = Math.max(worstGap, now - last); last = now; frames++; requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
      const done = {}, stamp = name => () => { done[name] = performance.now(); };
      const male = C => C.variant({ gender: 'male' });
      // Your hunter loads in the foreground; four other players' sets are queued behind it, and the assassin is then
      // asked for by you too (it must jump the queue).
      const hunter = male(HunterSprite).load({}).then(stamp('hunter'));
      const others = [['mage', MageSprite], ['assassin', AssassinSprite], ['priest', PriestSprite], ['warrior', WarriorSprite]]
        .map(([name, C]) => male(C).load({}, { background: true }).then(stamp(name)));
      const promoted = male(AssassinSprite).load({}).then(stamp('assassinForeground'));
      await Promise.all([hunter, promoted, ...others]);
      await new Promise(resolve => setTimeout(resolve, 300));   // long-task entries are delivered asynchronously
      const sprite = await male(HunterSprite).load({});
      const canvas = sprite.frame('idle', 0, 0);
      const lit = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data.filter((v, i) => i % 4 === 3 && v).length;
      return { done, longest, worstGap, frames, lit, backgroundFlag: (await male(MageSprite).load({}, { background: true })).background };
    });
    const { done } = r;
    check(done.hunter < done.mage && done.hunter < done.priest && done.hunter < done.warrior, 'the foreground set finishes before queued background sets');
    check(done.assassinForeground <= done.mage, 'a background set you then ask for jumps the queue (' + JSON.stringify(done) + ')');
    check(done.mage < done.priest && done.priest < done.warrior, 'background sets load one at a time, in the order they were asked for');
    check(r.lit > 500, 'a loaded sprite composites a real figure (' + r.lit + ' visible pixels)');
    check(r.longest === 0, 'no long (50 ms+) main-thread task while five sets load (longest ' + Math.round(r.longest) + ' ms)');
    check(r.worstGap < 60, 'frames keep coming while sets load (worst gap ' + Math.round(r.worstGap) + ' ms)');
    console.log(`sprite-loading: ${checks} checks passed`, JSON.stringify({ longest: Math.round(r.longest), worstGap: Math.round(r.worstGap) }));
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); process.exit(1); });
