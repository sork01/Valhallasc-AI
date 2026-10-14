// Export the exact in-game dungeon marks as transparent poster overlays.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const themes = ['regearvault', 'regearcloister', 'regearreliquary', 'regearnave', 'regearmoonwell'];
const dest = path.join(root, 'test-results/dungeon-marks');
(async () => {
  fs.mkdirSync(dest, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><title>Dungeon marks</title>');
    await page.addScriptTag({ path: path.join(root, 'client/magesprite.js') });
    for (const theme of themes) {
      const data = await page.evaluate(theme => {
        const c = document.createElement('canvas'); c.width = 220; c.height = 200;
        const g = c.getContext('2d'); g.translate(110, 177); g.scale(1.2, 1.2);
        MageSprite.dungeonAura(g, { theme, count: 5 }, 0);
        return c.toDataURL('image/png').split(',')[1];
      }, theme);
      fs.writeFileSync(path.join(dest, theme + '.png'), Buffer.from(data, 'base64'));
    }
  } finally { await browser.close(); }
  console.log(`Exported ${themes.length} in-game dungeon marks`);
})().catch(e => { console.error(e); process.exitCode = 1; });
