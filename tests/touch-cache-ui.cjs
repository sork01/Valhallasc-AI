const { run, replace } = require('./lib/touch.cjs');
const suite = {
  name: 'touch-cache',
  mutate: page => replace(page, 'field.js', 'chunkCacheLimit = Math.max(32, groundChunks.length);', 'chunkCacheLimit = 31;'),
  async test({ player, check, sleep }) {
    const page = await player('GroundCache');
    await sleep(300);
    await page.evaluate(() => {
      window.newCanvases = 0;
      const create = document.createElement;
      document.createElement = function(tag, ...args) {
        if (tag.toLowerCase() === 'canvas') newCanvases++;
        return create.call(this, tag, ...args);
      };
    });
    await sleep(500);
    const created = await page.evaluate(() => newCanvases);
    check(created === 0, `stationary ground reuses its canvas tiles (${created} new canvases)`);
    await page.evaluate(() => { Field.setPaused(true); Settings.show(); newCanvases = 0; });
    await sleep(500);
    check(await page.evaluate(() => newCanvases === 0), 'opening Settings keeps the ground cache stable');
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
