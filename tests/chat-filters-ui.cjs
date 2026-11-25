const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
require('./lib/touch.cjs').requireMemoryLimit();

const root = path.resolve(__dirname, '..', 'client');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const markup = read('index.html').match(/<section id="chat"[\s\S]*?<\/section>/)[0].replace(' hidden>', '>');
let source = read('syslog.js');
if (process.env.MUTATE === 'filter')
  source = source.replace('return filterFor(key)?.includes(entry.category) ?? true;', 'return true;');
if (process.env.MUTATE === 'skill')
  source = source.replace("if (previous != null && skill > previous)", "if (false)");
const fixture = '<main style="width:100vw;height:100vh;position:relative;container-type:inline-size">' +
  markup + '</main><style>' + read('online.css') + '</style><script>' +
  'window.WORLD_ITEMS = [{id:"fish_pier_sprat",name:"Pier Sprat",rarity:"common"},' +
  '{id:"smith_ore_tin",name:"Tin Ore",rarity:"common"},{id:"test_gear",name:"Trial Blade",rarity:"rare"}];' +
  source + '</script>';

(async () => {
  const browser = await chromium.launch({ headless:true });
  try {
    const page = await browser.newPage({ viewport:{ width:1100, height:650 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://chat.test/', route => route.fulfill({ contentType:'text/html; charset=utf-8', body:fixture }));
    await page.goto('https://chat.test/');
    const populate = () => page.evaluate(() => {
      const id = 'hero';
      const take = (item, quantity) => ({ item, quantity });
      SystemLog.welcome({ id, inventory:[], professions:{ fishing:{skill:149}, blacksmithing:{skill:1} } });
      SystemLog.chat('Ready to travel?', 'Adventurer', 'party');
      SystemLog.event({ kind:'fish_catch', actor:id, item:'fish_pier_sprat', kg:3, quantity:1, skillUp:150 }, id);
      SystemLog.event({ kind:'fish_catch', actor:'other', item:'fish_pier_sprat', kg:99, quantity:1 }, id);
      SystemLog.packet({ type:'mining', state:'done', item:'smith_ore_tin', quantity:2, skill:2 });
      SystemLog.packet({ type:'dialogue', notice:'Quest complete: Bridge Watch!', inventory:[
        take('fish_pier_sprat', 1), take('smith_ore_tin', 2), take('test_gear', 1),
      ], gearInstances:[{ item:'test_gear', rarity:'epic' }] });
      SystemLog.snapshot({ id, inventory:[take('fish_pier_sprat', 1), take('smith_ore_tin', 2), take('test_gear', 1)],
        professions:{ fishing:{skill:150}, blacksmithing:{skill:2} } });
    });
    const box = name => page.locator('#chat-filter-options input[value="' + name + '"]');
    const save = () => page.locator('#chat-filters button[type="submit"]').click();
    const system = page.locator('#system-log');
    const custom = page.locator('#custom-chat-log');
    await populate();
    assert(await page.locator('#tab-system').evaluate(tab => tab.classList.contains('unread')));
    await page.getByRole('tab', { name:'System', exact:true }).click();
    const initial = await system.innerText();
    for (const line of ['You catch Pier Sprat (ca 3 kg) ×1.', 'Fishing skill increased to 150.',
      'You mine 2 × Tin Ore.', 'Blacksmithing skill increased to 2.', 'Quest complete: Bridge Watch!',
      'You receive 1 × Trial Blade.']) assert(initial.includes(line), 'Missing ' + line + '\nActual log: ' + initial + '\nBrowser errors: ' + errors.join(', '));
    assert(!/99 kg|Ready to travel|You receive .* (Pier Sprat|Tin Ore)/.test(initial));
    assert.equal(await system.locator('.sys-rarity[data-rarity="epic"]').textContent(), 'Trial Blade');

    await page.getByRole('button', { name:'Filter', exact:true }).click();
    await box('fishing').uncheck();
    await save();
    assert(!(await system.innerText()).includes('You catch'), 'System filter hides catches');
    assert((await system.innerText()).includes('Fishing skill increased'));
    await page.getByRole('button', { name:'New chat tab' }).click();
    await page.getByLabel('Tab name').fill('Fishing party');
    for (const option of await page.locator('#chat-filter-options input').all()) {
      await option.setChecked(['party', 'fishing'].includes(await option.getAttribute('value')));
    }
    await save();
    assert.match(await custom.innerText(), /Adventurer: Ready to travel/);
    assert.match(await custom.innerText(), /You catch Pier Sprat/);
    assert.doesNotMatch(await custom.innerText(), /Blacksmithing|Trial Blade/);

    await page.reload();
    await populate();
    await page.getByRole('tab', { name:'Fishing party' }).click();
    assert.match(await custom.innerText(), /You catch Pier Sprat/);
    assert.doesNotMatch(await custom.innerText(), /Trial Blade/);
    await page.getByRole('button', { name:'Filter', exact:true }).click();
    await page.getByLabel('Tab name').fill('Party only');
    await box('fishing').uncheck();
    await save();
    assert.match(await custom.innerText(), /Ready to travel/);
    assert.doesNotMatch(await custom.innerText(), /You catch/);
    await page.getByRole('button', { name:'Filter', exact:true }).click();
    await page.getByRole('button', { name:'Delete tab' }).click();
    assert.equal(await page.getByRole('tab', { name:'Party only' }).count(), 0);
    assert(!(await system.innerText()).includes('You catch'), 'deleting a custom tab leaves System filters intact');
    assert.deepEqual(errors, []);
    console.log('System and custom chat filters passed packet, rarity, editing and reload checks');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
