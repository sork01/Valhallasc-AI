'use strict';
(() => {
  // ---------- tiny persistent state ----------
  const KEY = 'valhallasc.save.v1';
  const defaults = { lang: /^ko/i.test(navigator.language || '') ? 'ko' : 'en', sound: true, musicVol: 1, sfxVol: 1, ui: {}, char: null, draft: null };
  let save = { ...defaults };
  try { Object.assign(save, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { /* private mode */ }
  const vol = v => Number.isFinite(+v) ? Math.max(0, Math.min(1, +v)) : 1;
  save.musicVol = vol(save.musicVol); save.sfxVol = vol(save.sfxVol);
  const persist = () => { try { localStorage.setItem(KEY, JSON.stringify(save)); } catch (e) { /* ignore */ } };

  // ---------- text ----------
  const T = {
    en: {
      soundOn: 'Sound on (M)', soundOff: 'Sound off (M)',
      back: 'Back', toTitle: 'Back to Title', newChar: 'New Character',
      ccTitle: 'Assemble Your Warband!', forged: 'Forged in Battle!',
      warriorDesc: 'A brave sword-and-shield vanguard. High health, strong melee attacks, and armor ready for the front lines.',
      warriorHint: 'Click to move or attack · WASD to walk · Space to swing · 1–9 skills · E character · B bags · F talk · Esc for menu',
      arms: 'Weapons', warriorTip: 'Click the Warrior to swing. Change armor and weapons in the field with E.',
      warriorLoading: 'Calling the Warrior…', warriorError: 'Warrior sprites could not load. Select Warrior again to retry.',
      warriorArmorNames: ['Simple cloth', 'Crimson guard', 'Azure guard'], warriorWeaponNames: ['Empty hands', 'Sword & shield', 'Royal sword & shield'],
      mageDesc: 'A rune caster with powerful ranged spells. Equip robes and staffs to change your look and strength.',
      mageHint: 'Click to move or cast · WASD to walk · Space to cast · 1–9 skills · E character · B bags · F talk · Esc for menu',
      equipment: 'Character (E)', gender: 'Body', male: 'Male', female: 'Female', hair: 'Hair', weapon: 'Staff', mageTip: 'Click the Mage to cast. Robes and staffs can be changed in the field with E.',
      mageLoading: 'Summoning the Mage…', mageError: 'Mage sprites could not load. Select Mage again to retry.',
      mageArmorNames: ['Simple cloth', 'Apprentice', 'Runic'], mageWeaponNames: ['Empty hands', 'Ash staff', 'Crystal staff'],
      assassinDesc: 'A swift duelist with twin blades and deadly critical strikes. Shadowstep through danger with Shift.',
      assassinHint: 'Click to move or attack · WASD to walk · Space to slash · Shift to shadowstep · 1–9 skills · E character · B bags · F talk · Esc for menu',
      blades: 'Blades', assassinTip: 'Click the Assassin to slash. Change outfits and blades in the field with E.',
      assassinLoading: 'Calling the Assassin…', assassinError: 'Assassin sprites could not load. Select Assassin again to retry.',
      assassinArmorNames: ['Simple cloth', 'Nightweave', 'Moonveil'], assassinWeaponNames: ['Empty hands', 'Twin daggers', 'Moonfang'],
      priestDesc: 'A golden-haired healer in ivory and crimson robes. Mend and ward your party, then smite what is left standing with a mace and holy light.',
      priestHint: 'Click to move or attack · WASD to walk · Space to strike · 1–9 skills (Mend heals your most wounded ally) · E character · B bags · F talk · Esc for menu',
      maces: 'Mace', priestTip: 'Click the Priest to strike. Change robes and maces in the field with E.',
      priestLoading: 'Calling the Priest…', priestError: 'Priest sprites could not load. Select Priest again to retry.',
      priestArmorNames: ['Simple cloth', 'Pilgrim robes', 'Dawnweave'], priestWeaponNames: ['Empty hands', 'Oak mace', 'Sunbreaker'],
      hunterDesc: 'A ranger in a feathered headband with a bow and a quiver. Pick enemies off from far away, roll clear of trouble and rain arrows on whatever is left.',
      hunterHint: 'Click to move or attack · WASD to walk · Space to shoot · 1–9 skills · E character · B bags · F talk · Esc for menu',
      bows: 'Bows', hunterTip: 'Click the Hunter to loose an arrow. Change coats and bows in the field with E.',
      hunterLoading: 'Calling the Hunter…', hunterError: 'Hunter sprites could not load. Select Hunter again to retry.',
      hunterArmorNames: ['Simple cloth', 'Scout\u2019s Jerkin', 'Wildwarden Coat'], hunterWeaponNames: ['Empty hands', 'Hunter\u2019s Shortbow', 'Wildwarden Longbow'],
      areaName: 'Greenmeadow Field', gold: 'gold', slain: 'enemies', paused: 'Paused', resume: 'Resume',
      fieldHint: 'Click to move or attack · WASD to walk · Space to swing · Esc for menu',
      defeated: 'Defeated!', defeatedSub: 'You wake up back at the start…', lvl: 'Lv',
      name: 'Name', namePh: 'Your name', random: 'Random name',
      hairBeard: 'Hair & Beard', skin: 'Skin', armor: 'Armor', armorNames: ['Crimson', 'Azure', 'Verdant'], runes: 'Runes',
      tip: 'Tip: click the Warrior’s axe, mug, head, beard or fish!',
      health: 'Health', attack: 'Attack', defense: 'Defense', speed: 'Speed',
    },
    ko: {
      soundOn: '소리 켜짐 (M)', soundOff: '소리 꺼짐 (M)',
      back: '뒤로', toTitle: '타이틀로', newChar: '새 캐릭터',
      ccTitle: '워밴드를 결성하라!', forged: '전투로 단련되어!',
      warriorDesc: '검과 방패를 든 용감한 선봉장. 높은 체력과 강력한 근접 공격으로 최전선을 지킵니다.',
      warriorHint: '클릭: 이동·공격 · WASD: 걷기 · 스페이스: 베기 · E: 장비 · F: 대화 · 1–9: 스킬 · Esc: 메뉴',
      arms: '무기', warriorTip: '워리어를 눌러 검을 휘두르세요. 필드에서 E 키로 갑옷과 무기를 바꿀 수 있습니다.',
      warriorLoading: '워리어 소환 중…', warriorError: '워리어를 불러오지 못했습니다. 다시 선택해 주세요.',
      warriorArmorNames: ['기본 옷', '진홍 갑옷', '청람 갑옷'], warriorWeaponNames: ['맨손', '검과 방패', '왕실 검과 방패'],
      mageDesc: '강력한 원거리 주문을 사용하는 마법사. 로브와 지팡이를 바꾸면 외형과 능력이 달라집니다.',
      mageHint: '클릭: 이동·시전 · WASD: 걷기 · 스페이스: 시전 · E: 장비 · F: 대화 · 1–9: 스킬 · Esc: 메뉴',
      equipment: '장비 (E)', gender: '체형', male: '남성', female: '여성', hair: '머리', weapon: '지팡이', mageTip: '마법사를 눌러 주문을 시전하세요. 필드에서 E 키로 장비를 바꿀 수 있습니다.',
      mageLoading: '마법사 소환 중…', mageError: '마법사를 불러오지 못했습니다. 다시 선택해 주세요.',
      mageArmorNames: ['기본 옷', '견습 로브', '룬 로브'], mageWeaponNames: ['맨손', '나무 지팡이', '수정 지팡이'],
      assassinDesc: '쌍검과 치명타를 사용하는 민첩한 암살자. Shift 키로 위험을 뚫고 질주하세요.',
      assassinHint: '클릭: 이동·공격 · WASD: 걷기 · 스페이스: 베기 · Shift: 그림자 질주 · E: 장비 · F: 대화 · 1–9: 스킬 · Esc: 메뉴',
      blades: '쌍검', assassinTip: '암살자를 눌러 베기를 시전하세요. 필드에서 E 키로 장비를 바꿀 수 있습니다.',
      assassinLoading: '암살자 소환 중…', assassinError: '암살자를 불러오지 못했습니다. 다시 선택해 주세요.',
      assassinArmorNames: ['기본 옷', '밤의 의복', '달의 장막'], assassinWeaponNames: ['맨손', '쌍단검', '달송곳니'],
      priestDesc: '상아색과 진홍색 로브를 걸친 금발의 치유 사제. 파티를 치유하고 보호하며, 철퇴와 성스러운 빛으로 적을 응징합니다.',
      priestHint: '클릭: 이동·공격 · WASD: 걷기 · 스페이스: 타격 · E: 장비 · F: 대화 · 1–9: 스킬 (첫 스킬은 치유) · Esc: 메뉴',
      maces: '철퇴', priestTip: '사제를 눌러 철퇴를 휘두르세요. 필드에서 E 키로 장비를 바꿀 수 있습니다.',
      priestLoading: '사제 소환 중…', priestError: '사제를 불러오지 못했습니다. 다시 선택해 주세요.',
      priestArmorNames: ['기본 옷', '순례자의 로브', '새벽의 제복'], priestWeaponNames: ['맨손', '참나무 철퇴', '태양 파쇄자'],
      hunterDesc: '깃털 머리띠를 두른 활과 화살통의 사냥꾼. 멀리서 적을 쓰러뜨리고, 위험에서 굴러 벗어나며, 화살비를 퍼붓습니다.',
      hunterHint: '클릭: 이동·공격 · WASD: 걷기 · 스페이스: 사격 · E: 장비 · F: 대화 · 1–9: 스킬 · Esc: 메뉴',
      bows: '활', hunterTip: '사냥꾼을 눌러 화살을 쏘세요. 필드에서 E 키로 장비를 바꿀 수 있습니다.',
      hunterLoading: '사냥꾼 소환 중…', hunterError: '사냥꾼을 불러오지 못했습니다. 다시 선택해 주세요.',
      hunterArmorNames: ['기본 옷', '정찰병의 조끼', '와일드워든 코트'], hunterWeaponNames: ['맨손', '사냥꾼의 단궁', '와일드워든 장궁'],
      areaName: '푸른 초원', gold: '골드', slain: '적', paused: '일시정지', resume: '계속하기',
      fieldHint: '클릭: 이동·공격 · WASD: 걷기 · 스페이스: 휘두르기 · Esc: 메뉴',
      defeated: '쓰러졌다!', defeatedSub: '시작 지점에서 깨어납니다…', lvl: 'Lv',
      name: '이름', namePh: '이름 입력', random: '무작위 이름',
      hairBeard: '머리·수염', skin: '피부', armor: '갑옷', armorNames: ['진홍', '청람', '초록'], runes: '룬',
      tip: '팁: 워리어의 도끼, 맥주잔, 머리, 수염, 물고기를 눌러 보세요!',
      health: '체력', attack: '공격', defense: '방어', speed: '속도',
    },
  };
  const t = k => (T[save.lang] || T.en)[k];
  const applyI18n = () => {
    document.documentElement.lang = save.lang;
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  };

  // ---------- helpers ----------
  const $ = id => document.getElementById(id);
  const stage = $('stage');
  const scenes = { splash: $('scene-splash'), login: $('scene-login'), chars: $('scene-chars'), create: $('scene-create'), game: $('scene-game') };
  let scene = 'splash';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function show(name) {
    scene = name;
    stage.dataset.scene = name;
    for (const [k, el] of Object.entries(scenes)) el.hidden = k !== name;
    if (name === 'create') enterCreate(); else leaveCreate();
    if (name === 'game') enterGame(); else leaveGame();
    if (name === 'splash') $('start').focus({ preventScroll: true });
    if (name === 'login') Account.enter(); else if (name === 'chars') Account.enterChars();
    syncMusic();
  }

  // ---------- audio (synthesised, so there are no files to load) ----------
  let ac = null;
  function audio() {
    if (!ac) { const A = window.AudioContext || window.webkitAudioContext; if (A) ac = new A(); }
    if (ac && ac.state === 'suspended') ac.resume();
    return ac;
  }

  // Every effect plays through one gain node so the Settings slider can scale them together. The slider is
  // squared (a perceptual taper), so 100% is exactly the loudness the game always had.
  const taper = v => v * v;
  let sfxGain = null;
  function sfxOut(c) {
    if (!sfxGain || sfxGain.context !== c) { sfxGain = c.createGain(); sfxGain.connect(c.destination); }
    sfxGain.gain.value = taper(save.sfxVol);
    return sfxGain;
  }

  // ---------- background music (music.js) ----------
  // Browsers only let audio start after a tap or key press, so the score begins on the first one
  // (on the title screen that is the tap that awakens the horn) and then plays on every screen.
  let music = null, fmusic = null, cmusic = null, rmusic = null, gmusic = null, smusic = null, musicZone = 0;   // title/creation theme, meadow theme, Crags theme (zone 1), glacier theme (zone 2), fen theme (zone 3), city theme (zone 4)
  function ensureMusic() {
    const c = audio(); if (!c || !window.createMusic) return;
    if (!music) { music = window.createMusic(c); c.addEventListener('statechange', ensureMusic); }
    if (!fmusic && window.createFieldMusic) fmusic = window.createFieldMusic(c);
    if (!cmusic && window.createCragMusic) cmusic = window.createCragMusic(c);
    if (!rmusic && window.createRimeMusic) rmusic = window.createRimeMusic(c);
    if (!gmusic && window.createFenMusic) gmusic = window.createFenMusic(c);
    if (!smusic && window.createCityMusic) smusic = window.createCityMusic(c);
    syncMusic();
  }
  // the field has its own theme; the title and creation screens share the snowy one (one plays at a time, fading over)
  function syncMusic() {
    if (!ac || ac.state !== 'running') return;
    // In the game the zone picks the score: Greenmeadow and Alderhaven keep the folk tune, the Crags, the glacier and the fen get their own.
    const here = scene === 'game' ? (musicZone === 4 && smusic ? smusic : musicZone === 3 && gmusic ? gmusic : musicZone === 2 && rmusic ? rmusic : musicZone > 0 && cmusic ? cmusic : fmusic) : null;
    for (const m of [fmusic, cmusic, rmusic, gmusic, smusic]) if (m && m !== here && m.running) m.stop();
    if (scene === 'game') { if (music && music.running) music.stop(); if (here && !here.running) here.start(); }
    else if (music && !music.running) music.start();
    applyMusicLevel(3);
  }
  function applyMusicLevel(secs = 1.5) {
    if (music) music.setLevel(save.sound ? (scene === 'splash' ? 1 : .55) * taper(save.musicVol) : 0, secs);
    for (const m of [fmusic, cmusic, rmusic, gmusic, smusic]) if (m) m.setLevel(save.sound ? taper(save.musicVol) : 0, secs);
  }
  function unlockAudio() { const c = audio(); if (c) c.resume().then(ensureMusic).catch(() => {}); }
  ['pointerdown', 'keydown', 'touchstart'].forEach(ev => addEventListener(ev, unlockAudio, { capture: true }));
  document.addEventListener('visibilitychange', () => { if (!ac) return; if (document.hidden) ac.suspend(); else ac.resume(); });
  const toast = $('toast');
  let toastT = 0;
  function showToast(msg) { toast.textContent = msg; toast.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => toast.classList.remove('show'), 1600); }
  addEventListener('keydown', e => {                      // M = mute / unmute all sound
    if (e.key !== 'm' && e.key !== 'M') return;
    if (e.target && /^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
    save.sound = !save.sound; persist(); applyMusicLevel(.6); dispatchEvent(new Event('prefs-change')); showToast(save.sound ? t('soundOn') : t('soundOff'));
  });
  function blip(freq = 660, dur = .08, vol = .05) {
    if (!save.sound) return;
    const c = audio(); if (!c) return;
    const o = c.createOscillator(), g = c.createGain(), now = c.currentTime;
    o.type = 'triangle'; o.frequency.value = freq;
    g.gain.setValueAtTime(vol, now); g.gain.exponentialRampToValueAtTime(.0001, now + dur);
    o.connect(g).connect(sfxOut(c)); o.start(now); o.stop(now + dur + .02);
  }
  function horn() {
    if (!save.sound) return;
    const c = audio(); if (!c) return;
    if (music) music.duck(2.6);
    const now = c.currentTime, dur = 2.6;
    const out = c.createGain(); out.gain.value = .0001;
    out.gain.exponentialRampToValueAtTime(.35, now + .35);
    out.gain.setValueAtTime(.35, now + 1.6);
    out.gain.exponentialRampToValueAtTime(.0001, now + dur);
    const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 3;
    lp.frequency.setValueAtTime(300, now); lp.frequency.exponentialRampToValueAtTime(1400, now + .9);
    lp.frequency.exponentialRampToValueAtTime(500, now + dur);
    const vib = c.createOscillator(), vg = c.createGain(); vib.frequency.value = 5.5; vg.gain.value = 3;
    vib.connect(vg);
    // a fifth apart, like a real war horn
    for (const [f, type, v] of [[98, 'sawtooth', .6], [147, 'sawtooth', .35], [196, 'square', .15]]) {
      const o = c.createOscillator(), g = c.createGain();
      o.type = type; o.frequency.setValueAtTime(f * .94, now); o.frequency.exponentialRampToValueAtTime(f, now + .3);
      vg.connect(o.frequency); g.gain.value = v;
      o.connect(g).connect(lp); o.start(now); o.stop(now + dur + .1);
    }
    vib.start(now); vib.stop(now + dur + .1);
    // cheap echo off the mountains
    const d = c.createDelay(1); d.delayTime.value = .32;
    const fb = c.createGain(); fb.gain.value = .35;
    lp.connect(out); lp.connect(d); d.connect(fb).connect(d); d.connect(out);
    out.connect(sfxOut(c));
  }

  function el(tag, props = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v; else n.setAttribute(k, v);
    }
    n.append(...kids);
    return n;
  }

  // ---------- voices and effects (synthesised) ----------
  function voice(f0, dur = .85, vol = .5, breath = true) {
    if (!save.sound) return;
    const c = audio(); if (!c) return;
    const now = c.currentTime, o = c.createOscillator(), g = c.createGain();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(f0, now); o.frequency.linearRampToValueAtTime(f0 * 1.5, now + dur * .14); o.frequency.exponentialRampToValueAtTime(f0 * .85, now + dur);
    g.gain.setValueAtTime(.0001, now); g.gain.exponentialRampToValueAtTime(vol, now + Math.min(.05, dur * .2)); g.gain.exponentialRampToValueAtTime(.0001, now + dur);
    for (const fr of [700, 1150, 2600]) { const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = fr; bp.Q.value = 5; o.connect(bp); bp.connect(g); }
    g.connect(sfxOut(c)); o.start(now); o.stop(now + dur + .05);
    if (!breath) return;
    const buf = c.createBuffer(1, Math.floor(c.sampleRate * .3), c.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
    const n = c.createBufferSource(), hp = c.createBiquadFilter(), ng = c.createGain();
    n.buffer = buf; hp.type = 'highpass'; hp.frequency.value = 1500; ng.gain.value = .18 * vol;
    n.connect(hp).connect(ng).connect(sfxOut(c)); n.start(now);
  }
  const shout = () => voice(140, .85, .55);
  const grunt = () => voice(105, .3, .4, false);
  const laughSound = () => { for (let i = 0; i < 5; i++) setTimeout(() => voice(150 + (i % 2) * 30, .17, .34, false), i * 180); };
  function tone(freqs, dur, vol, type = 'sine') {
    if (!save.sound) return;
    const c = audio(); if (!c) return;
    const now = c.currentTime;
    for (const fr of freqs) {
      const o = c.createOscillator(), g = c.createGain();
      o.type = type; o.frequency.value = fr;
      g.gain.setValueAtTime(vol, now); g.gain.exponentialRampToValueAtTime(.0001, now + dur);
      o.connect(g).connect(sfxOut(c)); o.start(now); o.stop(now + dur + .05);
    }
  }
  const clang = () => tone([520, 1310, 2210, 3080], 1.1, .12);
  const clink = () => tone([1760, 2637, 3520], .35, .1);

  // ---------- character creation ----------
  const OPT = window.WARRIOR_OPTS;
  const modular = c => ['warrior', 'mage', 'assassin', 'priest', 'hunter'].includes(c?.class);
  const spriteClass = c => (c?.class === 'warrior' ? WarriorSprite : c?.class === 'assassin' ? AssassinSprite : c?.class === 'priest' ? PriestSprite : c?.class === 'hunter' ? HunterSprite : MageSprite).variant(c);
  const equipmentKeys = c => [c.class + 'Armor', c.class + 'Weapon'];
  const NAMES = ['Bjorn', 'Ragna', 'Thora', 'Ulfar', 'Freya', 'Gunnar', 'Sunwoo', 'Haneul', 'Minjae', 'Dolgi', 'Eirik', 'Seoyun', 'Astrid', 'Jihoon'];
  const randName = () => NAMES[Math.floor(Math.random() * NAMES.length)];
  const defaultCfg = () => ({ name: randName(), class: 'warrior', gender: 'male', hairColor: 0, skin: 0, armor: 0, rune: 0, warriorArmor: 'crimson', warriorWeapon: 'sword', mageArmor: 'apprentice', mageWeapon: 'ash', assassinArmor: 'shadow', assassinWeapon: 'daggers', priestArmor: 'pilgrim', priestWeapon: 'mace', hunterArmor: 'scout', hunterWeapon: 'shortbow' });
  const idx = (v, n) => { v = Math.floor(+v); return v >= 0 && v < n ? v : 0; };
  let cfg = defaultCfg();
  const load = c => {
    cfg = Object.assign(defaultCfg(), c || {});
    cfg.name = String(cfg.name || '').slice(0, 16);
    cfg.hairColor = idx(cfg.hairColor, OPT.hairColors.length); cfg.skin = idx(cfg.skin, OPT.skinColors.length);
    cfg.armor = idx(cfg.armor, OPT.armors); cfg.rune = idx(cfg.rune, OPT.runeHues.length);
    cfg.class = ['mage', 'assassin', 'priest', 'hunter'].includes(cfg.class) ? cfg.class : 'warrior';
    cfg.gender = cfg.gender === 'female' ? 'female' : 'male';
    if (modular(cfg)) { cfg.hairColor = idx(cfg.hairColor, spriteClass(cfg).HAIR.length); cfg.skin = idx(cfg.skin, spriteClass(cfg).SKIN.length); }
    const warriorGear = WarriorSprite.equipment(cfg); cfg.warriorArmor = warriorGear.armor; cfg.warriorWeapon = warriorGear.weapon;
    const gear = MageSprite.equipment(cfg); cfg.mageArmor = gear.armor; cfg.mageWeapon = gear.weapon;
    const assassinGear = AssassinSprite.equipment(cfg); cfg.assassinArmor = assassinGear.armor; cfg.assassinWeapon = assassinGear.weapon;
    const priestGear = PriestSprite.equipment(cfg); cfg.priestArmor = priestGear.armor; cfg.priestWeapon = priestGear.weapon;
    const hunterGear = HunterSprite.equipment(cfg); cfg.hunterArmor = hunterGear.armor; cfg.hunterWeapon = hunterGear.weapon;
  };
  load(save.draft);
  if (save.char) { const draft = cfg; load(save.char); save.char = { ...cfg }; cfg = draft; persist(); }
  const saveDraft = () => { save.draft = { ...cfg }; persist(); };

  // the Warrior: WebGL-animated painting (warriorview.js); falls back to the still image without WebGL
  const wcv = $('wcv');
  const view = new window.WarriorView(wcv, name => onWarrior(name));
  view.reduced = reduced;
  window.valhalla = { view, get music() { return music; }, get fmusic() { return fmusic; }, get cmusic() { return cmusic; }, get rmusic() { return rmusic; }, get gmusic() { return gmusic; }, get smusic() { return smusic; }, get ctx() { return ac; } };   // debug handle (also used by the tests)
  if (view.ok) {
    view.load('assets/warrior.webp', 'assets/warrior_mask.png').then(() => { view.bind(); view.set(cfg); if (scene === 'create' && !modular(cfg)) view.setActive(true); }).catch(() => fallbackWarrior());
  } else fallbackWarrior();
  function fallbackWarrior() {
    view.ok = false;
    const img = el('img', { class: 'wfallback', src: 'assets/warrior.webp', alt: 'Warrior' });
    wcv.replaceWith(img);
    img.hidden = modular(cfg);
  }

  // One sprite per class and body type: spriteViews.mage is the male Mage, spriteViews.mageF the female one.
  const spriteViews = { warrior: null, mage: null, assassin: null, priest: null, hunter: null, warriorF: null, mageF: null, assassinF: null, priestF: null, hunterF: null }, spritePromises = {};
  let mageRaf = 0, castStart = -10;
  const viewKey = c => c.class + (c.gender === 'female' ? 'F' : '');
  const currentSprite = c => spriteViews[viewKey(c)];
  const magecv = $('magecv'); magecv.width = 300; magecv.height = 394;
  async function ensureMage(type = cfg.class, gender = cfg.gender) {
    const key = viewKey({ class: type, gender }), here = () => viewKey(cfg) === key, playing = () => scene === 'game' && !!save.char && viewKey(save.char) === key;
    if (spriteViews[key]) return spriteViews[key];
    if (spritePromises[key]) return spritePromises[key];
    const look = playing() ? save.char : cfg;
    $('mage-status').textContent = t(type + 'Loading'); $('mage-status').hidden = !here();
    spritePromises[key] = spriteClass({ class: type, gender }).load(look).then(sprite => {
      spriteViews[key] = sprite;
      if (here()) { sprite.set(playing() ? save.char : cfg); $('mage-status').hidden = true; }
      if (scene === 'create' && here()) { $('go').disabled = false; paintMage(performance.now()); }
      return sprite;
    }).catch(error => {
      if (here()) { $('mage-status').textContent = t(type + 'Error'); $('mage-status').hidden = false; }
      throw error;
    }).finally(() => { spritePromises[key] = null; });
    return spritePromises[key];
  }
  function paintMage(now) {
    const mage = currentSprite(cfg);
    if (!mage) return;
    const g = magecv.getContext('2d'); g.clearRect(0, 0, magecv.width, magecv.height);
    g.save(); g.translate(150, 346);
    // A small rune platform grounds the sprite at the same foot anchor.
    g.strokeStyle = '#8acfff'; g.lineWidth = 2; g.globalAlpha = .65;
    g.beginPath(); g.ellipse(0, 0, 88, 25, 0, 0, Math.PI * 2); g.stroke(); g.globalAlpha = 1;
    const age = (now - castStart) / 1000;
    const h = { fx: 1, fy: 1, atkT: age >= 0 && age < mage.meta.attack.duration ? age : 0, walk: 0 };
    mage.draw(g, h, reduced ? 0 : now / 1000, 2.7);
    if (cfg.class === 'mage' && h.atkT > .24 && h.atkT < .5) {
      g.fillStyle = '#e6f8ff'; g.shadowColor = '#59d9ff'; g.shadowBlur = 15;
      g.beginPath(); g.arc(49, -180, 6 * (1 - (h.atkT - .24) / .26), 0, Math.PI * 2); g.fill();
    }
    g.restore();
  }
  function animateMage(now) {
    if (scene !== 'create' || !modular(cfg) || reduced) return;
    paintMage(now); mageRaf = requestAnimationFrame(animateMage);
  }
  function castPreview() { castStart = performance.now(); if (cfg.class !== 'mage') noiseBurst(.14, 1400, 2800, .08); else tone([587, 880, 1175], .4, .035); paintMage(castStart + (reduced ? 200 : 0)); }
  magecv.addEventListener('click', castPreview);
  Object.defineProperty(window.valhalla, 'warrior', { get: () => spriteViews.warrior });
  Object.defineProperty(window.valhalla, 'mage', { get: () => spriteViews.mage });
  Object.defineProperty(window.valhalla, 'assassin', { get: () => spriteViews.assassin });
  Object.defineProperty(window.valhalla, 'priest', { get: () => spriteViews.priest });
  Object.defineProperty(window.valhalla, 'hunter', { get: () => spriteViews.hunter });
  Object.defineProperty(window.valhalla, 'sprites', { get: () => spriteViews });

  function onWarrior(name) {
    switch (name) {
      case 'attack:start': blip(300, .2, .08); break;
      case 'attack:shout': shout(); break;
      case 'attack:strike': clang(); burstSparks(70, 'blade', '#ffc857', 1.5); slashT = performance.now() / 1000; stage.classList.add('shake'); setTimeout(() => stage.classList.remove('shake'), 520); break;
      case 'cheers:clink': clink(); burstSparks(26, 'mug', '#fff6d6', .45); break;
      case 'cheers:laugh': case 'laugh:laugh': laughSound(); break;
      case 'beard:hmm': voice(90, .4, .35, false); break;
      case 'fish:splash': blip(900, .08, .06); burstSparks(14, 'fish', '#bfe8ff', .5); break;
      case 'flex:grunt': grunt(); break;
    }
  }

  // controls
  const custom = $('custom');
  const row = (label, ...kids) => el('div', { class: 'row' }, el('span', { class: 'lab', text: label }), el('div', { class: 'ctl' }, ...kids));
  const opt = (k, v, cls, label, color) => {
    const b = el('button', { class: cls, type: 'button', 'data-k': k, 'data-v': String(v), 'aria-label': label, 'aria-pressed': 'false' });
    if (color) b.style.setProperty('--c', color);
    return b;
  };
  function gearSelect(key, selected, change, inField = false) {
    const armor = key.endsWith('Armor'), type = ['warrior', 'assassin', 'priest', 'hunter'].find(c => key.startsWith(c)) || 'mage';
    const C = spriteClass({ class: type }), values = Object.keys(armor ? C.ARMOR : C.WEAPON);
    const names = t(type + (armor ? 'ArmorNames' : 'WeaponNames'));
    const label = t(armor ? 'armor' : { warrior: 'arms', assassin: 'blades', priest: 'maces', hunter: 'bows' }[type] || 'weapon');
    const select = el('select', { class: 'gear-pick', 'aria-label': label, id: (inField ? 'field-' : 'create-') + key });
    values.forEach((v, i) => {
      const item = WORLD_ITEMS.find(item => item.class === type && item.kind === (armor ? 'armor' : 'weapon') && item.variant === v);
      if (inField ? v === 'none' || Inventory.quantity(item?.id) > 0 : item?.starter) select.append(el('option', { value: v, text: names[i] }));
    });
    if (![...select.options].some(o => o.value === selected)) { selected = [...select.options].find(o => o.value !== 'none')?.value || 'none'; change(selected); }
    select.value = selected; select.addEventListener('change', () => change(select.value));
    return row(label, select);
  }
  function buildControls() {
    custom.replaceChildren();
    const input = el('input', { class: 'field', id: 'name', type: 'text', maxlength: '16', autocomplete: 'off', placeholder: t('namePh'), 'aria-label': t('name') });
    input.value = cfg.name;
    input.addEventListener('input', () => { cfg.name = input.value; saveDraft(); input.classList.remove('bad'); });
    const dice = el('button', { class: 'arrow', type: 'button', 'aria-label': t('random'), text: '↻' });
    dice.addEventListener('click', () => { cfg.name = randName(); input.value = cfg.name; saveDraft(); blip(700); });
    custom.append(row(t('name'), input, dice));
    if (modular(cfg)) {      // every class comes in a male and a female body; the choice is part of the look, fixed once the character is made
      const seg = el('div', { class: 'seg', role: 'group', 'aria-label': t('gender') });
      for (const g of ['male', 'female']) {
        const b = el('button', { class: 'segb', type: 'button', id: 'gender-' + g, 'data-gender': g, 'aria-pressed': String(cfg.gender === g), text: t(g) });
        b.addEventListener('click', () => { if (cfg.gender === g) return; cfg.gender = g; buildControls(); refresh(); updateClass(); castPreview(); blip(760); });
        seg.append(b);
      }
      custom.append(row(t('gender'), seg));
    }
    const sw = (k, list, labelKey) => { const d = el('div', { class: 'swatches' }); list.forEach((c, i) => d.append(opt(k, i, 'sw', `${t(labelKey)} ${i + 1}`, c))); return d; };
    const isModular = modular(cfg), C = spriteClass(cfg);
    custom.append(row(t(isModular ? 'hair' : 'hairBeard'), sw('hairColor', isModular ? C.HAIR : OPT.hairSwatch, isModular ? 'hair' : 'hairBeard')));
    custom.append(row(t('skin'), sw('skin', isModular ? C.SKIN : OPT.skinSwatch, 'skin')));
    if (isModular) {
      for (const key of equipmentKeys(cfg)) custom.append(gearSelect(key, cfg[key], value => { cfg[key] = value; refresh(); blip(760); }));
      custom.append(el('p', { class: 'tip', text: t(cfg.class + 'Tip') })); return;
    }
    const tiles = el('div', { class: 'tiles' });
    for (let i = 0; i < OPT.armors; i++) { const b = opt('armor', i, 'tile', t('armorNames')[i]); b.append(el('i', { class: 'ti ti' + i }), el('span', { text: t('armorNames')[i] })); tiles.append(b); }
    custom.append(row(t('armor'), tiles));
    custom.append(row(t('runes'), sw('rune', OPT.runeSwatch, 'runes')));
    custom.append(el('p', { class: 'tip', text: t('tip') }));
  }
  custom.addEventListener('click', onPick);
  function onPick(e) {
    const b = e.target.closest('button[data-k]'); if (!b) return;
    cfg[b.dataset.k] = +b.dataset.v;
    refresh(); blip(760);
  }
  function refresh() {
    custom.querySelectorAll('button[data-k]').forEach(b => b.setAttribute('aria-pressed', String(String(cfg[b.dataset.k]) === b.dataset.v)));
    view.set(cfg); const sprite = currentSprite(cfg); if (sprite) { sprite.set(cfg); paintMage(performance.now()); } saveDraft();
  }
  function updateClass() {
    const isModular = modular(cfg), name = cfg.class[0].toUpperCase() + cfg.class.slice(1);
    $('class-name').textContent = { warrior: 'WARRIOR (워리어)', mage: 'MAGE (마법사)', assassin: 'ASSASSIN (암살자)', priest: 'PRIEST (사제)', hunter: 'HUNTER (사냥꾼)' }[cfg.class];
    $('class-desc').dataset.i18n = cfg.class + 'Desc'; $('class-desc').textContent = t($('class-desc').dataset.i18n);
    $('custom-title').textContent = `[Customize ${name}]`; $('custom-panel').setAttribute('aria-label', 'Customize ' + name);
    for (const name of ['warrior', 'mage', 'assassin', 'priest', 'hunter']) { const b = $('cls-' + name); b.classList.toggle('on', name === cfg.class); b.setAttribute('aria-pressed', String(name === cfg.class)); }
    document.querySelector('#wcv, .wfallback').hidden = isModular; magecv.hidden = !isModular; $('mage-status').hidden = !isModular || !!currentSprite(cfg);
    magecv.setAttribute('aria-label', cfg.class === 'warrior' ? 'Warrior preview. Click to swing the sword.' : cfg.class === 'assassin' ? 'Assassin preview. Click to slash.' : cfg.class === 'priest' ? 'Priest preview. Click to strike with the mace.' : cfg.class === 'hunter' ? 'Hunter preview. Click to shoot an arrow.' : 'Mage preview. Click to cast a spell.');
    cancelAnimationFrame(mageRaf);
    if (view.ok) view.setActive(scene === 'create' && !isModular);
    $('go').disabled = isModular && !currentSprite(cfg);
    if (isModular) { ensureMage(cfg.class, cfg.gender).catch(() => {}); if (scene === 'create') animateMage(performance.now()); }
    const values = cfg.class === 'assassin' ? [68, 80, 38, 95] : cfg.class === 'priest' ? [75, 55, 50, 70] : cfg.class === 'hunter' ? [70, 85, 40, 85] : cfg.class === 'mage' ? [60, 90, 35, 55] : [92, 88, 60, 34];
    $('stats').replaceChildren(...['health', 'attack', 'defense', 'speed'].flatMap((k, j) => [
      el('dt', { text: t(k) }), (() => { const d = el('dd'), i = el('i'); i.style.setProperty('--v', values[j] + '%'); d.append(i); return d; })()]));
  }

  let introTimer = 0;
  function enterCreate() {
    if (save.char && !save.draft) load(save.char);
    buildControls(); refresh(); updateClass();
    if (view.ok && !modular(cfg)) view.resize();
    clearTimeout(introTimer); introTimer = setTimeout(() => { if (modular(cfg)) castPreview(); else if (view.ok) view.play('attack'); }, 450);
    $('cls-' + cfg.class).focus({ preventScroll: true });
  }
  function leaveCreate() { clearTimeout(introTimer); cancelAnimationFrame(mageRaf); if (view.ok) view.setActive(false); }
  for (const name of ['warrior', 'mage', 'assassin', 'priest', 'hunter']) $('cls-' + name).addEventListener('click', () => {
    if (cfg.class !== name) { cfg.class = name; if (modular(cfg)) cfg.skin = idx(cfg.skin, spriteClass(cfg).SKIN.length); buildControls(); refresh(); }
    updateClass(); if (modular(cfg)) castPreview(); else if (view.ok) view.play('attack');
  });
  $('back').addEventListener('click', () => { blip(520); show('splash'); });
  $('go').addEventListener('click', () => {
    const nm = $('name'); const name = nm.value.trim();
    if (name.length < 2) { nm.classList.add('bad'); nm.focus(); blip(200, .15, .08); return; }
    cfg.name = name.slice(0, 16);
    Online.newCharacter(); save.char = { ...cfg }; save.draft = null; persist();
    clang(); horn(); show('game');
  });

  // ---------- the field: first map (field.js) ----------
  const hud = { lv: $('hud-lv'), hp: $('hp-fill'), hpT: $('hp-text'), xp: $('xp-fill'), gold: $('hud-gold'), kills: $('hud-kills') };
  function onHud(s) {
    hud.hp.style.width = (s.hp / s.maxHp * 100).toFixed(1) + '%'; hud.hpT.textContent = `${Math.ceil(s.hp)} / ${s.maxHp}`;
    hud.xp.style.width = (s.xp / s.xpNeed * 100).toFixed(1) + '%'; hud.lv.textContent = ` ${t('lvl')} ${s.level}`; window.Quests?.setLevel(s.level);
    hud.gold.textContent = s.gold; hud.kills.textContent = s.kills; $('bag-gold').textContent = `${s.gold} gold`;
    const inCity = !!s.hub || s.area === 'Alderhaven', title = $('area-title'), away = s.zone > 0;
    if (title.dataset.area !== s.area) { title.dataset.area = s.area; title.classList.remove('show'); void title.offsetWidth; title.classList.add('show'); }
    title.querySelector('b').textContent = away ? s.area : inCity ? 'Alderhaven · Fountain Square' : t('areaName');
    title.querySelector('span').textContent = away ? (s.hub ? `${s.hub} · Sanctuary · quests · supplies` : s.levels ? `Recommended levels ${s.levels[0]}–${s.levels[1]} · stay close to the gate` : (s.tagline || 'Unexplored lands')) : inCity ? 'Sanctuary · shops · townspeople' : '푸른 초원';
    renderBuffs(s.buffs || []);
    if ((s.zone || 0) !== musicZone) { musicZone = s.zone || 0; syncMusic(); }
    $('city-travel').hidden = inCity;
    $('city-travel').textContent = s.traveling ? (away ? `Walking to ${(s.camp || 'camp').split(' ')[0]}…` : 'Walking to Alderhaven…') : (away ? `Visit ${s.camp || 'the camp'} ↓` : 'Visit Alderhaven ↓');
  }
  // ---------- level-up banner, flash and active effects ----------
  const luBanner = $('levelup-banner'), luFlash = $('levelup-flash'), buffBar = $('buff-bar');
  let luTimer = 0;
  function restart(node, cls) { node.classList.remove(cls); void node.offsetWidth; node.classList.add(cls); }
  function levelBanner(ev) {
    if (!ev?.level) return;
    const learned = (ev.unlocked || []).map(id => WORLD_SKILLS.find(k => k.id === id)).filter(Boolean);
    $('lu-level').textContent = `Level ${ev.level}`;
    $('lu-skills').replaceChildren(...learned.map(k => {
      const row = el('div', { class: 'lu-skill' }), glyph = el('span', { class: 'skill-icon' }); glyph.innerHTML = Skillbar.icon(k.icon);
      row.append(glyph, el('b', { text: `New skill: ${k.name}` }), el('small', { text: k.description })); return row;
    }));
    $('lu-hint').textContent = learned.length ? 'Press K to arrange your skills' : 'Fully healed · spend stat points in Character (E)';
    luBanner.hidden = false; restart(luBanner, 'show'); restart(luFlash, 'show');
    restart($('hud-lv'), 'lv-pop'); restart(document.querySelector('.bar.xp'), 'xp-flash');
    const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
    clearTimeout(luTimer); luTimer = setTimeout(() => { luBanner.hidden = true; luBanner.classList.remove('show'); luFlash.classList.remove('show'); }, calm ? 3200 : 5200);
  }
  function renderBuffs(list) {
    const key = list.map(b => b.id).join();
    if (buffBar.dataset.key !== key) {
      buffBar.dataset.key = key;
      buffBar.replaceChildren(...list.map(b => {
        const food = WORLD_ITEMS.find(k => k.id === b.id), def = WORLD_SKILLS.find(k => k.id === b.id) || (food && { name: food.name, icon: 'food', description: `Restores ${food.heal} HP over ${food.duration} s.` });
        const chip = el('span', { class: 'buff-chip', 'data-buff': b.id, 'data-kind': b.kind, title: `${def?.name || b.id}: ${def?.description || ''}` }), glyph = el('span', { class: 'skill-icon' });
        glyph.innerHTML = Skillbar.icon(def?.icon || 'attack'); chip.append(glyph, el('i')); return chip;
      }));
    }
    for (const chip of buffBar.children) { const b = list.find(x => x.id === chip.dataset.buff); if (b) { chip.querySelector('i').textContent = Math.ceil(b.left); chip.style.setProperty('--left', Math.max(0, Math.min(1, b.left / b.time))); } }
  }
  function noiseBurst(dur, f0, f1, vol, q = 1.2, type = 'bandpass') {
    if (!save.sound) return;
    const c = audio(); if (!c) return;
    const now = c.currentTime, len = Math.floor(c.sampleRate * dur), buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
    const s = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    s.buffer = buf; f.type = type; f.Q.value = q; f.frequency.setValueAtTime(f0, now); f.frequency.exponentialRampToValueAtTime(f1, now + dur);
    g.gain.setValueAtTime(vol, now); g.gain.exponentialRampToValueAtTime(.0001, now + dur);
    s.connect(f); f.connect(g); g.connect(sfxOut(c)); s.start(now);
  }
  function sweep(f0, f1, dur, vol, type = 'sine') {
    if (!save.sound) return;
    const c = audio(); if (!c) return;
    const now = c.currentTime, o = c.createOscillator(), g = c.createGain();
    o.type = type; o.frequency.setValueAtTime(f0, now); o.frequency.exponentialRampToValueAtTime(f1, now + dur);
    g.gain.setValueAtTime(vol, now); g.gain.exponentialRampToValueAtTime(.0001, now + dur);
    o.connect(g).connect(sfxOut(c)); o.start(now); o.stop(now + dur + .02);
  }
  const SFX = {
    shadowstep: () => noiseBurst(.16, 900, 3200, .065),
    cast: () => { sweep(330, 990, .25, .065, 'triangle'); tone([1175], .2, .025); },
    swing: () => noiseBurst(.2, 500, 2400, .14, 1.4),
    hit: () => { sweep(190, 70, .13, .22); noiseBurst(.07, 1800, 900, .08); sweep(420, 180, .16, .08, 'triangle'); },
    crit: () => { SFX.hit(); tone([1320, 1980], .3, .07); },
    slimeDie: () => { sweep(520, 140, .22, .16, 'triangle'); noiseBurst(.16, 1400, 300, .1); },
    hurt: () => voice(115, .32, .32, false),
    pickup: () => tone([1568], .12, .05),
    // A potion is a quick gulp that rises; a meal is two soft low notes.
    consume: ev => { if (ev?.value > 0) { sweep(240, 620, .16, .08, 'triangle'); tone([1175, 1568], .25, .04); } else { tone([330, 440], .18, .05, 'triangle'); } },
    // A rising whoosh, a run up the scale, then a full major chord with sparkles on top.
    levelup: () => {
      sweep(180, 1900, .7, .09, 'sawtooth'); noiseBurst(.8, 300, 7000, .09, .8);
      [523, 659, 784, 1047, 1319, 1568, 2093].forEach((f, i) => setTimeout(() => tone([f, f * 2], .55, .06, 'triangle'), 120 + i * 85));
      setTimeout(() => { tone([523, 659, 784, 1047, 1319], 2, .05, 'triangle'); tone([262, 392], 2, .06, 'sine'); }, 780);
      for (let i = 0; i < 9; i++) setTimeout(() => tone([2093 + Math.random() * 2093], .3, .025), 900 + i * 110 + Math.random() * 60);
    },
    skill: ev => {
      const def = WORLD_SKILLS.find(k => k.id === ev?.skill), kind = def?.effect.effect;
      if (kind === 'nova') { sweep(220, 55, .45, .26, 'sawtooth'); noiseBurst(.4, 1200, 200, .18); }
      else if (kind === 'cone' || kind === 'strike') { noiseBurst(.22, 700, 3200, .16, 1.4); sweep(900, 300, .15, .06, 'triangle'); }
      else if (kind === 'volley') SFX.cast();
      else if (kind === 'dash') { noiseBurst(.25, 300, 3600, .15, 1); if (def.effect.mult === 0) sweep(1400, 200, .2, .08); }
      else if (kind === 'chain') { noiseBurst(.35, 3000, 6000, .16, 3); sweep(1800, 400, .3, .05, 'square'); }
      else if (kind === 'meteor') { sweep(1400, 180, .38, .1, 'sawtooth'); setTimeout(() => { sweep(160, 40, .6, .35); noiseBurst(.5, 900, 120, .25); }, 380); }
      else if (kind === 'buff') tone([523, 784, 1047], .6, .05, 'triangle');
      else if (kind === 'heal' || kind === 'mend') { tone([659, 880, 1319], .8, .05, 'sine'); tone([1760, 2637], .5, .03); }
    },
    healed: () => { tone([880, 1319, 1760], .5, .04, 'sine'); },
    death: () => voice(78, .95, .38),
    respawn: () => tone([392, 587], .5, .06),
    portal: () => { sweep(180, 720, .5, .09, 'sine'); tone([523, 784, 1047], .5, .05); },
  };
  function onField(name, data) {
    if (SFX[name]) SFX[name](data);
    if (name === 'levelup') levelBanner(data);
    if (name === 'spriteError') showToast(t((save.char?.class || 'mage') + 'Error'));
    if (name === 'death') $('dead-msg').hidden = false;
    if (name === 'respawn') $('dead-msg').hidden = true;
  }
  function enterGame() {
    const c = save.char || cfg, p = $('hud-portrait');
    if (modular(c)) {
      p.style.backgroundImage = ''; p.style.backgroundSize = 'cover'; p.style.backgroundPosition = 'center';
      ensureMage(c.class, c.gender).then(sprite => { if (scene === 'game' && save.char && viewKey(save.char) === viewKey(c)) { sprite.set(save.char); p.style.backgroundImage = `url(${sprite.portrait()})`; } }).catch(() => showToast(t(c.class + 'Error')));
    } else if (view.ok && view.loaded) {
      view.set(c); p.style.backgroundImage = `url(${view.snapshot()})`; p.style.backgroundSize = '200% auto'; p.style.backgroundPosition = '57% 26%';
    } else { p.style.backgroundImage = 'url(assets/warrior.webp)'; p.style.backgroundSize = '250% auto'; p.style.backgroundPosition = '57% 8%'; }
    $('hud-name').textContent = c.name; $('pause').hidden = true; $('equipment').hidden = true; $('dead-msg').hidden = true;
    $('p-equipment').hidden = !modular(c);
    document.querySelector('.hud-hint').textContent = t(modular(c) ? c.class + 'Hint' : 'fieldHint');
    Field.start({ canvas: $('fieldcv'), mini: $('minimap'), char: c, opts: OPT, onHud, onEvent: onField,
      onCharacter: look => {
        save.char = { ...look }; persist(); $('hud-name').textContent = look.name;
        const sprite = currentSprite(look);
        if (sprite) { sprite.set(look); p.style.backgroundImage = `url(${sprite.portrait()})`; }
        if (!$('equipment').hidden) renderEquipment();
      },
      slimeSprites: { png: 'assets/slimes_%k.png', json: 'assets/slimes.txt' } });
    window.Settings?.refresh();
    const at = $('area-title'); at.classList.remove('show'); void at.offsetWidth; at.classList.add('show');
  }
  function leaveGame() { window.Settings?.close(false); if (window.Field) Field.stop(); }
  let equipmentFocus = null;
  function setPause(on) { window.Settings?.close(false); window.Skillbar?.close(false); window.Quests?.close(false); City.close(false); Inventory.hideTooltip(); const wasEquipment = !$('equipment').hidden; $('equipment').hidden = true; $('pause').hidden = !on; Field.setPaused(on); if (on) $('p-resume').focus({ preventScroll: true }); else if (wasEquipment && equipmentFocus?.isConnected && !equipmentFocus.closest('[hidden]')) equipmentFocus.focus({ preventScroll: true }); }
  function renderEquipment() {
    const c = save.char, mage = c && currentSprite(c); if (!c || !mage) return;
    mage.set(c); const canvas = $('equipmentcv'); canvas.width = 320; canvas.height = 420;
    const g = canvas.getContext('2d'); g.translate(160, 365); mage.draw(g, { fx: 1, fy: 1, walk: 0 }, 0, 2.8);
    const stats = Field.equipmentStats;
    $('character-subtitle').textContent = `${c.name} · Level ${Field.hero.level} ${c.class[0].toUpperCase() + c.class.slice(1)}`;
    $('equipment-stats').textContent = `${t('attack')}: ${Number(stats.attack.toFixed(1))} · ${t('defense')}: ${Number(stats.defense.toFixed(1))}`;
    window.Attributes?.render();
    $('hud-portrait').style.backgroundImage = `url(${mage.portrait()})`;
    Inventory.render(document.getElementById('inventory-list'));
    Inventory.renderEquipped(document.getElementById('equipped-slots'));
  }
  function openEquipment(view = 'both') {
    window.Skillbar?.close(false);
    window.Quests?.close(false);
    City.close(false);
    if (scene !== 'game' || !Online.connected || Field.hero.dead || !modular(save.char)) return;
    if ($('equipment').hidden) equipmentFocus = document.activeElement;
    const workspace = document.querySelector('.equipment-workspace');
    workspace.dataset.view = view; workspace.setAttribute('aria-labelledby', view === 'bags' ? 'bag-title' : 'equipment-title');
    $('pause').hidden = true; $('equipment').hidden = false; Field.setPaused(true);
    $('equipmentcv').setAttribute('aria-label', 'Equipped ' + save.char.class);
    Inventory.renderEquipped($('equipped-slots'));
    ensureMage(save.char.class, save.char.gender).then(renderEquipment).catch(() => showToast(t(save.char.class + 'Error')));
    if (view === 'bags') $('bag-sort').focus({ preventScroll: true });
    else $('field-' + save.char.class + 'Armor')?.focus({ preventScroll: true });
  }
  addEventListener('keydown', e => {
    if (scene !== 'game' || e.defaultPrevented || e.repeat) return;
    const key = e.key.toLowerCase(), gearKey = key === 'e' || key === 'i' || key === 'b';
    const closesEquipment = !$('equipment').hidden && gearKey && e.target?.tagName === 'SELECT';
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target?.tagName || '') && key !== 'escape' && !closesEquipment) return;
    if (window.Skillbar?.open || window.Settings?.active) return;
    if (window.Quests?.open) {
      if (gearKey || key === 'k') { e.preventDefault(); Quests.close(false); if (gearKey) openEquipment(key === 'e' ? 'both' : 'bags'); else Skillbar.show(); }
      else if (key === 'escape' || key === 'q') { e.preventDefault(); Quests.close(); }
      return;
    }
    if (key === 'q') { e.preventDefault(); window.Quests?.show(); return; }
    if (City.open && key === 'escape') { e.preventDefault(); City.close(); return; }
    if (key === 'escape') { e.preventDefault(); if (!$('equipment').hidden) setPause(false); else setPause($('pause').hidden); }
    if (gearKey) {
      e.preventDefault();
      const view = key === 'e' ? 'both' : 'bags';
      if ($('equipment').hidden) openEquipment(view);
      else if (document.querySelector('.equipment-workspace').dataset.view !== view) openEquipment(view);
      else setPause(false);
    }
  });
  $('city-travel').addEventListener('click', () => Field.visitCity());
  $('p-characters').addEventListener('click', async () => {
    const list = $('character-list'); list.hidden = !list.hidden;
    if (list.hidden) return;
    await Online.refreshCharacters();
    list.replaceChildren(...Online.characters.map(slot => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'btn ghost';
      button.textContent = `${slot.look.name} · ${slot.look.class}`;
      button.addEventListener('click', () => { if (slot.key === Online.currentKey) { setPause(false); list.hidden = true; return; } const look = Online.select(slot.key); leaveGame(); save.char = look; persist(); enterGame(); list.hidden = true; });
      return button;
    }));
    if (!list.children.length) list.textContent = 'Your character will appear here after connecting.';
  });
  $('p-equipment').addEventListener('click', () => openEquipment());
  $('equipment-open').addEventListener('click', () => openEquipment());
  $('inventory-open').addEventListener('click', () => openEquipment('bags'));
  $('bag-expand').addEventListener('click', () => { setPause(false); Field.visitNpc('merchant'); });
  $('bags-close').addEventListener('click', () => setPause(false));
  $('bag-character').addEventListener('click', () => openEquipment(document.querySelector('.equipment-workspace').dataset.view === 'bags' ? 'both' : 'bags'));
  addEventListener('inventory-change', () => { if (!$('equipment').hidden) renderEquipment(); });
  addEventListener('character-stats-change', () => { if (!$('equipment').hidden) renderEquipment(); });
  $('equipment').addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const nodes = [...$('equipment').querySelectorAll('button:not(:disabled), select:not(:disabled), input:not(:disabled)')];
    const visible = nodes.filter(n => n.getClientRects().length > 0), first = visible[0], last = visible.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  $('equipment-close').addEventListener('click', () => setPause(false));
  $('p-resume').addEventListener('click', () => setPause(false));
  $('p-title').addEventListener('click', () => show('splash'));
  $('p-new').addEventListener('click', () => {
    if (Online.mode === 'account' && Online.account && Online.characters.length >= Online.account.max) { showToast(`Your account already has ${Online.account.max} characters. Delete one first.`); return; }
    load(save.char || cfg); save.draft = { ...cfg }; persist(); show('create'); });

  // ---------- awaken the horn ----------
  let starting = false;
  function awaken() {
    if (starting || scene !== 'splash') return;
    starting = true;
    horn();
    const f = $('flash');
    f.classList.remove('go'); void f.offsetWidth; f.classList.add('go');
    if (!reduced) { stage.classList.add('shake'); setTimeout(() => stage.classList.remove('shake'), 520); }
    burst = 1;
    setTimeout(() => { show('login'); starting = false; }, reduced ? 100 : 900);
  }
  $('start').addEventListener('click', awaken);

  // ---------- sign-in (account.js): guest, game account or gunning.se SSO ----------
  // save.char always belongs to the current mode. A guest's look is set aside while an account plays, and comes back after.
  function setMode(mode) {
    if (mode === 'account' && save.mode !== 'account') { save.guestChar = save.char; save.char = null; save.mode = 'account'; persist(); }
    else if (mode === 'guest' && save.mode === 'account') { save.char = save.guestChar || null; delete save.guestChar; save.mode = 'guest'; persist(); }
    if (mode === 'account') Online.useAccount(); else Online.useGuest();
  }
  Account.init({
    show,
    guest() { setMode('guest'); show(save.char ? 'game' : 'create'); },
    account() { setMode('account'); },
    play(look) { save.char = { ...look }; save.draft = null; persist(); show('game'); },
    create() { load(save.char || cfg); save.draft = { ...cfg }; persist(); Online.newCharacter(); show('create'); },
  });

  // ---------- effects: snow, embers, twinkling stars ----------
  const cv = $('fx'), ctx = cv.getContext('2d');
  let W = 0, H = 0, dpr = 1, burst = 0;
  const snow = [], embers = [], stars = [];
  const FIRE = { x: .5, y: .8 };
  const motes = [];

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = cv.clientWidth; H = cv.clientHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  }
  const rnd = (a, b) => a + Math.random() * (b - a);
  function initFx() {
    snow.length = embers.length = stars.length = 0;
    for (let i = 0; i < 140; i++) snow.push({ x: Math.random(), y: Math.random(), r: rnd(.0008, .0028), v: rnd(.03, .09), sway: rnd(0, 6.28), sp: rnd(.4, 1.2) });
    for (let i = 0; i < 36; i++) embers.push(newEmber(true));
    for (let i = 0; i < 40; i++) motes.push(newMote(true));
    for (let i = 0; i < 26; i++) stars.push({ x: rnd(.02, .98), y: rnd(.02, .32), ph: rnd(0, 6.28), sp: rnd(.6, 1.8), s: rnd(.004, .010) });
  }
  function newEmber(scatter) {
    return { x: FIRE.x + rnd(-.02, .02), y: scatter ? rnd(.5, .78) : FIRE.y + rnd(-.03, .01), vx: rnd(-.015, .015), vy: -rnd(.05, .14), life: rnd(1.2, 3), age: scatter ? rnd(0, 1) : 0, r: rnd(.0009, .0024) };
  }
  function newMote(scatter) {
    const x = rnd(.25, .62);
    return { x, y: scatter ? rnd(.2, .62) : rnd(.5, .62), vx: rnd(-.006, .006), vy: -rnd(.012, .04), life: rnd(4, 9), age: scatter ? rnd(0, 4) : 0, r: rnd(.0009, .0024) };
  }
  function sparkle(x, y, s, a) {
    ctx.globalAlpha = a; ctx.fillStyle = '#e8fbff';
    ctx.beginPath();
    ctx.moveTo(x, y - s); ctx.quadraticCurveTo(x, y, x + s, y); ctx.quadraticCurveTo(x, y, x, y + s);
    ctx.quadraticCurveTo(x, y, x - s, y); ctx.quadraticCurveTo(x, y, x, y - s); ctx.fill();
  }

  const sparksList = [];
  let slashT = 0;
  function emitSpark(x, y, col, power = 1) {
    const a = -Math.PI / 2 + rnd(-1.2, 1.2), sp = rnd(60, 220) * power;
    sparksList.push({ x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, life: rnd(.5, 1.2), age: 0, r: rnd(1.2, 3), col, g: power < .6 ? -30 : 260 });
  }
  function burstSparks(n, where = 'blade', col = '#ffc857', power = 1) {
    if (!view.ok || !view.loaded || reduced) return;
    const cr = cv.getBoundingClientRect(), [x, y] = view.anchor(where);
    for (let i = 0; i < n; i++) emitSpark(x - cr.left + rnd(-25, 25), y - cr.top + rnd(-25, 25), col, power);
  }
  let sparkAcc = 0;
  function drawCreate(dt, now) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#fff';
    for (const p of snow) {
      p.y += p.v * dt; p.sway += p.sp * dt; p.x += Math.sin(p.sway) * .012 * dt;
      if (p.y > 1.02) { p.y = -.02; p.x = Math.random(); }
      ctx.globalAlpha = .5 + p.r * 120;
      ctx.beginPath(); ctx.arc(p.x * W, p.y * H, p.r * W, 0, 6.283); ctx.fill();
    }
    sparkAcc += dt * 7;                                           // the runes throw off a few cyan sparks
    if (sparkAcc >= 1) { const n = Math.floor(sparkAcc); sparkAcc -= n; burstSparks(n, 'blade', '#9af0ff', .5); }
    ctx.globalCompositeOperation = 'lighter';
    for (let i = sparksList.length - 1; i >= 0; i--) {
      const s = sparksList[i];
      s.age += dt; if (s.age > s.life) { sparksList.splice(i, 1); continue; }
      s.vy += s.g * dt; s.x += s.vx * dt; s.y += s.vy * dt;
      ctx.globalAlpha = 1 - s.age / s.life; ctx.fillStyle = s.col;
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 6.283); ctx.fill();
    }
    // slash arc: the blade's sweep, drawn as a fading glowing crescent
    const age = now / 1000 - slashT;
    if (slashT && age >= 0 && age < .42 && view.ok && view.loaded) {
      const cr = cv.getBoundingClientRect(), g = view.slashGeometry();
      const k = Math.min(1, age / .16), end = g.a0 + .2 - 1.35 * (k * (2 - k)), fade = 1 - age / .42;
      ctx.lineCap = 'round';
      for (const [w, col, al] of [[26, '#59d9ff', .35], [14, '#bff6ff', .7], [5, '#ffffff', 1]]) {
        ctx.globalAlpha = al * fade; ctx.strokeStyle = col; ctx.lineWidth = w * fade + 2;
        ctx.beginPath(); ctx.arc(g.cx - cr.left, g.cy - cr.top, g.r * 1.05, g.a0 + .2, end, true); ctx.stroke();
      }
    }
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
  }

  let last = performance.now();
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, .05); last = now;
    if (scene === 'create') { drawCreate(dt, now); return; }
    if (scene !== 'splash') return;               // nothing to paint on other scenes
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const t0 = now / 1000;

    for (const s of stars) {
      const a = .5 + .5 * Math.sin(t0 * s.sp + s.ph);
      if (a > .15) sparkle(s.x * W, s.y * H, s.s * W * (.5 + a * .6), a * .85);
    }
    ctx.fillStyle = '#fff';
    for (const p of snow) {
      p.y += p.v * dt * (burst ? 2.5 : 1); p.sway += p.sp * dt;
      p.x += Math.sin(p.sway) * .012 * dt;
      if (p.y > 1.02) { p.y = -.02; p.x = Math.random(); }
      ctx.globalAlpha = .55 + p.r * 120;
      ctx.beginPath(); ctx.arc(p.x * W, p.y * H, p.r * W, 0, 6.283); ctx.fill();
    }
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < motes.length; i++) {
      const m = motes[i];
      m.age += dt; m.x += (m.vx + Math.sin(t0 * .8 + i) * .004) * dt; m.y += m.vy * dt;
      if (m.age > m.life) { motes[i] = newMote(false); continue; }
      const k = Math.sin(Math.PI * m.age / m.life);
      ctx.globalAlpha = k * .8; ctx.fillStyle = '#9af0ff';
      ctx.beginPath(); ctx.arc(m.x * W, m.y * H, m.r * W * (1 + k * .6), 0, 6.283); ctx.fill();
    }
    for (let i = 0; i < embers.length; i++) {
      const e = embers[i];
      e.age += dt; e.x += (e.vx + Math.sin(t0 * 3 + i) * .01) * dt; e.y += e.vy * dt * (burst ? 2.5 : 1);
      if (e.age > e.life) { embers[i] = newEmber(false); continue; }
      const k = 1 - e.age / e.life;
      ctx.globalAlpha = k * .95; ctx.fillStyle = k > .55 ? '#ffd27a' : '#ff7a2a';
      ctx.beginPath(); ctx.arc(e.x * W, e.y * H, e.r * W * (.5 + k), 0, 6.283); ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    if (burst) burst = Math.max(0, burst - dt);
  }

  // ---------- boot ----------
  applyI18n();
  buildControls(); updateClass();
  if (!reduced) {
    resize(); initFx();
    new ResizeObserver(resize).observe(cv);
    requestAnimationFrame(frame);
  } else {
    // reduced motion: keep it still, no canvas loop
    cv.remove();
  }
  // Preferences shared with settings.js (volumes and the HUD layout); it never touches localStorage itself.
  window.Prefs = {
    get music() { return save.musicVol; }, get sfx() { return save.sfxVol; }, get sound() { return save.sound; },
    get layout() { return save.ui && typeof save.ui === 'object' ? save.ui : {}; },
    set(patch) {
      if ('musicVol' in patch) save.musicVol = vol(patch.musicVol);
      if ('sfxVol' in patch) save.sfxVol = vol(patch.sfxVol);
      if ('sound' in patch) save.sound = !!patch.sound;
      if ('ui' in patch) save.ui = patch.ui;
      persist(); applyMusicLevel(.4);
      if (sfxGain) sfxGain.gain.value = taper(save.sfxVol);
      dispatchEvent(new Event('prefs-change'));
    },
    preview() { SFX.hit(); },
  };
  ensureMusic();
  show('splash');
})();
