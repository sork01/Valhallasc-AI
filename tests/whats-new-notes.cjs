// Release guard: every displayed version needs its own plain-language notes before it can ship.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'client/index.html'), 'utf8');
const version = html.match(/class="version">([^<]+)</)[1];
const notes = JSON.parse(fs.readFileSync(path.join(root, 'client/release-notes.txt'), 'utf8'));
if (process.env.MUTATE === 'missing') notes.splice(notes.findIndex(entry => entry.version === version), 1);
assert.equal(notes[0].version, version, `No latest release notes for ${version}`);
assert.equal(new Set(notes.map(entry => entry.version)).size, notes.length, 'Duplicate version');
const code = /\b(?:undefined|null|const|function|localStorage|server|client|protocol|binary|packet|fixture|database|commit|MCP|Rust|JavaScript)\b|\.\w+\.(?:js|rs)|=>|\bx\d+(?:\.\d+)?\b|\d+[.,]\d+\s*%/i;
let lines = 0;
for (const entry of notes) {
  assert.match(entry.version, /^(Beta|Multiplayer alpha) \d+\.\d+\.\d+$/);
  assert.match(entry.date, /^\d{4}-\d{2}-\d{2}$/);
  let count = 0;
  for (const field of ['new', 'changed', 'removed']) {
    assert.ok(Array.isArray(entry[field]), `${entry.version}: missing ${field}`);
    for (const line of entry[field]) {
      assert.ok(typeof line === 'string' && line.length > 10, 'Empty note');
      assert.ok(!code.test(line), `Programming language or exact balance number: ${line}`);
      if (field === 'removed') assert.match(line, /\b(so|because|replace[sd]?)\b/i, `Removal needs a reason: ${line}`);
      lines++; count++;
    }
  }
  assert.ok(count, `${entry.version}: empty release`);
}
for (const version of ['Beta 1.14.32', 'Beta 1.14.33']) assert.ok(notes.some(entry => entry.version === version), `Missing history: ${version}`);
console.log(`whats-new-notes: ${notes.length} versions, ${lines} plain-language notes; ${version} is covered`);
