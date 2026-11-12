/* World announcements appear about 25% down; short errors use a separate higher stack.
   The server decides what is important and sends {type:'announce', kind, text}; online.js hands the packet here and also writes the line to the chat log.
   Messages stack newest at the bottom. Errors use five plain red lines that fade over two seconds.
   API: Announce.show(text, kind). Other kinds retain their ordinary announcement presentation. */
(() => {
  const MAX = 3, ERRORS = 5, ERROR_LIFE = 2000, HOLD = 5200, FADE = 700;
  const KINDS = ['treasure', 'boss', 'quest', 'info', 'error'];
  function show(text, kind) {
    const error = kind === 'error';
    const box = document.getElementById(error ? 'error-messages' : 'announce');
    if (!box || typeof text !== 'string' || !text) return;
    const line = document.createElement('p');
    line.className = 'announce-line';
    line.dataset.kind = KINDS.includes(kind) ? kind : 'info';
    line.textContent = window.Locale?.translate(text) || text;
    box.append(line);
    while (box.children.length > (error ? ERRORS : MAX)) box.firstElementChild.remove();
    if (error) setTimeout(() => line.remove(), ERROR_LIFE);
    else setTimeout(() => { line.classList.add('out'); setTimeout(() => line.remove(), FADE); }, HOLD);
  }
  window.Announce = { show, clearErrors() { document.getElementById('error-messages')?.replaceChildren(); } };
})();
