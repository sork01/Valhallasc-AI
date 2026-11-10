'use strict';
// Smooth motion between server snapshots. The server sends each actor's position about every 100 ms; the screen is drawn at the
// display's rate (60 fps). Chasing the latest position with a plain ease-out makes the sprite surge when a snapshot lands and
// slow before the next one, a pulse at the snapshot rate that reads as stutter. Instead each actor carries the velocity between
// its last two snapshots (measured on the server's own clock, so network jitter does not disturb it) and is drawn on the line
// those snapshots lie on, a fixed `lag` behind the newest one:
//   target = server position + velocity * (age of the snapshot - lag)
// With a steady velocity the target is continuous across a snapshot (the position advances by velocity * gap just as the age falls
// by `gap`), so the sprite glides. Other actors lag a whole gap behind (an interpolation: it never runs past the truth, so it
// cannot overshoot a stop); the hero lags less (0.7 of a gap) to stay responsive. A stationary actor has zero velocity and eases
// to its position exactly as before. Pure maths (no DOM, no canvas), so it is tested on its own: tests/actor-motion.cjs.
(() => {
  const DEFAULT_GAP = .1;   // seconds between snapshots until two have been seen (10 Hz)
  const MAX_GAP = .25;      // a longer gap (a dropped snapshot or two) is still interpolated across, up to this long
  const MIN_GAP = .03;
  const TYPICAL_MAX = .12;  // a gap counts towards the typical interval only up to this (a lost snapshot is not the rate)
  const SPEED_MAX = 20;     // tiles/s: faster than a walk, a mount or Spark Travel means a dash or a teleport, so no velocity
  const FOLLOW = 14;        // 1/s: how fast the drawn position closes a gap to its target (the rate the old ease-out used)
  const HERO_LAG = .7;      // the hero's lag as a fraction of the gap
  const SLACK = .04;        // seconds a late snapshot may be extrapolated past one gap before the sprite holds still
  const OFFSET_RISE = .05;  // per snapshot: how fast the clock offset may grow (a falling offset is believed at once)
  const LATE_MAX = .2;      // seconds: the deepest extra buffer a jittery link may ask for
  const LATE_DECAY = .95;   // per snapshot: how fast the extra buffer is given back once the link steadies
  const HERO_LATE = .5;     // the hero takes this share of the extra buffer (it trades some smoothness for response)
  const finite = Number.isFinite;

  // Snapshots arrive unevenly (Wi-Fi, a busy browser, a bursty link), so an actor's age is not measured from when its snapshot
  // arrived but from the server's own clock, mapped to the local clock by an offset that follows the LEAST delayed packets: a
  // packet cannot arrive early, so a smaller (local arrival - server time) is closer to the truth, and a late one is ignored.
  // `late` is how far behind that offset the recent packets ran: the buffer a jittery link needs on top of one snapshot gap. It grows
  // at once with a late packet and decays slowly, so a steady link has no extra delay and a bursty one gets a deeper buffer.
  const clock = { t: NaN, offset: NaN, late: 0 };
  function observe(serverTime, now) {
    if (!finite(serverTime)) return null;
    const sample = now - serverTime;
    if (!finite(clock.offset) || serverTime < clock.t - 1) { clock.offset = sample; clock.late = 0; }   // first packet, or the server restarted
    else if (serverTime !== clock.t) {
      clock.offset = sample < clock.offset ? sample : clock.offset + (sample - clock.offset) * OFFSET_RISE;
      clock.late = Math.min(LATE_MAX, Math.max(sample - clock.offset, clock.late * LATE_DECAY));
    }
    clock.t = serverTime;
    return clock.offset;
  }
  const resetClock = () => { clock.t = NaN; clock.offset = NaN; clock.late = 0; };

  // A snapshot has just set `actor.nx/ny` (the server position) from (x, y); `prevX/prevY` are the previous server position.
  // `serverTime` is the snapshot's server clock (seconds) and `now` the local clock (seconds) when it arrived.
  // `snap` means the actor was placed rather than moved (first sight, a zone change, a teleport): no velocity.
  function track(actor, prevX, prevY, x, y, serverTime, now, snap) {
    const t = finite(serverTime) ? serverTime : now;
    const gap = t - actor.mT;
    if (finite(actor.mT) && gap < 1e-3 && gap > -1e-3 && !snap) return;   // the same snapshot applied twice: keep what we have
    let vx = 0, vy = 0, g = actor.mGap || DEFAULT_GAP;
    if (!snap && finite(actor.mT) && finite(prevX) && finite(prevY) && gap > 1e-3 && gap <= MAX_GAP) {
      const ax = (x - prevX) / gap, ay = (y - prevY) / gap;
      if (Math.hypot(ax, ay) <= SPEED_MAX) { vx = ax; vy = ay; }
      // The lag follows the typical interval, not the last one, so a lost snapshot does not shift the whole timeline.
      const typical = Math.min(TYPICAL_MAX, Math.max(MIN_GAP, gap));
      g = actor.mGap ? actor.mGap + (typical - actor.mGap) * .25 : typical;
    }
    // mAt: when this snapshot is due on the local clock (its server time plus the least-delay offset), not when it happened to arrive.
    const offset = observe(serverTime, now);
    actor.mVx = vx; actor.mVy = vy; actor.mT = t; actor.mAt = offset === null ? now : serverTime + offset; actor.mGap = g;
  }

  // One frame: move the drawn position (actor.x/y) towards its target. `now` is the local clock (seconds); `dt` is only the fallback
  // frame time for an actor's first step. The step is taken from the clock itself, the same one the snapshot ages are read from, so
  // an uneven frame cannot make the carry and the target disagree (a frame callback runs later than the vsync time it is given).
  function step(actor, dt, now, isHero) {
    if (!finite(actor.nx) || !finite(actor.ny)) return;
    if (finite(actor.mStepAt) && now >= actor.mStepAt) dt = Math.min(now - actor.mStepAt, .1);
    actor.mStepAt = now;
    const g = actor.mGap || DEFAULT_GAP, vx = actor.mVx || 0, vy = actor.mVy || 0;
    const late = clock.late, age = Math.max(0, now - (finite(actor.mAt) ? actor.mAt : now)), maxAge = g + late + SLACK;
    const lead = Math.min(age, maxAge) - (g * (isHero ? HERO_LAG : 1) + late * (isHero ? HERO_LATE : 1));
    const tx = actor.nx + vx * lead, ty = actor.ny + vy * lead;
    // Carry the sprite along with the target's own motion, then close what is left of the gap. The carry stops when the target
    // does (an overdue snapshot), or the sprite would keep running past it.
    const carry = age < maxAge ? dt : 0;
    const px = actor.x + vx * carry, py = actor.y + vy * carry, k = Math.min(1, dt * FOLLOW);
    actor.x = px + (tx - px) * k; actor.y = py + (ty - py) * k;
  }

  const api = { DEFAULT_GAP, MAX_GAP, SPEED_MAX, FOLLOW, HERO_LAG, SLACK, track, step, resetClock };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else window.ActorMotion = api;
})();
