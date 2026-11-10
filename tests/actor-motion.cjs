// UI-ACTOR-MOTION, the maths: how a sprite moves between 10 Hz server snapshots (client/actormotion.js is pure, so it runs here
// without a browser). A 60 fps frame loop is fed snapshots with arrival jitter and compared with the ease-out it replaced:
// the old one pulsed at the snapshot rate, the new one glides. `MOTION_FILE=<path>` runs the same checks on a mutated copy of the
// module; checked 2026-11-10, each of these fails: no carry, carry forever, no lag, hero lagging like the others, no dash speed cap,
// no velocity reset on a placement, ages from arrival times, no jitter buffer, a clock offset that is not the least-delay one, a
// clock updated per actor.
const assert = require('node:assert/strict');
const path = require('node:path');
const M = require(process.env.MOTION_FILE ? path.resolve(process.env.MOTION_FILE) : '../client/actormotion.js');

const FRAME = 1 / 60, GAP = .1, SPEED = 5.2;
let seed = 20261110;
const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32;
const OLD_RATE = 14;

// One actor on a line, moving at `speed` tiles/s until `stopAt` seconds, then standing. `skip` lists snapshot numbers that never arrive.
// Returns the drawn x at every frame and the server x (nx) it was chasing.
function run({ legacy = false, hero = false, speed = SPEED, stopAt = 3, until = 4.5, jitter = .015, burst = false, delay = {}, skip = [], jumps = {} }) {
  M.resetClock();
  // The server's snapshots: number n has server clock n * GAP and the position of an actor that walks at `speed` until `stopAt`.
  const snapshots = [];
  let server = 0;
  for (let n = 0; n * GAP <= until + 1; n++) {
    const st = n * GAP;
    server += (st < stopAt ? speed : 0) * GAP + (jumps[n] || 0);
    if (skip.includes(n)) continue;
    // network delay plus jitter; `burst` holds every odd snapshot back one gap so it arrives together with the next (a stalled link catching up)
    snapshots.push({ n, st, x: server, arrival: st + .02 + (rnd() * 2 - 1) * jitter + (burst && n % 2 === 0 ? GAP : 0) + (delay[n] || 0) });
  }
  for (let i = 1; i < snapshots.length; i++) snapshots[i].arrival = Math.max(snapshots[i].arrival, snapshots[i - 1].arrival);   // in order, like a WebSocket
  const actor = { x: 0, y: 0, nx: 0, ny: 0 }, frames = [];
  let next = 0;
  for (let t = 0; t <= until + 1e-9; t += FRAME) {
    while (next < snapshots.length && snapshots[next].arrival <= t) {
      const s = snapshots[next++], prev = actor.nx;
      actor.nx = s.x; actor.ny = 0;
      if (next === 1) actor.x = s.x;                                          // first sight: placed, not moved
      if (!legacy) M.track(actor, prev, 0, s.x, 0, s.st, s.arrival, next === 1);
    }
    if (legacy) { const k = Math.min(1, FRAME * OLD_RATE); actor.x += (actor.nx - actor.x) * k; }
    else M.step(actor, FRAME, t, hero);
    frames.push({ t, x: actor.x, nx: actor.nx });
  }
  return frames;
}
const steps = (frames, from, to) => frames.filter(f => f.t > from && f.t < to).map((f, i, a) => i ? f.x - a[i - 1].x : null).slice(1);
const stats = a => { const m = a.reduce((s, v) => s + v, 0) / a.length, sd = Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / a.length); return { mean: m, sd, cv: sd / m, min: Math.min(...a), max: Math.max(...a) }; };

// 1. Steady walking: the old ease-out pulsed (frame steps varied wildly), the new motion glides.
{
  const oldS = stats(steps(run({ legacy: true }), 1, 2.9)), newS = stats(steps(run({}), 1, 2.9)), heroS = stats(steps(run({ hero: true }), 1, 2.9));
  console.log(`steady walk, frame step coefficient of variation: old ${oldS.cv.toFixed(3)}, new ${newS.cv.toFixed(3)}, hero ${heroS.cv.toFixed(3)}`);
  assert.ok(oldS.cv > .3, `the old ease-out should be uneven (cv ${oldS.cv})`);
  assert.ok(newS.cv < .12, `walking must glide, not pulse (cv ${newS.cv})`);
  assert.ok(heroS.cv < .12, `the hero must glide too (cv ${heroS.cv})`);
  assert.ok(newS.min > 0, 'the sprite never stands still or steps back mid-walk');
  assert.ok(Math.abs(newS.mean - SPEED * FRAME) < .004, `average speed is the server speed (${newS.mean} vs ${SPEED * FRAME})`);
  assert.ok(newS.max < 1.5 * SPEED * FRAME, `no frame jumps more than half again the walking step (${newS.max})`);
}

