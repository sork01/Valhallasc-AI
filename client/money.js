'use strict';
// Money (COIN-DENOMINATIONS). Every amount in the game is one whole number of COPPER: 100 copper = 1 silver, 100 silver = 1 gold.
// The server, the saves and every field called `gold` keep that number unchanged; only what the player reads is split here.
//   Money.parts(n)  -> { gold, silver, copper }
//   Money.text(n)   -> "12 gold 34 silver 5 copper" (zero parts hidden, "0 copper" for nothing), for titles, notices and messages
//   Money.short(n)  -> "12g 34s 5c", for the canvas (floating numbers)
//   Money.html(n)   -> the same amount as numbers with small coin icons, for the DOM; Money.set(el, n) fills an element with it
(() => {
  const SILVER = 100, GOLD = 10000;
  const parts = amount => {
    const n = Math.max(0, Math.floor(Number(amount) || 0));
    return { gold: Math.floor(n / GOLD), silver: Math.floor(n / SILVER) % 100, copper: n % SILVER };
  };
  const group = n => n.toLocaleString('en-US');
  const list = amount => {
    const p = parts(amount), out = [];
    if (p.gold) out.push(['gold', p.gold]);
    if (p.silver) out.push(['silver', p.silver]);
    if (p.copper || !out.length) out.push(['copper', p.copper]);
    return out;
  };
  const tr = value => window.Locale?.translate(value) || value;
  const text = amount => list(amount).map(([unit, n]) => tr(`${group(n)} ${unit}`)).join(' ');
  const short = amount => list(amount).map(([unit, n]) => `${group(n)}${unit[0]}`).join(' ');
  const COLORS = { gold: ['#fff1a6', '#e0a526', '#8a5d0c'], silver: ['#ffffff', '#c3ccd6', '#6d7886'], copper: ['#ffd2a8', '#cf7a3d', '#7b3d17'] };
  // Numbers with a small coin each. The words stay in the markup for screen readers (and for text search): "12 gold 34 silver 5 copper".
  function html(amount) {
    const inner = list(amount).map(([unit, n]) => `<b class="money-n">${group(n)}</b><i class="coin coin-${unit}" aria-hidden="true"></i><span class="sr-only"> ${unit} </span>`).join('');
    return `<span class="money" data-copper="${Math.max(0, Math.floor(Number(amount) || 0))}">${inner}</span>`;
  }
  const set = (element, amount) => { if (element) element.innerHTML = window.Money.html(amount); return element; };
  // A number field that takes copper shows what it comes to in gold, silver and copper right beside it.
  function preview(input) {
    if (!input || input.dataset.moneyPreview) return;
    input.dataset.moneyPreview = '1';
    const note = document.createElement('small'); note.className = 'money-preview'; note.setAttribute('aria-live', 'polite');
    const update = () => { note.textContent = Money.text(Number(input.value) || 0); };
    input.addEventListener('input', update); input.addEventListener('change', update); input.after(note); update();
    return update;
  }
  window.Money = { preview, parts, text, short, html, set, list, COLORS, SILVER, GOLD };
})();
