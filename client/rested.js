'use strict';
// The server owns the reserve. Opening this readout never changes or requests XP.
window.Rested = (() => {
  const holder = document.createElement('div');
  holder.id = 'rested'; holder.hidden = true;
  const button = document.createElement('button');
  button.id = 'rested-status'; button.type = 'button';
  button.setAttribute('aria-expanded', 'false'); button.setAttribute('aria-controls', 'rested-details');
  const panel = document.createElement('div');
  panel.id = 'rested-details'; panel.hidden = true;
  for (const text of [
    'Rested grants 200% more XP from monsters and quests while your reserve lasts.',
    'Earn 5% Rested per hour offline, up to 200% after 40 hours.',
    '100% Rested stores bonus XP equal to one level. Extra XP uses this reserve.',
  ]) {
    const p = document.createElement('p'); p.textContent = text; panel.append(p);
  }
  holder.append(button, panel); document.querySelector('.hud-bars').append(holder);
  const frame = holder.closest('.hud-tl');
  const close = () => { panel.hidden = true; button.setAttribute('aria-expanded', 'false'); frame.classList.remove('rested-open'); };
  button.addEventListener('click', () => {
    panel.hidden = !panel.hidden; button.setAttribute('aria-expanded', String(!panel.hidden));
    frame.classList.toggle('rested-open', !panel.hidden);
  });
  document.addEventListener('pointerdown', e => { if (!holder.contains(e.target)) close(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !panel.hidden) { close(); e.stopImmediatePropagation(); button.focus(); }
  }, true);
  return {
    update(s) {
      holder.hidden = !s.rested;
      if (holder.hidden) { close(); return; }
      const percent = Math.max(0, Math.min(200, Number(s.rested.percent) || 0));
      // Round down so a nearly full reserve is never advertised as full.
      const amount = Math.floor(percent * 10) / 10;
      const text = `Rested: ${amount}% / 200%`;
      const translated = window.Locale?.translate(text) || text;
      if (button.textContent !== translated) button.textContent = translated;
      holder.classList.toggle('rested-active', percent > 0);
    },
  };
})();
