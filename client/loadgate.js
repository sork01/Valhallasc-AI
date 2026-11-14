// Load gate for the loading screen: counts every image and every file under assets/ that is still on its way, so the screen can stay up until the
// world has really finished loading. Must be the first script after compat.js (it patches Image.src and fetch before anything else creates one).
// Combat sound cues (assets/combat/) are deliberately loaded lazily in idle time and are not waited for.
(() => {
  let pending = 0, essential = 0, changed = performance.now();   // `essential`: holds (your own character); the rest are plain downloads
  const waiting = new Map(), started = performance.now();   // what is still on its way (label -> ms since the page started), for diagnosing a slow screen
  let serial = 0;
  const touch = () => { changed = performance.now(); };
  const begin = (label, isHold) => { pending++; if (isHold) essential++; touch(); const key = ++serial; waiting.set(key, { text: `${label || '?'} @${Math.round(performance.now() - started)}ms`, isHold: !!isHold }); return key; };
  const end = key => { const entry = waiting.get(key); if (!entry) return; waiting.delete(key); pending = Math.max(0, pending - 1); if (entry.isHold) essential = Math.max(0, essential - 1); touch(); };

  // Images: every src that is not already complete counts until it loads, fails or is replaced.
  try {
    const proto = HTMLImageElement.prototype, desc = Object.getOwnPropertyDescriptor(proto, 'src');
    if (desc && desc.set) Object.defineProperty(proto, 'src', {
      configurable: true, enumerable: desc.enumerable, get: desc.get,
      set(value) {
        this.__gateDone?.();
        desc.set.call(this, value);
        if (this.complete || this.loading === 'lazy' || typeof value !== 'string' || !value || value.startsWith('data:')) return;
        const key = begin(`img ${value}`);
        let done = false;
        const finish = () => { if (done) return; done = true; this.__gateDone = null; end(key); };
        this.__gateDone = finish;
        this.addEventListener('load', finish, { once: true }); this.addEventListener('error', finish, { once: true });
      },
    });
  } catch (_) {}

  // Files under assets/: counted until the whole body has arrived.
  const realFetch = window.fetch;
  if (typeof realFetch === 'function') window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const track = /(^|\/)assets\//.test(url) && !/assets\/combat\//.test(url) && (!init || init.priority !== 'low');
    const result = realFetch.apply(this, arguments);
    if (!track) return result;
    const key = begin(`fetch ${url}`), finish = () => end(key);
    return result.then(response => {
      let body; try { body = response.clone().arrayBuffer(); } catch (_) { finish(); return response; }
      body.then(finish, finish);
      return response;
    }, error => { finish(); throw error; });
  };

  // The five loading paintings are fetched and decoded as soon as the page starts (while the player is still on the title screen), so the
  // loading screen itself never has to wait for anything. `art.ready` lists the ones that can be painted at once.
  const art = { count: 5, ready: [], keep: [] };
  for (let n = 1; n <= art.count; n++) {
    const img = new Image(); img.decoding = 'async'; img.src = `assets/loading_${n}.webp`; art.keep.push(img);
    (img.decode ? img.decode() : Promise.resolve()).then(() => { art.ready.push(n); }, () => {});
  }

  window.LoadGate = {
    art,
    get pending() { return pending; },
    // Hold the loading screen until the returned function is called. Used for work that is not a plain download: decoding your own character's art.
    hold(label = 'hold') { const key = begin(label, true); let done = false; return () => { if (!done) { done = true; end(key); } }; },
    get waiting() { return [...waiting.values()].map(entry => entry.text); },
    // Resolves once nothing has been loading for `quiet` ms (and at least `minWait` ms have passed). Plain downloads are waited for at most
    // `assetMax` ms; your own character (a hold) at most `max` ms, so a slow connection never keeps you on this screen for long.
    whenIdle({ quiet = 450, minWait = 350, assetMax = 8000, max = 20000 } = {}) {
      const start = performance.now();
      return new Promise(resolve => {
        const check = () => {
          const now = performance.now(), age = now - start;
          if (age >= max || (age >= minWait && essential === 0 && ((pending === 0 && now - changed >= quiet) || age >= assetMax))) resolve(pending === 0);
          else setTimeout(check, 80);
        };
        check();
      });
    },
  };
})();

// Tips under the loading screen (English; Locale translates them at show time). Keep each to one or two short sentences, and never name a key.
window.LoadingTips = {
  list: [
    'Time spent offline builds a rested reserve that gives you extra XP.',
    'Dying costs no XP, but your worn gear loses durability. Repair it at a smith.',
    'When you die you become a ghost. Walk back to your body and choose Resurrect, or find a Spirit Guide.',
    'Talk to a travel master to unlock Spark Travel, then fly between towns.',
    'Mailboxes in towns let you send letters to other players.',
    'Bags full? Sell junk to a merchant or keep your things in the bank.',
    'Every piece of gear takes a cell of its own in your bags, even identical ones.',
    'In a party, green and better gear is rolled for with Need, Greed or Pass.',
    'Elite enemies drop better gear. Bring a party or hire mercenaries.',
    'Hire mercenaries at a Meeting Stone. They always match your level.',
    'Open the world map to see the regions of Veyrheim and the roads between them.',
    'Quest items drop only while you are on the quest and still need them.',
    'Money is counted in copper, silver and gold: 100 copper make 1 silver, and 100 silver make 1 gold.',
    'Every class learns an area skill at level 20.',
    'Point at a buff or debuff icon to see what it does and how long it lasts.',
    'Broken gear stays on but gives no stats. Repair it before your next fight.',
    'Day turns to night in Veyrheim, and every region has its own music.',
    'Edit UI in Settings lets you move and resize the parts of your screen.',
    'A sign stands before each final boss door and explains how to survive its attacks.',
    'Achievements give points and titles. Find them in the Character window.',
    'Starter gear can be sold once you have taken it off.',
    'Level 99 is the highest level. Rebirth gives a lasting bonus to what enemies drop.',
    'Not sure where to go? Open the quest journal and track a quest to see it on the map.',
  ],
  last: -1,
  next() {
    let n; do { n = Math.floor(Math.random() * this.list.length); } while (n === this.last && this.list.length > 1);
    this.last = n; const text = this.list[n];
    return window.Locale?.translate?.(text) || text;
  },
};
