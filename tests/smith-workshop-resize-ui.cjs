// Run through scripts/test-touch-bounded.sh with the Valhalla release executable.
const { run, replace, debug, touch } = require('./lib/touch.cjs');

const suite = {
  name: 'smith-workshop-resize',
  mutate(page) {
    return replace(page, 'settings.js', 'if (resize?.pointer !== event.pointerId) return;\n      // A centered window',
      'return;\n      // A centered window');
  },
  async test({ player, check, width }) {
    const phone = width < 900;
    const page = await player('WorkshopSize', {characterClass:'warrior', isMobile:phone, hasTouch:phone});
    const press = locator => phone ? locator.tap() : locator.click();
    const smith = await page.evaluate(() => WORLD_MAP.npcs.find(npc => npc.id === 'smith'));
    await debug(page, {op:'teleport',zone:0,x:smith.x,y:smith.y});
    await page.waitForFunction(({x,y}) => Math.hypot(Field.hero.x-x,Field.hero.y-y) < 1, smith);
    await page.evaluate(npc => Online.send({type:'interact',npc}), smith.id);

    const frame = page.locator('#npc-dialogue > .gossip-window');
    const grip = page.locator('#npc-smith-resize');
    const workshop = page.locator('#npc-offers [data-view="smith"]');
    await workshop.waitFor();
    const conversation = await frame.boundingBox();
    check(await grip.isHidden(), 'the greeting has its normal layout without a workshop grip');
    await press(workshop);
    const train = page.locator('#npc-inventory button');
    await press(train);
    await page.locator('.smith-recipes .smith-recipe').first().waitFor();

    const stage = await page.locator('#stage').boundingBox();
    const initial = await frame.boundingBox();
    const parchment = page.locator('#npc-quest-page');
    const initialRows = await parchment.evaluate(el => el.clientHeight);
    check(initial.width >= Math.min(780, stage.width * .87) - 2, 'the workshop opens wider');
    check(initial.height >= Math.min(610, stage.height * .86) - 2, 'the workshop opens with more room for recipes');
    const handle = await grip.boundingBox();
    check(handle && (!phone || handle.height >= 43.5), 'the workshop has a usable corner grip outside Edit UI');
    const corner = await grip.evaluate(el => {
      const r = el.getBoundingClientRect();
      const target = document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
      const root = el.closest('#npc-dialogue'), frame = el.closest('.gossip-window');
      return { hit:el.contains(target), target:target?.id || target?.className,
        root:root.getBoundingClientRect().toJSON(), frame:frame.getBoundingClientRect().toJSON(),
        columns:getComputedStyle(root).gridTemplateColumns, rows:getComputedStyle(root).gridTemplateRows,
        scale:getComputedStyle(frame).scale,
        viewport: [innerWidth,innerHeight,scrollX,scrollY] };
    });
    check(corner.hit, 'the corner grip is inside the viewport and receives input ' + JSON.stringify({stage,handle,corner}));

    const x = handle.x + handle.width / 2, y = handle.y + handle.height / 2;
    if (phone) {
      const dispatch = await touch(page);
      await dispatch('touchStart', [[0,x,y]]);
      await dispatch('touchMove', [[0,x-35,y-22]]);
      await dispatch('touchMove', [[0,x-65,y-38]]);
      await dispatch('touchEnd', []);
    } else {
      await page.mouse.move(x,y);
      await page.mouse.down();
      await page.mouse.move(x-65,y-38,{steps:5});
      await page.mouse.up();
    }
    const smaller = await frame.boundingBox();
    const close = (a,b) => Math.abs(a-b) <= 2;
    check(close(smaller.width, initial.width-130) && close(smaller.height, initial.height-76),
      'the grip changes both physical dimensions around the window center ('
        + JSON.stringify({initial,smaller,saved:await page.evaluate(() => Prefs.panelSize.smith)}) + ')');
    check(await parchment.evaluate(el => el.clientHeight) < initialRows - 40,
      'resizing changes the amount of recipe content shown');
    const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).panelSize.smith);
    check(close(saved.w, smaller.width) && close(saved.h, smaller.height), 'the workshop records its own size');
    check(smaller.x >= stage.x && smaller.y >= stage.y && smaller.x+smaller.width <= stage.x+stage.width
      && smaller.y+smaller.height <= stage.y+stage.height, 'the resized frame stays within the stage');

    await press(page.locator('#npc-back'));
    const greeting = await frame.boundingBox();
    check(await grip.isHidden() && close(greeting.width,conversation.width) && close(greeting.height,conversation.height),
      'the normal conversation size stays independent');
    await press(workshop);
    const reopened = await frame.boundingBox();
    check(close(reopened.width,smaller.width) && close(reopened.height,smaller.height), 'reopening uses the saved size');
    await grip.focus();
    await page.keyboard.press('ArrowRight');
    check(close((await frame.boundingBox()).width,smaller.width + 16), 'the keyboard can resize the workshop');
    if (phone) await page.keyboard.press('0');
    else await grip.dblclick();
    const reset = await frame.boundingBox();
    check(close(reset.width,initial.width) && close(reset.height,initial.height), 'reset restores the larger default');
    await page.context().close();
  },
};

run([suite]).catch(error => { console.error(error); process.exitCode = 1; });