// 2. The velocity is read from the server's clock, not the arrival times: jitter changes nothing about it.
{
  M.resetClock();
  const a = { x: 0, y: 0, nx: 0, ny: 0 };
  M.track(a, undefined, undefined, 0, 0, 0, 100, true);
  a.nx = .52; M.track(a, 0, 0, .52, 0, .1, 100.123, false);
  assert.ok(Math.abs(a.mVx - 5.2) < 1e-9 && a.mVy === 0, `velocity is distance over server time (${a.mVx})`);
  a.nx = 1.04; M.track(a, .52, 0, 1.04, 0, .2, 100.19, false);
  assert.ok(Math.abs(a.mVx - 5.2) < 1e-9, 'a snapshot that arrived late and one that arrived early give the same velocity');
}

// 3. Stopping: the sprite settles on the server position without running past it, and the hero's small lead stays small.
for (const hero of [false, true]) {
  const f = run({ hero }), final = f.at(-1).nx;
  const over = Math.max(...f.map(p => p.x)) - final;
  assert.ok(over < (hero ? .25 : .02), `${hero ? 'hero' : 'actor'} runs ${over.toFixed(3)} tiles past where the server stopped it`);
  assert.ok(Math.abs(f.at(-1).x - final) < .005, `${hero ? 'hero' : 'actor'} settles on the server position`);
  const settled = f.filter(p => p.t > 3.0 + .6);
  assert.ok(settled.every(p => Math.abs(p.x - final) < .02), `${hero ? 'hero' : 'actor'} is at rest within 0.6 s of the stop`);
}

// 4. The hero is drawn closer to the server position than others (it stays responsive); others lag a whole gap.
{
  const gapTo = frames => stats(frames.filter(f => f.t > 1 && f.t < 2.9).map(f => f.nx - f.x)).mean;
  const other = gapTo(run({})), hero = gapTo(run({ hero: true }));
  console.log(`mean distance behind the server position while walking: actor ${other.toFixed(3)}, hero ${hero.toFixed(3)} tiles (old ease-out ${gapTo(run({ legacy: true })).toFixed(3)})`);
  assert.ok(hero < other * .6, `the hero lags well under other actors (${hero.toFixed(3)} against ${other.toFixed(3)})`);
  assert.ok(hero < .3 && hero > -.1, 'the hero is never far from the server position');
  assert.ok(other < .6, 'other actors trail by at most about one snapshot of travel');
}

// 5. A dropped snapshot is interpolated across, not jumped or stalled.
{
  const f = run({ skip: [15] }), s = stats(steps(f, 1, 2.9));
  assert.ok(s.max < 2.2 * SPEED * FRAME, `one lost snapshot must not make a jump or a stall (max ${s.max}, min ${s.min})`);
  assert.ok(s.min > 0, 'no step back after a lost snapshot');
}

// 6. A dash or teleport (far faster than any walk) gets no velocity, so nothing is thrown past the target.
{
  const f = run({ stopAt: 0, jumps: { 10: 6 } }), final = f.at(-1).nx;
  assert.ok(Math.max(...f.map(p => p.x)) - final < .005, 'a 6-tile dash is eased in, never overshot');
  const a = { x: 0, y: 0, nx: 0, ny: 0 };
  M.track(a, undefined, undefined, 0, 0, 0, 0, true); M.track(a, 0, 0, 8, 0, .1, .1, false);
  assert.equal(a.mVx, 0, '80 tiles/s is not a velocity');
}

// 7. A zone change or first sight (snap) clears the velocity.
{
  M.resetClock();
  const a = { x: 0, y: 0, nx: 0, ny: 0 };
  M.track(a, undefined, undefined, 0, 0, 0, 0, true); M.track(a, 0, 0, .52, 0, .1, .1, false);
  assert.ok(a.mVx > 5);
  M.track(a, .52, 0, 1.04, 0, .2, .2, true);   // a placement at a plausible speed: still no velocity
  assert.equal(a.mVx, 0, 'placing an actor leaves it with no velocity');
}

