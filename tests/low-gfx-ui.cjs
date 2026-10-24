const fs = require('node:fs');
const { execFileSync } = require('node:child_process');
const { run, replace, safeSpot } = require('./lib/touch.cjs');
const hz = +execFileSync('getconf', ['CLK_TCK'], { encoding: 'utf8' }).trim();
async function ticks(cdp) {
  const { processInfo } = await cdp.send('SystemInfo.getProcessInfo');
  let total = 0;
  for (const p of processInfo) try { const s = fs.readFileSync(`/proc/${p.id}/stat`, 'utf8').split(') ')[1].split(' '); total += +s[11] + +s[12]; } catch (_) {}
  return total;
}
const suite = {
  name: 'low-gfx',
  mutate: page => replace(page, 'field.js', 'now - lastPaint >= 1000 / 30 - .5', 'true'),
  async test({ player, check, browser, width, height, sleep, out }) {
    const page = await player('LowGraphics', { keepSuggestion: true, deviceScaleFactor: 2 }); await safeSpot(page);
    check(await page.locator('#low-gfx-suggestion').isVisible(), 'first touch visit offers Low graphics');
    check(await page.evaluate(() => !Prefs.lowGraphics), 'Low graphics is never forced');
    await page.evaluate(() => {
      window.paintCount = 0; const set = CanvasRenderingContext2D.prototype.setTransform;
      CanvasRenderingContext2D.prototype.setTransform = function(...args) { if (this.canvas.id === 'fieldcv') paintCount++; return set.apply(this, args); };
    });
    const cdp = await browser.newBrowserCDPSession();
    async function sample() {
      await page.evaluate(() => { paintCount = 0; });
      const start = performance.now(), before = await ticks(cdp); await sleep(3000);
      const elapsed = performance.now() - start, after = await ticks(cdp);
      const state = await page.evaluate(() => ({ paints: paintCount, animations: document.getAnimations().filter(a => a.playState === 'running').length, backing: document.querySelector('#fieldcv').width, css: document.querySelector('#fieldcv').clientWidth }));
      return { ...state, elapsedMs: elapsed, cpuPercentOfCore: (after - before) / hz / (elapsed / 1000) * 100, fps: state.paints / (elapsed / 1000) };
    }
    await sleep(350); const normal = await sample();
    await page.locator('#low-gfx-accept').click(); await sleep(350); const low = await sample();
    check(await page.evaluate(() => Prefs.lowGraphics && Prefs.touchGraphicsSuggested), 'accepting saves the setting and suggestion answer');
    check(low.backing === low.css && normal.backing >= normal.css * 1.9, `backing scale drops (${normal.backing} -> ${low.backing})`);
    check(low.fps <= 31.5 && normal.fps > 10, `paint rate is capped while input updates continue (${normal.fps.toFixed(1)} -> ${low.fps.toFixed(1)})`);
    check(await page.evaluate(() => document.documentElement.classList.contains('low-graphics')), 'Low graphics applies cosmetic rules');
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click(); await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    check(await page.evaluate(() => Prefs.lowGraphics), 'setting survives reload');
    check(await page.locator('#low-gfx-suggestion').isHidden(), 'suggestion stays dismissed');
    await page.locator('#touch-actions [data-action="menu"]').click(); await page.locator('#p-settings').click();
    check(await page.locator('#set-low-graphics').isChecked(), 'Settings shows the saved preference');
    await page.locator('#set-low-graphics').uncheck();
    check(await page.evaluate(() => !Prefs.lowGraphics && !document.documentElement.classList.contains('low-graphics')), 'normal graphics can be restored');
    fs.writeFileSync(`${out}/cpu-${width}x${height}.txt`, JSON.stringify({ normal, low, savingPercent: Math.round((1 - low.cpuPercentOfCore / normal.cpuPercentOfCore) * 100) }, null, 2) + '\n');
    console.log(`CPU ${width}x${height}: ${normal.cpuPercentOfCore.toFixed(1)}% -> ${low.cpuPercentOfCore.toFixed(1)}% of a core; ${normal.fps.toFixed(1)} -> ${low.fps.toFixed(1)} paints/s`);
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
