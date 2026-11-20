// Explicitly choose the saved guest when a reconnect fixture reaches the picker.
// New browsers still land in creation; dedicated choice tests use the picker directly.
const warning = 'Guest progress is tied to this browser. Clearing browser data or losing this browser can make your character and progress inaccessible. Use an account to keep access across devices. Continue as guest?';
const warnings = [warning, JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname, '../../scripts/sv-translations.txt'), 'utf8'))[warning]];
async function playGuest(page) {
  const accept = async dialog => {
    if (!warnings.includes(dialog.message())) throw Error('Unexpected dialog while choosing guest');
    await dialog.accept();
  };
  page.on('dialog', accept);
  try { await page.locator('#login-guest').click(); } finally { page.off('dialog', accept); }
  if (await page.locator('#scene-chars').isVisible()) {
    const selected = await page.evaluate(() => Online.characters.findIndex(c => c.key === Online.currentKey));
    await page.locator('.char-play').nth(Math.max(0, selected)).click();
  }
}
module.exports = { playGuest };
