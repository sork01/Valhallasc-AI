const { run } = require('./lib/touch.cjs');
run(['touch-cache', 'touch-input', 'touch-skills', 'touch-windows', 'touch-install', 'low-gfx'].map(n => require(`./${n}-ui.cjs`)))
  .catch(e => { console.error(e); process.exitCode = 1; });
