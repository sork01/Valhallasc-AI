const { run, replace, debug, safeSpot } = require('./lib/touch.cjs');
const suite = {
  name: 'achievements',
  mutate: page => process.env.MUTATE === 'category'
    ? replace(page, 'achievements.js', '!category || category === value', 'true')
    : replace(page, 'achievements.js', '`${data.points} / ${data.maximum}`', '`${data.points} / ${data.points}`'),
  async test({ player, check, width, height, out }) {
    const page = await player('Pathfinder'); await safeSpot(page);
    await page.evaluate(() => { window.__nameplates = []; const fill = CanvasRenderingContext2D.prototype.fillText; CanvasRenderingContext2D.prototype.fillText = function(s,...args) { if (String(s).includes('Pathfinder')) window.__nameplates.push(String(s)); return fill.call(this,s,...args); }; });
    await page.keyboard.press('Escape'); await page.locator('#p-achievements').click();
    await page.waitForSelector('.achievement-card');
    check(await page.locator('.achievement-card').count() === 102, 'all 102 achievements shown');
    check(await page.locator('.achievement-group-heading').allTextContents().then(a => a.join(',') === 'Adventure,Combat,Quests,Exploration'), 'all achievements are grouped under their catalog categories');
    check(await page.locator('#achievement-categories').evaluate(n => {
      const rows = [...n.children].map(button => button.getBoundingClientRect().top);
      return Math.max(...rows) - Math.min(...rows) < 1;
    }), 'category buttons fit on one row to leave space for the cards');
    for (const [category, count] of [['Adventure',17],['Combat',40],['Quests',13],['Exploration',32]]) {
      const button = page.locator(`#achievement-categories button[data-category="${category}"]`);
      await button.click();
      check(await button.getAttribute('aria-pressed') === 'true', `${category} selection is exposed to assistive technology`);
      check(await page.locator('.achievement-card').count() === count && await page.locator('.achievement-group-heading').textContent() === category, `${category} shows only its ${count} achievements`);
      check((await button.locator('small').textContent()).endsWith(`/ ${count}`), `${category} completion count uses its own total`);
      const r = await button.boundingBox(); check(r.width >= 43.5 && r.height >= 43.5, `${category} has a 44 px touch target`);
    }
    await page.locator('#achievement-categories button[data-category="Combat"]').click();
    await page.locator('[data-achievement="dungeon_choirmother"]').scrollIntoViewIfNeeded();
    await page.screenshot({ path:`${out}/achievement-frames-${width}x${height}.png` });
    check(await page.locator('[data-achievement="dungeon_choirmother"]').evaluate(n => {
      const card = n.getBoundingClientRect();
      return [...n.querySelectorAll('header, h4, p, progress, small')].every(child => {
        const r = child.getBoundingClientRect(); return r.left >= card.left && r.right <= card.right;
      });
    }), 'long dungeon titles fit inside the ornate frame');
    check(await page.locator('#achievement-list').evaluate(n => n.scrollWidth <= n.clientWidth + 1), 'gold decorations do not cause horizontal list overflow');
    check(await page.locator('.achievement-card').first().locator('.achievement-corner[aria-hidden=true]').count() === 4, 'all four decorative corner flourishes are present');
    check(await page.locator('.achievement-corner').first().evaluate(async n => {
      const image = new Image(); image.src = getComputedStyle(n).backgroundImage.slice(5, -2);
      try { await image.decode(); return image.naturalWidth > 0; } catch (_) { return false; }
    }), 'gold corner artwork loads');
    await page.locator('#achievement-categories button[data-category=""]').click();
    check(await page.locator('[data-achievement^="dungeon_"]').count() === 21, 'all 20 dungeon goals and their overall achievement are shown');
    for (const [id,title] of [['dungeon_master','The Delver'],['mounts_5','The Stablemaster'],['story_20','The Witness']]) {
      check((await page.locator(`[data-achievement="${id}"]`).textContent()).includes(title), `${title} reward is visible before it is earned`);
    }
    check(/\d+ \/ 2200/.test(await page.locator('#achievement-total').textContent()), 'earned / maximum uses the full 2200-point catalog');
    check(await page.locator('#achievement-title-select option').count() === 1, 'no unearned titles selectable');
    await page.keyboard.press('e'); check(await page.locator('#equipment').isHidden(), 'game shortcuts do not open another window behind achievements');
    await page.locator('#achievements-close').focus(); await page.keyboard.press('Shift+Tab');
    check(await page.locator('#achievement-list').evaluate(n => document.activeElement === n), 'keyboard focus stays within the achievement dialog');
    check(await page.locator('[data-achievement="forge"]').textContent().then(t => /Gryphon/.test(t) && /The Chainbreaker/.test(t)), 'hard achievement shows both mount and title rewards');
    const box = await page.locator('.achievements-window').boundingBox(), stage = await page.locator('#stage').boundingBox();
    check(await page.locator('#achievements-close').evaluate(n => { const r=n.getBoundingClientRect(); return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2) === n; }), 'Close remains above the DPS meter and combat HUD');
    check(box.height >= Math.min(height * .7, 500), `the list uses the available screen height (${box.height}px)`);
    check(box.x >= stage.x - 1 && box.y >= stage.y - 1 && box.x + box.width <= stage.x + stage.width + 1 && box.y + box.height <= stage.y + stage.height + 1, `window fits the stage ${JSON.stringify({box,stage})}`);
    for (const id of ['achievements-close','achievement-title-select','achievements-filter']) {
      const r = await page.locator('#'+id).boundingBox(); check(r.width >= 43.5 && r.height >= 43.5, `${id} touch target is at least 44 px`);
    }
    await page.locator('#achievements-filter').selectOption('incomplete');
    check(await page.locator('.achievement-card[data-complete="true"]').count() === 0, 'in-progress filter hides completed achievements');
    await debug(page, { op: 'explore_all' });
    await page.waitForFunction(() => document.querySelector('#achievement-title-select option[value="explorer"]'), null, { timeout: 10000 });
    await page.locator('#achievements-filter').selectOption('');
    check(await page.locator('[data-achievement="explorer"]').getAttribute('data-complete') === 'true', 'authoritative full-fog exploration completes The Explorer');
    check(await page.locator('[data-achievement="explorer"] progress').getAttribute('value') === '207', 'all 207 cells counted');
    await page.locator('#achievement-title-select').selectOption('explorer');
    await page.waitForFunction(() => Field.hero.achievementTitle === 'The Explorer');
    check(await page.locator('#hud-name').textContent() === 'Pathfinder The Explorer', 'selected title displays after the name');
    const total = await page.locator('#achievement-total').textContent();
    await page.evaluate(() => Online.send({ type:'select_title', achievement:'forge' }));
    await page.waitForFunction(() => /not earned that title/.test(document.getElementById('chat-log').textContent));
    check(await page.locator('#achievement-title-select').inputValue() === 'explorer', 'forged unearned title refused');
    check(await page.locator('#achievement-total').textContent() === total, 'a refusal awards no points');
    await page.locator('#achievements-filter').selectOption('complete');
    check(await page.locator('.achievement-card[data-complete="false"]').count() === 0, 'completed filter shows only earned achievements');
    await page.locator('#achievement-categories button[data-category="Exploration"]').click();
    check(await page.locator('.achievement-card').count() === 32, 'category and completed filters work together');
    check(await page.locator('#achievement-categories button[data-category="Exploration"] small').textContent() === '32 / 32', 'category counts update after authoritative progress');
    await page.locator('#achievement-categories button[data-category="Quests"]').click();
    check(await page.locator('.achievement-card').count() === 0 && (await page.locator('#achievement-list').textContent()).includes('No achievements in this view.'), 'an empty category with a completion filter explains the empty view');
    await page.locator('#achievement-categories button[data-category=""]').click();
    await page.screenshot({ path:`${out}/achievements-${width}x${height}.png` });
    await page.keyboard.press('Escape'); check(await page.locator('#achievements-panel').isHidden(), 'Escape closes the panel');
    const other = await player('Observer'); await safeSpot(other);
    await other.evaluate(() => { window.__nameplates=[]; const fill=CanvasRenderingContext2D.prototype.fillText; CanvasRenderingContext2D.prototype.fillText=function(s,...args){ if(String(s).includes('Pathfinder')) window.__nameplates.push(String(s)); return fill.call(this,s,...args); }; });
    await other.waitForFunction(() => window.__nameplates.includes('Pathfinder The Explorer'), null, { timeout: 10000 });
    check(true,'a second browser sees the selected title on the world nameplate');
    await other.context().close();
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero.achievementTitle === 'The Explorer');
    await page.keyboard.press('e'); await page.locator('#character-achievements-open').click();
    await page.waitForFunction(() => document.querySelector('#achievement-total').textContent.includes('/ 2200'));
    check(await page.locator('#achievement-total').textContent() === total, 'points and title survive reconnect with no duplicate awards');
    check(await page.locator('#achievement-title-select').inputValue() === 'explorer', 'title selection persists');
    await page.locator('#achievement-title-select').selectOption(''); await page.waitForFunction(() => !Field.hero.achievementTitle);
    check(await page.locator('#hud-name').textContent() === 'Pathfinder', 'No title restores the plain name');
    await page.locator('#achievements-close').click();
    await page.evaluate(() => { const key='valhallasc.save.v1'; const s=JSON.parse(localStorage.getItem(key)); s.lang='sv'; localStorage.setItem(key,JSON.stringify(s)); });
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero.id); await page.keyboard.press('Escape'); await page.locator('#p-achievements').click();
    await page.locator('#achievements-filter').selectOption('');
    await page.waitForSelector('[data-achievement="explorer"]');
    check(await page.locator('#achievements-heading').textContent() === 'Prestationer', 'Swedish panel heading');
    check(await page.locator('#achievement-categories button > span').allTextContents().then(a => a.join(',') === 'Alla prestationer,Äventyr,Strid,Uppdrag,Utforskning'), 'all category controls have Swedish labels');
    check(await page.locator('[data-achievement="explorer"] h4').textContent() === 'Utforskaren', 'Swedish catalog achievement');
    check((await page.locator('[data-achievement="story_20"]').textContent()).includes('Vittnet') && (await page.locator('[data-achievement="mounts_5"]').textContent()).includes('Stallmästaren') && (await page.locator('[data-achievement="dungeon_master"]').textContent()).includes('Djupvandraren'), 'all three added title rewards have Swedish text');
    check(await page.locator('#achievement-title-select option[value="explorer"]').textContent() === 'Utforskaren', 'Swedish title selector');
    await page.locator('#achievement-title-select').selectOption('explorer');
    await page.waitForFunction(() => document.getElementById('hud-name').textContent === 'Pathfinder Utforskaren');
    check(true,'Swedish title translated without translating the player name');
    await page.context().close();
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode=1; });
