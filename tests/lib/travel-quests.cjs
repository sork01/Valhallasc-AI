// A high-level hero leaving the starting dock is handed every automatic "Onward to ..." quest, which fills the 20 slot
// journal. For suites that need room: abandon each as it arrives, through the normal journal action.
module.exports = page => page.addInitScript(() => {
  const sent = new Set();
  setInterval(() => {
    if (!window.Online?.connected) return;
    for (const q of window.Field?.hero?.quests || []) {
      const key = `${Field.hero.id}:${q.id}`;
      if (q.claimed || !q.id.endsWith('_onward') || sent.has(key)) continue;
      sent.add(key);
      Online.send({ type: 'quest_abandon', id: q.id });
    }
  }, 50);
});