// 8. A stationary actor eases to its position exactly as the old code did.
{
  M.resetClock();
  const a = { x: 0, y: 0, nx: 1, ny: 0 }, b = { x: 0 };
  M.track(a, 1, 0, 1, 0, 0, 0, true);
  for (let i = 0; i < 20; i++) { M.step(a, FRAME, i * FRAME, false); b.x += (1 - b.x) * Math.min(1, FRAME * OLD_RATE); }
  assert.ok(Math.abs(a.x - b.x) < 1e-12, `a standing actor eases like before (${a.x} vs ${b.x})`);
}

// 9. A late snapshot is extrapolated a little, then the sprite holds: it never runs away.
{
  M.resetClock();
  const a = { x: 0, y: 0, nx: 0, ny: 0 };
  M.track(a, undefined, undefined, 0, 0, 0, 0, true);
  a.nx = .52; M.track(a, 0, 0, .52, 0, .1, .1, false);
  let x = 0; for (let t = .1; t < 3; t += FRAME) { M.step(a, FRAME, t, false); x = a.x; }
  assert.ok(x < .52 + 5.2 * M.SLACK + .01, `with no further snapshot the sprite stops near the last position (${x})`);
}

// 10. Missing or non-finite input never poisons a position.
{
  M.resetClock();
  const a = { x: 3, y: 4 };
  M.step(a, FRAME, 1, false);
  assert.deepEqual([a.x, a.y], [3, 4], 'no server position, no move');
  const b = { x: 0, y: 0, nx: 1, ny: 1 };
  M.track(b, NaN, NaN, 1, 1, NaN, 5, false); M.step(b, FRAME, 5.01, false);
  assert.ok(Number.isFinite(b.x) && Number.isFinite(b.y), 'NaN in, finite out');
}

// 11. Uneven delivery: the snapshots' arrival times wobble by +-45 ms, or arrive in pairs after a stall. The age is read from the
// server's clock (through the least-delay offset), so the glide survives; reading it from the arrival times does not.
for (const [label, opts] of [['45 ms jitter', { jitter: .045 }], ['batched pairs', { burst: true }], ['batched pairs, hero', { burst: true, hero: true }]]) {
  const oldS = stats(steps(run({ ...opts, legacy: true }), 1, 2.9)), newS = stats(steps(run(opts), 1, 2.9));
  console.log(`${label}: frame step cv old ${oldS.cv.toFixed(3)}, new ${newS.cv.toFixed(3)}`);
  assert.ok(newS.cv < .2 && newS.cv < oldS.cv * .6, `${label}: must still glide (cv ${newS.cv} against ${oldS.cv} before)`);
  assert.ok(newS.min >= 0, `${label}: never steps back`);
}

// 12. One snapshot arrives 150 ms late (a stall), the rest on time. The extra buffer it asks for is taken up gradually: the sprite
// may hitch once but never runs backwards or surges, and it settles back to the walking speed.
{
  const f = run({ delay: { 20: .15 } }), s = steps(f, 1.2, 2.9), after = steps(f, 2.7, 2.95);
  console.log(`one 150 ms stall: smallest frame step ${Math.min(...s).toFixed(4)}, largest ${Math.max(...s).toFixed(4)} (walking step ${(SPEED * FRAME).toFixed(4)})`);
  assert.ok(Math.min(...s) >= 0, 'a stall never makes the sprite step back');
  assert.ok(Math.max(...s) < 3 * SPEED * FRAME, 'and never makes it surge');
  assert.ok(Math.abs(stats(after).mean - SPEED * FRAME) < .012, 'it is back at the walking speed afterwards');
}
// 13. Every actor in a snapshot shares one clock reading: 30 actors give the same offset as 1 (the clock is updated per snapshot, not per actor).
{
  const final = count => {
    M.resetClock();
    const actors = Array.from({ length: count }, () => ({ x: 0, y: 0, nx: 0, ny: 0 }));
    for (let k = 0; k < 40; k++) for (const a of actors) {
      const prev = a.nx; a.nx = k * .52;
      M.track(a, prev, 0, a.nx, 0, k * GAP, k * GAP + (k % 4 === 0 ? .02 : .09), k === 0);
    }
    return actors[0].mAt;
  };
  assert.ok(Math.abs(final(1) - final(30)) < 1e-12, 'the clock offset must not depend on how many actors a snapshot carries');
}
console.log('actor-motion: ok');
