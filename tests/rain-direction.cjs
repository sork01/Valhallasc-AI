// Sample actual weather drawing across frames: the streak must follow the drop's motion.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
let source = fs.readFileSync(process.env.WEATHER_CANDIDATE || path.join(__dirname, '../client/weather.js'), 'utf8');
if (process.env.MUTATE === 'direction') source = source.replace(
  'g.moveTo(x-vx*trail,y-vy*trail); g.lineTo(x,y);',
  'g.moveTo(x,y); g.lineTo(x-5-a*3,y+14+a*11);');
if (process.env.MUTATE === 'camera') source = source.replace('time*wind-view.x', 'time*wind').replace('time*speed-view.y', 'time*speed');
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
function frame(time, camera) {
  const lines = [], splashes = []; let start = null, end = null;
  const g = {
    save() {}, restore() {}, fillRect() {},
    beginPath() { start = end = null; },
    moveTo(x, y) { start = [x, y]; }, lineTo(x, y) { end = [x, y]; },
    stroke() { if (start && end) lines.push({ start, end }); },
    ellipse(x, y) { splashes.push([x, y]); },
  };
  weather.draw(g, 1280, 800, time, camera);
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
for (const type of ['rain', 'thunderstorm']) {
  const speeds = [];
  for (const direction of [0, -1, 1]) {
    weather.setZone({ theme: 'meadow' });
    weather.sync({ type, intensity: 'heavy', inside: false, ageSeconds: 50, endsInSeconds: 100 }, 0, 0);
    weather.tick(2);
    const dt = .01, a = frame(10, { x: 0, y: 0 }), b = frame(10 + dt, { x: direction * 40 * dt, y: direction * 120 * dt });
    let total = 0, count = 0;
    for (let i = 0; i < a.lines.length; i++) {
      const from = a.lines[i].end, to = b.lines[i].end, dx = to[0] - from[0], dy = to[1] - from[1];
      if (Math.abs(dx) > 640 || Math.abs(dy) > 400) continue;
      const sx = to[0] - b.lines[i].start[0], sy = to[1] - b.lines[i].start[1];
      assert.ok(Math.abs(sx * dy - sy * dx) < 1e-7, `${type}: streak follows camera-relative motion`);
      total += Math.hypot(dx, dy) / dt; count++;
    }
    check(count > 0, `${type}: moving-camera particles are measurable`);
    speeds.push(total / count);
  }
  check(speeds[1] > speeds[0] && speeds[2] < speeds[0], `${type}: walking into rain speeds it up; walking with rain slows it down`);
  const jumped = frame(10.02, { x: 100000, y: -100000 });
  check(jumped.lines.every(l => Math.hypot(l.end[0] - l.start[0], l.end[1] - l.start[1]) < 50), `${type}: teleport does not make oversized streaks`);
}
reduced = true;
check(JSON.stringify(frame(0, { x: 0, y: 0 })) === JSON.stringify(frame(10, { x: -100, y: 200 })), 'reduced motion keeps rain stationary');
sandbox.window.Prefs.weather = 0;
check(frame(10).lines.length === 0, 'weather slider still disables rain');
console.log(`rain-direction: ${checks} checks passed`);
