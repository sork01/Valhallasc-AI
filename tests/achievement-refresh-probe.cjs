// Exercise the new catalog over real private WebSockets, including SQLite restarts.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'world/achievements.txt')));
const w = new TestWorld(), bot = 'Achiever', observer = 'Witness';
let checks = 0;
const check = (condition, message) => { assert(condition, message); checks++; };
const send = packet => w.bots.get(bot).socket.send(JSON.stringify(packet));
async function achievements() {
  const before = w.events.length;
  send({ type: 'achievements' });
  return w.waitFor(() => w.events.slice(before).find(e => e.bot === bot && e.type === 'achievements'));
}
(async () => {
  await w.start();
  await w.connect({ bot, class: 'warrior', gender: 'male' });
  await w.connect({ bot: observer, class: 'priest', gender: 'female' });
  let view = await achievements();
  check(view.entries.length === 154 && view.maximum === 4090, 'real protocol exposes 154 goals / 4090 points');
  const categories = Object.fromEntries(['Adventure', 'Combat', 'Quests', 'Exploration', 'Fishing'].map(c => [c, view.entries.filter(a => a.category === c).length]));
  assert.deepEqual(categories, { Adventure: 23, Combat: 50, Quests: 23, Exploration: 32, Fishing: 26 }); checks++;
  for (const a of catalog.slice(120)) {
    const entry = view.entries.find(e => e.id === a.id);
    check(entry && !entry.complete && entry.progress === 0, `${a.id} starts with no invented progress`);
  }
  // Only fixture history is injected; ordinary reconciliation and title validation still run.
  const before = w.events.length;
  send({ type: 'select_title', achievement: 'rebirth_10' });
  await w.waitFor(() => w.events.slice(before).some(e => e.bot === bot && e.type === 'error' && /not earned/.test(e.text)));
  checks++;
  await w.debug(bot, { op: 'set_rebirth', tiers: [9, 0, 0, 0, 0] });
  view = await achievements();
  check(view.entries.find(a => a.id === 'rebirth_10').progress === 9 && !view.entries.find(a => a.id === 'rebirth_10').complete, 'nine rebirths do not earn the ten-life title');
  await w.debug(bot, { op: 'set_rebirth', tiers: [10, 0, 0, 0, 0] });
  await w.waitFor(() => w.events.some(e => e.bot === bot && e.type === 'notice' && e.text === 'Achievement earned: Ten Dawns Later (+50 points).'));
  checks++;
  view = await achievements();
  check(view.entries.find(a => a.id === 'rebirth_10').complete, 'permanent history reconciles');
  send({ type: 'select_title', achievement: 'rebirth_10' });
  await w.waitFor(() => w.player(bot).achievementTitle === 'The Everlasting');
  await w.waitFor(() => w.views.get(observer).players.some(p => p.id === w.bots.get(bot).id && p.achievementTitle === 'The Everlasting'));
  checks++;
  await w.debug(bot, { op: 'quest', id: 'deep_seahorse', action: 'finish' });
  view = await achievements();
  check(view.entries.find(a => a.id === 'seahorse_friend').complete, 'claimed seahorse quest earns its achievement');
  const totals = { points: view.points, selected: view.selected };
  await w.disconnect(bot); await w.connect({ bot });
  view = await achievements();
  check(view.points === totals.points && view.selected === totals.selected, 'points and selected new title survive reconnect');
  await w.restart();
  view = await achievements();
  check(view.points === totals.points && view.selected === totals.selected, 'points and selected new title survive process/SQLite restart');
  check(w.player(bot).achievementTitle === 'The Everlasting', 'restored snapshot exposes the selected new title');
  // Production locale code translates every new card, requirement and reward.
  const context = {
    localStorage: { getItem: () => JSON.stringify({ lang: 'sv' }) }, navigator: { language: 'sv' },
    document: { documentElement: {}, body: { nodeType: 1, querySelectorAll: () => [], hasAttribute: () => false }, createTreeWalker: () => ({ nextNode: () => null }) },
    Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 }, NodeFilter: { SHOW_TEXT: 4 }, MutationObserver: class { observe() {} },
  };
  context.window = context; vm.createContext(context);
  for (const file of ['sv-data.js', 'locale.js']) vm.runInContext(fs.readFileSync(path.join(root, 'client', file), 'utf8'), context);
  const translations = JSON.parse(fs.readFileSync(path.join(root, 'scripts/sv-translations.txt')));
  for (const a of catalog.slice(120)) for (const text of [a.name, a.description, a.title].filter(Boolean)) {
    check(typeof translations[text] === 'string' && translations[text] !== text && context.Locale.translate(text) === translations[text], `${text} has hand-written Swedish`);
  }
  console.log(`Achievement refresh: ${checks} private protocol/catalog/Swedish checks pass, including real notices, title refusal, observer snapshot, reconnect and SQLite restart.`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await w.stop(); });
