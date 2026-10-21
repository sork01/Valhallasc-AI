// Windows client: a window around the live game. All game code is served by the site,
// so a client fix reaches this app the moment it is saved on the server.
const { app, BrowserWindow, shell, Menu } = require('electron');
const fs = require('fs');
const path = require('path');

const GAME_URL = 'https://gunning.se/Valhallasc/';
const ALLOWED_HOSTS = new Set(['gunning.se', 'www.gunning.se']); // the SSO sign-in is on gunning.se too

// Music starts without waiting for the first click.
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

if (!app.requestSingleInstanceLock()) { app.quit(); }

const stateFile = () => path.join(app.getPath('userData'), 'window-state.json');
function loadState() {
  try { return JSON.parse(fs.readFileSync(stateFile(), 'utf8')); } catch (_) { return {}; }
}
function saveState(win) {
  try {
    const maximized = win.isMaximized();
    const b = maximized ? (loadState().bounds || win.getBounds()) : win.getBounds();
    fs.writeFileSync(stateFile(), JSON.stringify({ bounds: b, maximized, fullscreen: win.isFullScreen() }));
  } catch (_) { /* a lost window size is not worth an error */ }
}

let win;
function create() {
  const st = loadState();
  win = new BrowserWindow({
    width: st.bounds?.width || 1280, height: st.bounds?.height || 720,
    x: st.bounds?.x, y: st.bounds?.y, minWidth: 640, minHeight: 360,
    backgroundColor: '#0a1230', title: 'Valhalla Rumble', autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: false },
  });
  Menu.setApplicationMenu(null);
  if (st.maximized) win.maximize();
  if (st.fullscreen) win.setFullScreen(true);

  const isAllowed = u => { try { const x = new URL(u); return x.protocol === 'https:' && ALLOWED_HOSTS.has(x.hostname); } catch (_) { return false; } };
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowed(url)) return { action: 'allow' };
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (e, url) => {
    if (url.startsWith('file:')) return; // the offline page
    if (!isAllowed(url)) { e.preventDefault(); if (/^https?:/i.test(url)) shell.openExternal(url); }
  });
  // The page title is the game's own; keep the window title fixed.
  win.on('page-title-updated', e => e.preventDefault());
  win.webContents.on('did-fail-load', (_e, code, desc, url, isMainFrame) => {
    if (!isMainFrame || code === -3) return; // -3: aborted by a redirect
    win.loadFile(path.join(__dirname, 'offline.html'), { query: { reason: desc } });
  });
  win.webContents.on('before-input-event', (e, input) => {
    if (input.type !== 'keyDown') return;
    if (input.key === 'F11') { win.setFullScreen(!win.isFullScreen()); e.preventDefault(); }
    else if (input.key === 'F5' || (input.control && input.key.toLowerCase() === 'r')) { win.loadURL(GAME_URL); e.preventDefault(); }
  });
  win.on('close', () => saveState(win));
  win.loadURL(GAME_URL);
}

app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
app.whenReady().then(create);
app.on('window-all-closed', () => app.quit());
