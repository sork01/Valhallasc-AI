// `/played` wording: the real playedText() block of client/online.js, run on its own. MUTATE=1 breaks the singular, which must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const text = fs.readFileSync(require('node:path').join(__dirname, '../client/online.js'), 'utf8');
const block = text.slice(text.indexOf('// PLAYED-BEGIN'), text.indexOf('// PLAYED-END'));
assert.ok(block.includes('function playedText'), 'the block is in online.js');
const run = (language, seconds) => {
  const context = { window: { Locale: { language } }, Math, Number };
  vm.createContext(context);
  vm.runInContext(process.env.MUTATE === '1' ? block.replace('n === 1 ? 0 : 1', '1') : block, context);
  return vm.runInContext('playedText(' + JSON.stringify(seconds) + ')', context);
};
const D = 86400, H = 3600, M = 60;
assert.equal(run('en', 0), 'Time played: 0 days, 0 hours, 0 minutes');
assert.equal(run('en', D + H + M + 59), 'Time played: 1 day, 1 hour, 1 minute');
assert.equal(run('en', 3 * D + 4 * H + 12 * M), 'Time played: 3 days, 4 hours, 12 minutes');
assert.equal(run('en', 59), 'Time played: 0 days, 0 hours, 0 minutes', 'seconds are dropped, never rounded up');
assert.equal(run('en', 30 * D + 23 * H + 59 * M), 'Time played: 30 days, 23 hours, 59 minutes');
assert.equal(run('sv', D + H + M), 'Speltid: 1 dag, 1 timme, 1 minut');
assert.equal(run('sv', 2 * D + 5 * H + 7 * M), 'Speltid: 2 dagar, 5 timmar, 7 minuter');
assert.equal(run('ko', 2 * M), 'Time played: 0 days, 0 hours, 2 minutes', 'other languages fall back to English');
assert.equal(run('en', 'oops'), 'Time played: 0 days, 0 hours, 0 minutes', 'a bad value reads as zero');
console.log('played-text: 9 checks passed');
