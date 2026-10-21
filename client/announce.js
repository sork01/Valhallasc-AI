/* Big announcements in the middle of the screen, about 25% down: important world events ("a treasure chest has appeared").
   The server decides what is important and sends {type:'announce', kind, text}; online.js hands the packet here and also writes the line to the chat log.
   Several close together stack (newest at the bottom, at most MAX at once); each fades out by itself. The box never takes clicks.
   API: Announce.show(text, kind). Kinds only choose the colour: treasure, boss, quest, info. */
(() => {
  const MAX = 3, HOLD = 5200, FADE = 700;
  const KINDS = ['treasure', 'boss', 'quest', 'info'];
  function show(text, kind) {
    const box = document.getElementById('announce');
    if (!box || typeof text !== 'string' || !text) return;
    const line = document.createElement('p');
    line.className = 'announce-line';
    line.dataset.kind = KINDS.includes(kind) ? kind : 'info';
    line.textContent = window.Locale?.translate(text) || text;
    box.append(line);
    while (box.children.length > MAX) box.firstElementChild.remove();
    setTimeout(() => { line.classList.add('out'); setTimeout(() => line.remove(), FADE); }, HOLD);
  }
  window.Announce = { show };
})();
