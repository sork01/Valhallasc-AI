const { run, replace } = require('./lib/touch.cjs');
const suite = {
  name: 'touch-install',
  mutate: page => replace(page, 'settings.js', "fullscreen.hidden = !document.fullscreenEnabled || typeof stage.requestFullscreen !== 'function';", 'fullscreen.hidden = true;'),
  async test({ player, check, width, height }) {
    const page = await player('TouchInstall');
    const manifestURL = await page.locator('link[rel=manifest]').getAttribute('href');
    check(manifestURL?.endsWith('.webmanifest'), 'manifest uses the permitted extension');
    const response = await page.request.get(new URL(manifestURL, page.url()).href), manifest = await response.json();
    check(response.status() === 200 && /application\/manifest\+json/.test(response.headers()['content-type']), 'manifest is served with its MIME type');
    check(manifest.orientation === 'landscape' && ['standalone', 'fullscreen'].includes(manifest.display), 'installed game requests landscape and its own window');
    check(new URL(manifest.start_url, response.url()).origin === new URL(page.url()).origin, 'installed game stays on its own origin');
    for (const icon of manifest.icons) {
      const iconResponse = await page.request.get(new URL(icon.src, response.url()).href);
      check(iconResponse.status() === 200 && iconResponse.headers()['content-type'].includes('image/png'), `${icon.sizes} install icon is served`);
    }
    check(await page.locator('link[rel=apple-touch-icon]').count() === 1, 'Apple home screen icon is linked');
    check(await page.evaluate(() => getComputedStyle(document.body).overscrollBehavior === 'none' && getComputedStyle(document.querySelector('#fieldcv')).touchAction === 'none'), 'game surface blocks pull-to-refresh and canvas pinches');
    await page.locator('#touch-actions [data-action="menu"]').click(); await page.locator('#p-settings').click();
    if (await page.evaluate(() => document.fullscreenEnabled)) {
      check(await page.locator('#set-fullscreen').isVisible(), 'supported fullscreen button is available');
      await page.locator('#set-fullscreen').click({ timeout: 7000 }).catch(async e => {
        console.error(await page.evaluate(async () => {
          const readings = [];
          for (let i=0; i<8; i++) { await new Promise(requestAnimationFrame); const el=document.querySelector('#set-fullscreen'), r=el.getBoundingClientRect(), w=el.closest('section'); readings.push({ x:r.x,y:r.y,w:r.width,h:r.height, scale:w.style.scale, k:w.style.getPropertyValue('--window-k'), windowHeight:w.offsetHeight,scroll:w.scrollTop }); }
          return readings;
        })); throw e;
      }); await page.waitForFunction(() => document.fullscreenElement?.id === 'stage');
      check(await page.locator('#set-fullscreen').textContent() === 'Exit fullscreen', 'fullscreen button reflects the entered state');
      await page.locator('#set-fullscreen').click(); await page.waitForFunction(() => !document.fullscreenElement);
    }
    if (await page.evaluate(() => document.fullscreenEnabled)) {
      await page.evaluate(() => { document.getElementById('stage').requestFullscreen = () => Promise.reject(new Error('Test refusal')); });
      await page.locator('#set-fullscreen').click();
      check(await page.locator('#set-fullscreen-notice').isVisible(), 'a refused request shows an inline explanation');
      check((await page.locator('#set-fullscreen-notice').textContent()).includes('home screen'), 'refusal offers the supported alternative');
    }
    await page.evaluate(() => { Object.defineProperty(document, 'fullscreenEnabled', { configurable: true, value: false }); dispatchEvent(new Event('fullscreenchange')); });
    check(await page.locator('#set-fullscreen').isHidden(), 'unsupported fullscreen is hidden');
    await page.setViewportSize({ width: height, height: width });
    const rotate = await page.locator('.rotate').evaluate(n => { const r = n.getBoundingClientRect(); return { w: r.width, h: r.height, hit: document.elementFromPoint(innerWidth/2, innerHeight/2)?.closest('.rotate') === n }; });
    check(rotate.w === height && rotate.h === width && rotate.hit, 'portrait rotate overlay covers gameplay and dialogs');
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
