// Sample actual weather drawing across frames: the streak must follow the drop's motion.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
let source = fs.readFileSync(process.env.WEATHER_CANDIDATE || path.join(__dirname, '../client/weather.js'), 'utf8');
if (process.env.MUTATE === 'direction') source = source.replace(
  'g.moveTo(x-wind*trail,y-length); g.lineTo(x,y);',
  'g.moveTo(x,y); g.lineTo(x-5-a*3,y+14+a*11);');
let reduced = false, checks = 0;
const sandbox = {
  window: { Prefs: { weather: 1, lowGraphics: false } },
  performance: { now: () => 0 },
  document: { getElementById: () => null },
  matchMedia: () => ({ matches: reduced }),
};
vm.runInNewContext(source, sandbox);
const weather = sandbox.window.Weather;
const check = (ok, label) => { assert.ok(ok, label); checks++; };
function frame(time) {
  const lines = [], splashes = []; let start = null, end = null;
  const g = {
    save() {}, restore() {}, fillRect() {},
    beginPath() { start = end = null; },
    moveTo(x, y) { start = [x, y]; }, lineTo(x, y) { end = [x, y]; },
    stroke() { if (start && end) lines.push({ start, end }); },
    ellipse(x, y) { splashes.push([x, y]); },
  };
  weather.draw(g, 1280, 800, time);
  return { lines, splashes };
}
weather.setZone({ theme: 'meadow' });
for (const type of ['rain', 'thunderstorm']) for (const intensity of ['light', 'medium', 'heavy']) for (const low of [false, true]) {
  sandbox.window.Prefs.lowGraphics = low;
  weather.sync({ type, intensity, inside: false, ageSeconds: 50, endsInSeconds: 100 }, 0, 0);
  weather.tick(2);
  const before = frame(10), after = frame(10 + 1 / 120), label = `${type}/${intensity}/${low ? 'low' : 'normal'}`;
  check(before.lines.length > 0 && before.lines.length === after.lines.length, `${label}: stable rain population`);
  let matched = 0;
  for (let i = 0; i < before.lines.length; i++) {
    const a = before.lines[i], b = after.lines[i];
    const dx = b.end[0] - a.end[0], dy = b.end[1] - a.end[1];
    if (Math.abs(dx) > 640 || Math.abs(dy) > 400) continue; // particles wrapping at viewport edges
    const sx = a.end[0] - a.start[0], sy = a.end[1] - a.start[1];
    assert.ok(dx > 0 && dy > 0, `${label}: drop moves downwind`);
    assert.ok(sx * dx + sy * dy > 0, `${label}: tip leads its streak`);
    assert.ok(Math.abs(sx * dy - sy * dx) < 1e-7, `${label}: streak aligns with measured velocity`);
    matched++;
  }
  check(matched > before.lines.length / 2, `${label}: most particles track correctly across frames`);
  check(before.splashes.length > 0 && before.splashes.every(([x, y]) => before.lines.some(l => Math.abs(l.end[0] - x) < 1e-8 && Math.abs(l.end[1] - y) < 1e-8)), `${label}: splashes sit at drop tips`);
}
reduced = true;
check(JSON.stringify(frame(0)) === JSON.stringify(frame(10)), 'reduced motion keeps rain stationary');
sandbox.window.Prefs.weather = 0;
check(frame(10).lines.length === 0, 'weather slider still disables rain');
console.log(`rain-direction: ${checks} checks passed`);
