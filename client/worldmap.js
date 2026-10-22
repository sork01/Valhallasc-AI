'use strict';
// World map (M, or the button under the minimap). Everything is drawn from window.WORLD_MAP, so a zone added to
// world/map.txt appears with its real ground, obstacles, camp, gates and spawn points; the only hand-made part is
// LAYOUT, where each public zone sits on the world sheet. Sealed dungeon floor plans are hidden until opened.
// The world sheet is a connected geographic atlas: each island uses its actual zone ground,
// and land bridges follow the authoritative portal graph. Press a region to zoom into its map.
(() => {
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const STAGE = { w: 160, h: 99 };
  // Square tiles on the 160x99 sheet (a circle in each square is the zone's ground). The gate graph is a tree, and this is that tree laid
  // out as a world: tiles that share a gate stand one isthmus apart, and nothing else is closer than a label's width.
  const LAYOUT = [{x:7.6,y:80.4,s:10.9},{x:10.7,y:66.3,s:10.9},{x:3.8,y:49.9,s:13.5},{x:2.0,y:32.2,s:13.5},{x:21.0,y:42.5,s:16.0},{x:31.9,y:62.4,s:6.4},{x:21.3,y:18.3,s:18.6},{x:48.9,y:3.9,s:16.0},{x:44.5,y:33.5,s:17.3},{x:46.9,y:65.8,s:18.6},{x:63.7,y:86.4,s:6.4},{x:42.4,y:58.2,s:6.4},{x:35.1,y:73.7,s:6.4},{x:67.7,y:46.6,s:13.5},{x:71.9,y:29.5,s:13.5},{x:72.7,y:11.9,s:13.5},{x:89.9,y:9.7,s:13.5},{x:97.9,y:25.3,s:17.6},{x:119.6,y:36.8,s:6.4},{x:103.9,y:47.6,s:13.5},{x:88.4,y:56.4,s:13.5},{x:74.5,y:67.8,s:14.1},{x:89.5,y:78.8,s:14.8},{x:106.2,y:70.0,s:13.5},{x:113.1,y:86.1,s:10.9},{x:124.0,y:65.6,s:16.0},{x:142.0,y:55.1,s:16.0},{x:134.6,y:34.6,s:16.7},{x:118.6,y:2.6,s:27},{x:122.1,y:51.3,s:6.4},{x:89.4,y:45.9,s:6.4},{x:72.8,y:85.7,s:6.4},{x:80.3,y:90.6,s:6.4},{x:128.1,y:90.6,s:6.4},{x:142.2,y:79.6,s:6.4},{x:151.6,y:28.4,s:6.4},{x:151.6,y:10.6,s:6.4},{x:151.4,y:19.5,s:6.4},{x:108.4,y:2.0,s:6.4},{x:149.7,y:2.0,s:6.4},null,{x:7.0,y:15.0,s:6.4},{x:35.0,y:3.9,s:6.4},{x:41.0,y:25.0,s:6.4},{x:108.4,y:12.0,s:6.4},{x:89.5,y:29.2,s:6.4},{x:79.5,y:29.2,s:6.4}];
  const GROUND = { chained_forge:'#63332e', emberwake:'#49414d', blackhour:'#211b2e', longship:'#123b46', skybridge:'#222e4d', nornroot:'#44374f', meadow: '#3f9b48', ember: '#2b1f22', frost: '#cfe3f0', fen: '#2f4a2c', city: '#5f9b4a', asterion: '#364a72', moonwell:'#153d58', stormglass:'#263b51', sunward:'#5baa49', ribbonwild:'#d98db2', tanglecrown:'#287a5b', worldtree:'#2f9369', lapiserg:'#d3a468', frostwake:'#c8e6f1', cairnspine:'#6b7378', yearwheel:'#a6cf9b', heartwood:'#806244', vault: '#07080e', eye_below: '#102b3d', elder_hollow: '#31492f', thousandfold: '#40264d', rain_crown: '#1c5251', seed_vault: '#415532', sunken_astrolabe: '#254e59', thunderheart_gate: '#273f60', blooming_labyrinth:'#36553f', solar_crucible:'#754530', amber_archive:'#735238', silent_solstice:'#3b5872', wyrd: '#6a5430', sky: '#1a1838', deep: '#0b3550', nacre: '#286776', astral: '#39776f', prismwaste: '#ad887e', orrery: '#37394e', moonspore: '#1c4244', cathedral_left: '#123b38', cathedral_right: '#442c3e', cathedral_main: '#161529' };
  const DIRT = { chained_forge:'#b4a09c', emberwake:"#b39170", blackhour:'#8d7ca3', longship:'#bf9c71', skybridge:'#8fd8f2', nornroot:'#c4a77f', meadow: '#c9a26a', ember: '#6a5040', frost: '#9fb7cc', fen: '#8a6a40', city: '#b6a98c', asterion: '#9ec6d9', moonwell:'#a8d5cf', stormglass:'#9ebdc1', sunward:'#d8bd83', ribbonwild:'#ffe3a0', tanglecrown:'#b99a62', worldtree:'#bd9662', lapiserg:'#efd59e', frostwake:'#8abfd3', cairnspine:'#b7a07b', yearwheel:'#f0d6a7', heartwood:'#b18a5f', vault: '#3a3f55', eye_below: '#386c78', elder_hollow: '#819965', thousandfold: '#ae779d', rain_crown: '#6aa895', seed_vault: '#b6a676', sunken_astrolabe: '#c0ac79', thunderheart_gate: '#a9cde3', blooming_labyrinth:'#deb4cd', solar_crucible:'#e9bb79', amber_archive:'#eac286', silent_solstice:'#b8d5e8', wyrd: '#b89860', sky: '#f0c8f4', deep: '#c8c29a', nacre: '#addbd3', astral: '#d7bc84', prismwaste: '#ead7a8', orrery: '#ad907b', moonspore: '#a5c4a8', cathedral_left: '#50877c', cathedral_right: '#967086', cathedral_main: '#514568' };
  const PORTAL = { chained_forge:'#77e5df', emberwake:"#ffbc70", blackhour:'#8aece1', longship:'#79dcc4', skybridge:'#7fe5ff', nornroot:'#edd293', meadow: '#7ae8c8', ember: '#ff8a3a', frost: '#8fd8ff', fen: '#b8e060', city: '#ffd36a', asterion: '#d9e8ff', moonwell:'#f8e8ad', stormglass:'#aaf2f0', sunward:'#f8da90', ribbonwild:'#ff86b9', tanglecrown:'#a6e5ae', worldtree:'#c8f7a7', lapiserg:'#79d5d3', frostwake:'#9af0da', cairnspine:'#f2cb89', yearwheel:'#ffe7a4', heartwood:'#ffe0a1', vault: '#59d9ff', eye_below: '#a3eee5', elder_hollow: '#d7ecaa', thousandfold: '#ffdcb4', rain_crown: '#c2f5db', seed_vault: '#f3df9a', sunken_astrolabe: '#a3e9ed', thunderheart_gate: '#d1eaff', blooming_labyrinth:'#f7c3df', solar_crucible:'#ffe0a0', amber_archive:'#f6d99d', silent_solstice:'#e6f3ff', wyrd: '#e0963a', sky: '#9fc4ff', deep: '#4fe0e8', nacre: '#b0ffe6', astral: '#c4b6ff', prismwaste: '#ffe3ac', orrery: '#f4c981', moonspore: '#c4f4af', cathedral_left: '#64daca', cathedral_right: '#f29cb4', cathedral_main: '#d5b9ff' };
  const BLURB = { chained_forge:'Ten halls descend beneath Asterion to Eldmarr and his nine Wardens. A level-99 raid for ten fighters.', emberwake:'A volcanic road beyond Asterion. Three elites guard the failing chains; Eldmarr speaks behind the sealed Nine-Chain Door.',
    blackhour: 'A level-99 midnight clockwork foundry beneath the Equinox Crossing. Five blue-geared fighters face giant machines for exclusive purple Nullforged equipment.',
    longship: 'A private level-35 wreck west of Keelhaven: a pointed hull, split cargo hatch, drowned capstan and Captain Svala at the prow.',
    skybridge: 'A private level-30 sanctuary of broken rainbow-glass arches below Bifrost Reach, with three guardians and the Bifrost Archon.',
    nornroot: 'A private level-25 barrow beneath the Norn Stones in Wyrdwood, with three guardians and a loom of unwritten fates.',
    meadow: 'Green pastures round the walled town of Alderhaven.',
    ember: 'Lava fords and ash-grey crags above Cinderwatch Camp.',
    frost: 'Four rings of ice that spiral up to a summit bowl.',
    fen: 'A dusk fen round a dark lake, lit by the lanterns of Lanternmere.',
    wyrd: 'An autumn forest, a troll bridge and a storm-wracked moor, between Hollowmoot and Skuldwatch.',
    sky: 'Floating islands over the storm, joined by rainbow-shard bridges, around Heimdall\'s Perch.',
    deep: 'The sea floor under the storm: the Shallows round Keelhaven and the Net, a labyrinth of living coral with Ran\'s Court at its heart.',
    nacre: 'A peaceful merfolk city of 120 shell homes, coral gardens and a Meeting Stone beside the three-wing Drowned Cathedral.',
    astral: 'A grassy impact basin of starglass groves and living constellations, reached from Nacrehold.',
    prismwaste: 'A salt and mirror desert beyond Astralhollow, with three broken ridges and the Last Shade refuge.',
    orrery: 'A vast broken clock beyond the Prismwaste, with the Stillpoint refuge and two dangerous winding courts.',
    moonspore: 'A fallen moon feeds a luminous fungal forest. Lamplight Refuge lies below three elite courts.',
    asterion: 'Seven rings of glass-roof houses turn around a singing astrolabe. A Meeting Stone opens the Moonwell below.',
    moonwell: 'A starlit water garden of floating petal islands and four guardians, beneath the Meeting Stone.',
    stormglass: 'Black sand and white lightning beyond Asterion. Breakwater Camp guards the open Eye Below.',
    eye_below: 'A private level-65 descent through deepglass halls, three wardens and a living lens.',
    elder_hollow: 'A private level-70 descent through living roots, three guardians and the Elder Heart.',
    thousandfold: 'A private level-75 palace of silk galleries, living paper and three guardians.',
    rain_crown: 'An open private level-80 jade temple with rain halls and three guardians.',
    seed_vault: 'An open private level-80 seed chamber beneath Veyrroot, with living roots and three guardians.',
    sunken_astrolabe: 'An open private level-85 brass observatory beneath the Lapis Erg, with a buried sky and three guardians.',
    thunderheart_gate: 'An open private level-95 storm chamber beneath the Cairnspine, with three charged guardians.',
    blooming_labyrinth: 'An open private level-97 maze of spring roots and glass petals, with three guardians.',
    solar_crucible: 'An open level-98 brass forge beneath Solhaven, with three solar guardians.',
    amber_archive: 'An open level-99 library of living records beneath Harvestwatch.',
    silent_solstice: 'An open level-99 frozen court beneath Rimehold.',
    sunward: 'A clear river divides sunlit grass, apple rows and old oakwood. Millbridge watches the Elder Hollow beneath the roots.',
    ribbonwild: 'A bright processional wheel of color courts and silk tents. The Thousandfold Pavilion opens through its gilded mask doors.',
    tanglecrown: 'A dense rain jungle with braided channels, giant kapok trees and root bridges. Banyan Landing guards the open Rain Crown Temple.',
    worldtree: 'Veyrroot is an open city of branch rings, leaf-roof markets and hanging rooms in one enormous jungle tree.',
    heartwood: 'The hollow heart of Veyrroot holds amber archives and the living pith. The Seed Vault opens into the living roots below.',
    lapiserg: 'Ochre dunes encircle three turquoise oases. Azure Wells leads to an open brass astrolabe beneath the sand.',
    frostwake: 'A snow-bright shelf split by blue crevasses. Frostwake Station watches three elite territories under the aurora.',
    cairnspine: 'Four slate switchbacks climb through giant boulders and white leafless trees. Boulderwatch guards the open Thunderheart Gate.',
    yearwheel: 'The world turns through four immense seasons. Springmere, Solhaven, Harvestwatch and Rimehold circle the Equinox Crossing, The four seasonal dungeons open beneath their courts.',
    cathedral_left:'The Flooded Cloister: level 40, four bosses, a private five-player wing.',
    cathedral_right:'The Coral Reliquary: level 45, four bosses, a private five-player wing.',
    cathedral_main:'The Grand Nave: level 50, four bosses, a private five-player wing.',
    vault: 'A dungeon of bones and torchlight under the Meeting Stone, for a party of five.',
  };
  // Base level and a dot colour for every enemy kind (the level matches Slime::default_level in server/src/world.rs;
  // the test compares the two).
  const KINDS = {
    ew_ashback: ['Ashback Salamander', 95, '#e99055'],
    ew_glasswing: ['Obsidian Glasswing', 96, '#a4b9cf'],
    ew_slagjaw: ['Slagjaw Burrower', 97, '#dca16b'],
    ew_cinderhorn: ['Cinderhorn Ram', 98, '#cd785b'],
    ew_chainmaw: ['Chainmaw, the First Shackle', 97, '#f2b16a'],
    ew_bellows: ['Yrsa, the Living Bellows', 99, '#88cbd3'],
    ew_crown: ['The Uncrowned Ember', 99, '#eab776'],

    green: ['Green Slime', 2, '#4fd25f'], blue: ['Blue Slime', 3, '#4aa8ff'], pink: ['Pink Slime', 3, '#ff7bbd'], yellow: ['Golden Slime', 4, '#ffd23f'],
    beetle: ['Ironhide Beetle', 5, '#8aafbf'], big: ['King Slime', 6, '#8f6bff'],
    wisp: ['Cinder Wisp', 5, '#ee6a1c'], spider: ['Magma Spider', 7, '#b09ab8'], wraith: ['Ash Wraith', 8, '#a89cd0'], golem: ['Basalt Golem', 10, '#c0b8c0'],
    cinderlord: ['Cinderlord (Elite · 2 players)', 10, '#ffb13b'],
    crab: ['Rime Crab', 10, '#6fb3dc'], wolf: ['Frostfang Wolf', 12, '#9fb4c8'], yeti: ['Glacier Yeti', 13, '#e4eef8'], wyrm: ['Rime Wyrm', 15, '#6bc6e8'],
    gloomroot: ['Gloomroot Colossus (Elite · 5 players)', 20, '#4fe0c8'],
    toad: ['Fen Toad', 15, '#8bc34a'], croc: ['Mire Crocodile', 17, '#a9c45a'], knight: ['Drowned Knight', 18, '#8fc0a8'], hydra: ['Mire Hydra', 20, '#c4e8b0'],
    thrall: ['Vault Thrall', 19, '#d8d2bc'], archer: ['Bone Archer (ranged)', 19, '#e6dfc4'], acolyte: ['Hollow Acolyte (ranged)', 20, '#b46bff'],
    gatewarden: ['Hrolf Bonegate (Boss)', 20, '#ffd24a'], choir: ['Valka, the Hollow Choir (Boss)', 20, '#7be0ff'],
    colossus: ['Ironwake, the Vault Colossus (Boss)', 21, '#ff9a3a'], hollowking: ['Haldor, the Hollow King (Boss)', 21, '#9cff8f'],
    boar: ['Rotfang Boar', 21, '#d0603a'], crow: ['Gallowcrow (ranged)', 23, '#9a84d6'], troll: ['Mosshide Troll', 25, '#6fb064'], weaver: ['Wyrdweaver (ranged)', 27, '#c070e8'],
    galehound: ['Galehound', 30, '#9fc0ee'], prismgolem: ['Prism Golem', 31, '#a9a0f0'], skyray: ['Skyray (ranged)', 32, '#6a86d0'], einherjar: ['Hollow Einherjar', 33, '#8ad0e8'], thunderroc: ['Thunderroc', 35, '#f0c070'],
    draugr: ['Drowned Draugr', 35, '#8ac4b8'], angler: ['Lantern Angler (ranged)', 36, '#9ffff0'], moray: ['Gnashing Moray', 37, '#c8e070'], siren: ['Siren (ranged)', 38, '#ff9ae8'], shellback: ['Shellback', 39, '#a8d090'], kraken: ['The Kraken (Elite · 5 players)', 40, '#b890f0'], hvitserk: ['Hvitserk (Elite · 3 players)', 37, '#e0b43a'], ghostmaw: ['Ghostmaw (Elite · 3 players)', 39, '#d8f0f8'],
    voidmoth: ['Void Moth', 40, '#c7a8ff'], crystalwyrm: ['Crystalwyrm', 41, '#6de8ff'], orbitbeetle: ['Orbit Beetle', 42, '#f4a43a'], eclipsedryad: ['Eclipse Dryad', 43, '#9ed17a'], meteorgolem: ['Meteor Golem', 45, '#b39bd1'],
    miragejackal: ['Mirage Jackal',45,'#e7b990'], shardscarab:['Shard Scarab',46,'#99e6dc'], glassharrier:['Glass Harrier',47,'#d5c5ff'], prismsentinel:['Prism Sentinel',48,'#d5e9ed'], mirrorqueen:['Mirror Queen (Elite · 3 players)',49,'#e7b8ff'], sunshard:['Sunshard (Elite · 5 players)',50,'#ffd58a'],
    bronzemantis:['Bronze Mantis',50,'#c8a66b'], gearling:['Gearling',51,'#9bc2be'], orbitseer:['Orbit Seer (ranged)',52,'#a3dce4'], chronoguard:['Chronoguard',53,'#b4a7ba'], pendulummatron:['Pendulum Matron (Elite · 3 players)',54,'#e1b5a9'], epochengine:['Epoch Engine (Elite · 5 players)',55,'#dab47d'],
    glowcapgrazer:['Glowcap Grazer',55,'#bbffae'], silkwing:['Silkwing',56,'#c7f8ee'], rootlurker:['Rootlurker',57,'#c9ae83'], lanternwraith:['Lantern Wraith (ranged)',58,'#b8ffa5'], mireheart:['Mireheart (Elite · 3 players)',58,'#efb9ba'], silverwidow:['Silver Widow (Elite · 3 players)',59,'#e9b9ff'], nightbloom:['Nightbloom (Elite · 5 players)',60,'#eafca1'],
    dew_moth:['Dew Moth',60,'#a8d5cf'], lumen_eel:['Lumen Eel',60,'#9af2d7'], rootbell:['Rootbell',60,'#f8e8ad'],
    tideglass_heron:['Tideglass Heron (Boss · 5 players)',60,'#a8d5cf'], hourpetal_stag:['Hourpetal Stag (Boss · 5 players)',60,'#f8e8ad'], moonskein_weaver:['Moonskein Weaver (Boss · 5 players)',60,'#f0a6be'],
    moonwell_echo:['Moonwell Echo (Boss · 5 players)',60,'#91f6e2'],
    saltclaw:['Saltclaw',60,'#d5e6d6'], stormgull:['Stormgull',61,'#f2f1db'],
    glassray:['Glassray',62,'#b7eee5'], breakersentinel:['Breaker Sentinel',64,'#d3d3c4'],
    maelstromheart:['Maelstrom Heart (Elite · 5 players)',65,'#f3efff'],
    meadowhare:['Meadow Hare',65,'#eed4a1'],sunbacksnail:['Sunback Snail',66,'#f2ebbd'],
    brushfox:['Brush Fox',67,'#d57b49'],spadebadger:['Spadeclaw Badger',68,'#e7e1c8'],
    honeyjaw:['Old Honeyjaw (Elite · 3 players)',69,'#ffe497'],
    wickerwarden:['Wicker Warden (Elite · 5 players)',70,'#fce3a2'],
    ribbongecko:['Ribbon Gecko',70,'#31c7bd'],balloonbeetle:['Balloon Beetle',71,'#b277db'],
    paintedmacaw:['Painted Macaw',72,'#52bbdf'],jesterling:['Jesterling',73,'#d36ab3'],
    paradegryphon:['Parade Gryphon (Elite · 3 players)',74,'#f7bb72'],
    maskcolossus:['Masquerade Colossus (Elite · 5 players)',75,'#ae94dc'],
    orchidmantis:['Orchid Mantis',75,'#d5ef83'],canopyglider:['Canopy Glider',76,'#59c0b5'],
    poolcaiman:['Blackwater Caiman',77,'#6ea58c'],drumgorilla:['Drum Gorilla',78,'#c69a70'],
    jadeanaconda:['Jade Anaconda (Elite · 3 players)',79,'#4dc098'],
    crownjaguar:['Crown Jaguar (Elite · 5 players)',80,'#f1ce73'],
    sapbeetle:['Sap Beetle',80,'#e3ae59'],lanternhornet:['Lantern Hornet',80,'#d7cf74'],
    mosslemur:['Moss Lemur',80,'#c8d68a'],barkmimic:['Bark Mimic',80,'#c5a479'],
    sandhopper:['Sandhopper',80,'#ca9958'],dunefennec:['Dune Fennec',81,'#d6a278'],glassscorpion:['Glass Scorpion',82,'#71bed0'],sunvulture:['Sun Vulture',83,'#c69b76'],
    dunecolossus:['Dune Colossus (Elite · 3 players)',84,'#d2a274'],mirageroc:['Mirage Roc (Elite · 5 players)',85,'#8dc3c6'],
    snowhare:['Snow Hare',85,'#c8dce4'],iceotter:['Ice Otter',86,'#86b3c5'],frostheron:['Frost Heron',87,'#b4d7e0'],glaciercrab:['Glacier Crab',88,'#66b4d0'],
    bellmammoth:['Bell Mammoth (Elite · 3 players)',88,'#d8ab68'],auroramanta:['Aurora Manta (Elite · 4 players)',89,'#68bcb8'],crevasseleviathan:['Crevasse Leviathan (Elite · 5 players)',90,'#77c9e4'],
    screeferret:['Scree Ferret',90,'#c4a78a'],stoneibex:['Stone Ibex',91,'#baa88c'],slateraven:['Slate Raven',92,'#828fa0'],ridgeadder:['Ridge Adder',93,'#a1ad87'],
    cairnbehemoth:['Cairn Behemoth (Elite · 3 players)',93,'#d0b38d'],whitebarktitan:['Whitebark Titan (Elite · 4 players)',94,'#e7dfc8'],stormcondor:['Storm Condor (Elite · 5 players)',95,'#91c9c7'],
    brooknewt:['Brook Newt',95,'#76c9ae'],sundarter:['Sun Darter',96,'#ffcf63'],acornmimic:['Acorn Mimic',97,'#c17b48'],snowstoat:['Snow Stoat',98,'#d9f5f9'],
    bloomtortoise:['Bloom Tortoise (Elite)',95,'#9bd579'],petalchimera:['Petal Chimera (Elite)',96,'#ec91c2'],rainseraph:['Rain Seraph (Elite)',97,'#8dd9dc'],
    glasslion:['Glass Lion (Elite)',96,'#ffc06d'],sunwheel:['Sunwheel (Elite)',97,'#ffe67d'],firephoenix:['Fire Phoenix (Elite)',98,'#f18c58'],
    lanternowl:['Lantern Owl (Elite)',97,'#e5a76e'],harvestreaper:['Harvest Reaper (Elite)',98,'#ac6c4b'],ambermantis:['Amber Mantis (Elite)',99,'#f2b861'],
    rimesaber:['Rime Saber (Elite)',97,'#a4d9ed'],snowgiant:['Snow Giant (Elite)',98,'#d8eff7'],longnightwyrm:['Longnight Wyrm (Elite)',99,'#9abbd9'],
    ram: ['Stormram', 29, '#8fe0ff'], oakhorn: ['Oakhorn (Elite · 3 players)', 25, '#ff9a3a'], hrungnir: ['Hrungnir (Elite · 5 players)', 30, '#7ab4ff'],
  };
  for (const e of CATHEDRAL_ENEMIES) KINDS[e.kind]=[e.name+(e.boss?' (Boss)':''),e.level,e.color];
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const kindInfo = kind => KINDS[kind] || [kind, 1, '#ff6b8a'];
  const travelMasters = z => (z.npcs || []).filter(n => n.travelStop);
  const onWorldSheet = z => z && !z.sealedTemplate && z.theme !== 'arena';
  const SEALED = { year_bloom_gate: 'Blooming Labyrinth', year_solar_gate: 'Solar Crucible', year_amber_gate: 'Amber Archive', year_solstice_gate: 'Silent Solstice' };
  // Fog of war: the server saves which of a zone's 3x3 cells the character has stood in (Field.explored, one bitmask per
  // zone). Nothing from an unvisited cell is shown: not its ground, gates, camp, enemies or people.
  const CELLS = 9;
  const maskOf = i => { const e = window.Field?.explored; return e ? (e[i] || 0) : (1 << CELLS) - 1; };
  const visited = i => maskOf(i) !== 0;
  const charted = i => { let n = 0; for (let b = maskOf(i); b; b >>= 1) n += b & 1; return n; };
  const known = (i, x, y) => window.Field.fog.seen(i, x, y);
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  let zones = null, graph = [], tiles = [], nameNodes = [], roadRefs = [], fogSignature = '', view = 'world', current = 0, previousFocus = null, highlight = null, timer = 0, tickTimer = 0, tileY = .54;
  const cache = new Map();

  function load() {
    if (zones) return zones;
    const W = window.WORLD_MAP;
    zones = [{ ...W, theme: 'meadow', name: W.name || 'Greenmeadow', paths: window.Field?.meadowPaths || [] },
      ...(W.zones || []).map(z => ({ theme: 'ember', paths: [], ...z }))];
    zones.forEach((z, i) => {
      z.portals ||= [];
      const levels = z.levels || (() => { const l = z.slimes.filter(s => s.kind !== 'big').map(s => kindInfo(s.kind)[1]); return l.length ? [Math.min(...l), Math.max(...l)] : null; })();
      z.range = levels;
      z.place = LAYOUT[i] || { x: 4 + ((i - LAYOUT.length) % 4) * 24, y: 58, s: 16 };   // unplaced zones queue along the bottom edge
    });
    // Each directed edge is a real gate. The graph also keeps the city and private dungeon branches.
    graph = zones.map((z, i) => z.portals.filter(p => Number.isInteger(p.to) && zones[p.to] && p.to !== i).map(p => ({ to: p.to, id: p.id, x: p.x, y: p.y })));
    return zones;
  }
  function route(from, to) {
    if (from === to) return [from];
    const queue = [from], prev = new Map([[from, -1]]);
    for (const zone of queue) for (const gate of graph[zone] || []) {
      if (!visited(gate.to) || prev.has(gate.to)) continue;
      prev.set(gate.to, zone);
      if (gate.to === to) { const path = [to]; for (let n = zone; n !== -1; n = prev.get(n)) path.unshift(n); return path; }
      queue.push(gate.to);
    }
    return [];
  }
  function routePaint(to) {
    const path = route(window.Field.zone || 0, to), edges = new Set(path.slice(1).map((n, i) => [path[i], n].sort((a, b) => a - b).join('-')));
    roadRefs.forEach(r => r.node.classList.toggle('wm-route-road', edges.has(r.pair)));
  }

  // ---------- ground ----------
  function objectColour(o, theme) {
    if(o.kind.startsWith('ew_')) return o.kind==='ew_lava'?'#ed864a':o.kind==='ew_door'?'#f0bd80':'#82717a';
    const fen = theme === 'fen', frost = theme === 'frost', ember = theme === 'ember', wyrd = theme === 'wyrd';
    switch (o.kind) {
      case 'skypine': return '#52c0a0';
      case 'prism': return '#b9a0ff';
      case 'orrery': return '#f4c981';
      case 'moonspore': return '#c4f4af';
      case 'column': return '#e8ecff';
      case 'skyrock': return '#aab6d8';
      case 'cloudpuff': return '#f0f4ff';
      case 'wardstone': case 'windcairn': case 'spirelight': case 'pylon': case 'hallgate': return '#ffd36a';
      case 'nest': return '#8a6a4a';
      case 'reefwall': return '#d86a78';
      case 'kelp': return '#2a8a5a';
      case 'coral': case 'anemone': return '#e0708a';
      case 'tidebell': return '#ffd36a';
      case 'clam': case 'sunkencolumn': return '#d8d4c4';
      case 'shiprib': case 'anchor': return '#8a6a4a';
      case 'deeprock': case 'vent': return '#5a6678';
      case 'pearllamp': return '#c8fff0';
      case 'lava': return '#ff6a2a';
      case 'ice': return '#4f93c8';
      case 'water': return theme === 'sunward' ? '#70bcd4' : wyrd ? '#2f6f9a' : '#244f5c';
      case 'oak_tree': case 'apple_tree': case 'willow_tree': return '#285d30';
      case 'birch_tree': return '#538547';
      case 'hawthorn_bush': return '#6a9d51';
      case 'wildflowers': return '#efe49d';
      case 'vale_cottage': case 'watermill': return '#f2d9ad';
      case 'elder_hollow_gate': return '#f8df91';
      case 'stone_bridge': return '#e0d3ac';
      case 'fan_topiary': return '#58c5d0';
      case 'worldheart_trunk': case 'hollow_arch': return '#e9d78c';
      case 'heartwood_vault': return '#ffe0a1';
      case 'heartwood_core': return '#a5e6af';
      case 'lapis_astrolabe': return '#f0d59c';
      case 'lapis_oasis': return '#5dc5c4';
      case 'lapis_date_palm': return '#6ea77a';
      case 'hanging_pod': case 'canopy_market': case 'amber_library': return '#b8d181';
      case 'festival_bloom': return '#f4c65e';
      case 'ribbon_pole': case 'pinwheel': case 'confetti_lantern': return '#ef6998';
      case 'silk_pavilion': case 'painted_stall': return '#f7d36f';
      case 'parade_standard': case 'mask_dais': case 'grand_pavilion_gate': return '#fff0b5';
      case 'jungle_water': case 'jade_pool': return '#48b4bb';
      case 'kapok_tree': case 'strangler_fig': return '#1d6047';
      case 'banana_palm': case 'giant_fern': case 'hanging_vines': return '#68b871';
      case 'orchid_cluster': case 'glow_mushroom': return '#e3a5c2';
      case 'banyan_lodge': case 'boardwalk_stall': case 'root_bridge': return '#c9b075';
      case 'jaguar_totem': case 'rain_crown_temple': return '#f0d889';
      case 'crag': return '#4a4a58';
      case 'pine': return '#1f4a3a';
      case 'beacon': return '#ff9a2e';
      case 'gallows': case 'ribcage': return '#d8d0b8';
      case 'elderash': return '#8a5a2a';
      case 'thicket': return '#6a2f58';
      case 'tree': return wyrd ? '#a8451e' : fen ? '#1b4a2a' : frost ? '#1f5a52' : ember ? '#150f13' : '#1f6b3a';
      case 'spire': return wyrd ? '#d8d8c8' : fen ? '#b8c0b0' : frost ? '#8ccdf0' : '#4b3b5e';
      case 'rock': return wyrd ? '#7a7a80' : fen ? '#6b7a68' : frost ? '#7f93aa' : ember ? '#6a6672' : '#8a93a8';
      case 'rampart': return '#6f7078';
      case 'eye_wall': return '#527c8e';
      case 'eye_lamp': case 'eye_lens': case 'eye_rune': return '#a3eee5';
      case 'span_wall': return '#526894';
      case 'span_brazier': case 'span_prism': case 'span_obelisk': case 'span_arch': return '#9bf0ff';
      case 'elder_wall': return '#6e6043';
      case 'elder_lantern': case 'elder_crown': case 'elder_seed': return '#c9e29e';
      case 'vaultwall': return '#5d6482';
      case 'pillar': return '#a3abc0';
      case 'brazier': return '#ff9a3a';
      case 'torch': return '#ffcf6a';
      case 'sarcophagus': return '#6a7088';
      case 'bones': return '#d6cfb6';
      case 'tower': return '#3f6a8a';
      case 'stall': return '#e0a040';
      case 'aetherhouse': return o.color || '#b9e4dc';
      case 'astrolabe': case 'moonobelisk': case 'glasslamp': return '#f2dfb2';
      case 'nacrehouse': case 'nacrestall': case 'house': case 'chapel': return o.color || '#a08060';
      case 'crystal': case 'obelisk': return '#a4e9e3';
      case 'astraltree': return '#244f64';
      case 'starstone': return '#637994';
      case 'starbloom': return '#d8afe9';
      case 'astralshrub': return '#5eaa91';
      case 'astrolamp': case 'starwell': return '#ffe2a0';
      case 'astralhouse': case 'observatory': return '#94bbc5';
      case 'mirrorwall': return '#e8d9ef';
      case 'sunspire': case 'lens_pillar': return '#ffe3ae';
      case 'glassstone': return '#9b8ca8';
      case 'saltbrush': return '#d8c9c3';
      case 'mooncaps': case 'sporelamp': case 'glowmoss': return '#c4f4af';
      case 'gloomstalk': case 'sporefern': return '#618f76';
      case 'moonstone': case 'moonwell': case 'moonaltar': return '#b5cbb8';
      case 'moonmirror': return '#f8e8ad';
      case 'moonlily': return '#c6e4d6';
      case 'moonreed': return '#9af2d7';
      case 'lamphouse': return '#97b9a2';
      case 'shade_tent': return '#a5798f';
      case 'bush': return fen ? '#3f6a3a' : frost ? '#4a8a78' : ember ? '#3a2a30' : '#2f8a45';
      default: return '#8a7a62';
    }
  }
  const FEATURE = new Set(['lava', 'ice', 'water', 'thicket']);
  const RADIUS = { crag: 1.3, pine: 1.4, elderash: 3.5, lava: 1.5, water: 1.1, ice: 1.15, thicket: 1.15, tree: 1.4, bush: .8, rock: .9, spire: 1, lamp: .5, flowers: .5 };
  function paint(index, px) {
    const key = `${index}:${px}`; if (cache.has(key)) return cache.get(key);
    const z = zones[index], k = px / z.size, c = document.createElement('canvas'); c.width = c.height = px;
    const g = c.getContext('2d');
    g.fillStyle = GROUND[z.theme]; g.fillRect(0, 0, px, px);
    if(z.theme==='yearwheel'){const half=px/2;for(const [x,y,c] of [[0,0,'#c3dfeb'],[half,0,'#c88055'],[0,half,'#8acb83'],[half,half,'#ecc274']]){g.fillStyle=c;g.fillRect(x,y,half,half);}g.fillStyle='#f5e4b4';g.beginPath();g.arc(half,half,px*.028,0,6.283);g.fill();}
    let seed = 7 + index * 131; const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
    for (let n = 0; n < 70; n++) { g.fillStyle = rnd() < .5 ? 'rgba(255,255,255,.05)' : 'rgba(0,0,0,.07)'; g.beginPath(); g.arc(rnd() * px, rnd() * px, (4 + rnd() * 9) * k, 0, 6.283); g.fill(); }
    g.lineCap = g.lineJoin = 'round'; g.strokeStyle = g.fillStyle = DIRT[z.theme]; g.lineWidth = 2.8 * k;
    for (const p of z.paths || []) { g.beginPath(); p.forEach(([x, y], i) => i ? g.lineTo(x * k, y * k) : g.moveTo(x * k, y * k)); g.stroke(); }
    if (z.theme === 'meadow') { g.beginPath(); g.arc(36 * k, 36 * k, 3.5 * k, 0, 6.283); g.fill(); }
    (z.sky || []).forEach((row, y) => { for (let x = 0; x < z.size; x++) { const c = row[x]; if (c && c !== ' ') { g.fillStyle = c === '=' ? '#f0c8f4' : '#8ad4b8'; g.fillRect(x * k, y * k, k + .6, k + .6); } } });   // floating islands and their bridges
    (z.moonwellFloor || []).forEach((row,y)=>{for(let x=0;x<z.size;x++){const c=row[x];if(c&&c!==' '){g.fillStyle=c==='='?'#f8e8ad':'#a8d5cf';g.fillRect(x*k,y*k,k+.6,k+.6);}}});
    (z.forgeFloor || z.blackhourFloor || z.longshipFloor || []).forEach((row,y)=>{for(let x=0;x<z.size;x++)if(row[x]==='='){g.fillStyle=z.forgeFloor?'#b4a09c':z.blackhourFloor?'#87749b':Math.abs(x+.5-64)<2?'#668c80':'#bf9c71';g.fillRect(x*k,y*k,k+.6,k+.6);}});
    for (const [x0, y0, x1, y1] of (z.forgeFloor || z.longshipFloor || z.blackhourFloor ? [] : z.rooms || [])) { g.fillStyle = '#2f3347'; g.fillRect(x0 * k, y0 * k, (x1 - x0) * k, (y1 - y0) * k); }   // a dungeon's floor
    const PAVE = z.theme === 'asterion' ? {1:'#9ec6d9',2:'#edd9ad',3:'#c99bbf'} : { 1: '#b6a98c', 2: '#ece2c8', 3: '#b8765a' };
    for (const r of z.roads || []) {
      g.fillStyle = g.strokeStyle = PAVE[r.t] || '#b6a98c';
      if (r.x0 !== undefined) g.fillRect(r.x0 * k, r.y0 * k, (r.x1 - r.x0) * k, (r.y1 - r.y0) * k);
      else if (r.r0 !== undefined) { g.lineWidth = (r.r1 - r.r0) * k; g.beginPath(); g.arc(r.x * k, r.y * k, (r.r0 + r.r1) / 2 * k, 0, 6.283); g.stroke(); }
      else { g.beginPath(); g.arc(r.x * k, r.y * k, r.r * k, 0, 6.283); g.fill(); }
    }
    if (z.city && z.theme !== 'city' && z.theme !== 'nacre' && z.theme !== 'asterion') for (const t of [z.city, ...(z.camps || [])]) {
      g.fillStyle = { meadow: '#d8cbb0', ember: '#88705d', frost: '#8fa6bd', fen: '#6a5238', wyrd: '#8a6a44', sky: '#cdd2f2', deep: '#4a7a82', astral: '#8fa9b2', prismwaste: '#c5a58d', orrery: '#a58a77', moonspore: '#719b83', stormglass:'#55798a', sunward:'#76ad56', ribbonwild:'#e5a8c5',tanglecrown:'#65ad70',lapiserg:'#d6ad72',yearwheel:'#e9daa9' }[z.theme];
      g.fillRect(t.x0 * k, t.y0 * k, (t.x1 - t.x0) * k, (t.y1 - t.y0) * k);
    }
    const objects = (z.objects || []).filter(o => o.kind !== 'post' && o.kind !== 'void');
    for (const pass of [0, 1]) for (const o of objects) {
      if (FEATURE.has(o.kind) !== (pass === 0)) continue;
      g.fillStyle = z.theme==='yearwheel' ? (o.kind.includes('gate')?'#ffe9a6':o.kind.includes('lodge')?'#e5c3a2':o.kind.includes('pool')?'#75c8d0':['#84bd79','#e7a950','#bf6e45','#b5dce5'][(o.x<200?(o.y<200?3:0):(o.y<200?2:1))]) : objectColour(o, z.theme);
      if (o.width) { g.fillRect((o.x - o.width / 2) * k, (o.y - o.depth / 2) * k, Math.max(1, o.width * k), Math.max(1, o.depth * k)); continue; }
      if (o.kind === 'grandfountain' || o.kind === 'fountain' || o.kind === 'meetingstone') { g.fillStyle = o.kind === 'meetingstone' ? '#59d9ff' : '#58a8d8'; g.beginPath(); g.arc(o.x * k, o.y * k, Math.max(2, (o.r || 1) * k), 0, 6.283); g.fill(); continue; }
      g.beginPath(); g.arc(o.x * k, o.y * k, Math.max(1, (o.kind === 'water' || o.kind === 'ew_lava' ? o.r : RADIUS[o.kind] || .8) * k), 0, 6.283); g.fill();
    }
    if (z.city && z.theme !== 'city' && z.theme !== 'nacre' && z.theme !== 'asterion') for (const t of [z.city, ...(z.camps || [])]) { g.fillStyle = '#ffe9a0'; g.beginPath(); g.arc(t.plaza.x * k, t.plaza.y * k, Math.max(2, 2.4 * k), 0, 6.283); g.fill(); }
    for (const n of z.npcs || []) { g.fillStyle = '#f5d477'; g.beginPath(); g.arc(n.x * k, n.y * k, Math.max(1, .55 * k), 0, 6.283); g.fill(); }
    cache.set(key, c); return c;
  }
  function copy(canvas, source) { canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height); canvas.getContext('2d').drawImage(source, 0, 0, canvas.width, canvas.height); }

  // ---------- world view ----------
  const rangeText = z => z.range ? (z.range[0] === z.range[1] ? `Lv ${z.range[0]}` : `Lv ${z.range[0]}–${z.range[1]}`) + (z.players ? ` · ${z.players} players` : '') : 'Safe city';
  const shortName = name => {
    const words = name.replace(/^The /, '').replace(/ — .*/, '').split(/\s+/);
    const choice = words.at(-1);
    return choice.length <= 10 ? choice : choice.slice(0, 8) + '…';
  };
  const edgePoint = (a, b) => {                                     // where the road from a's centre to b's centre leaves a's round ground
    const ax = a.x + a.s / 2, ay = a.y + a.s * tileY / 2;
    const dx = b.x + b.s / 2 - ax, dy = b.y + b.s * tileY / 2 - ay;
    const t = (a.s / 2 + .2) / (Math.hypot(dx, dy) || 1);
    return [ax + dx * t, ay + dy * t];
  };
  function svgNode(tag, attrs) { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); return n; }
  function islandPoints(place, index, pad = 0, vertical = tileY) {
    const { x, y, s } = place, cx = x + s / 2, cy = y + s * vertical / 2, points = [];
    for (let n = 0; n < 16; n++) {
      const angle = n / 16 * Math.PI * 2, wobble = 1 + .075 * Math.sin(index * 7 + n * 4.7) + .055 * Math.cos(index * 3 + n * 2.9);
      points.push([cx + Math.cos(angle) * (s / 2 + pad) * wobble,
                   cy + Math.sin(angle) * (s / 2 + pad) * vertical * wobble]);
    }
    return points;
  }
  const pointPath = points => 'M ' + points.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join(' L ') + ' Z';
  function islandClip(index) {
    const square = { x: 0, y: 0, s: 100 };
    return 'polygon(' + islandPoints(square, index, 0, 1).map(([x, y]) => `${x.toFixed(1)}% ${y.toFixed(1)}%`).join(',') + ')';
  }
  // ---- the world sheet: continents, coasts, scenery and names ----
  // The gate graph is a tree, so the sheet lays it out as one: a west continent (Greenmeadow to the Wyrdwood), the Stormrift sea with
  // its three island zones (Bifrost Reach, Ran's Deep, Nacrehold) and a long east continent (Astralhollow to the Yearwheel). Zones that
  // are joined by land touch through an isthmus; the four crossings of the Stormrift are sea lanes.
  const SEA_LANES = new Set(['6-7', '7-8', '8-9', '9-13']);
  const NAMES = { 'Greenmeadow': 'Greenmeadow', 'Emberfall Crags': 'Emberfall', 'Rimeveil Glacier': 'Rimeveil', 'Gloamfen': 'Gloamfen', 'Skaldholm': 'Skaldholm', 'The Undervault': 'Undervault', 'Wyrdwood': 'Wyrdwood',
    'Bifrost Reach': 'Bifrost Reach', 'Rán\'s Deep': 'Rán\'s Deep', 'Nacrehold': 'Nacrehold', 'The Drowned Cathedral — Flooded Cloister': 'Cloister', 'The Drowned Cathedral — Coral Reliquary': 'Reliquary', 'The Drowned Cathedral — Grand Nave': 'Grand Nave',
    'Astralhollow': 'Astralhollow', 'The Prismwaste': 'Prismwaste', 'The Obsidian Orrery': 'Orrery', 'The Moonspore Canopy': 'Moonspore', 'Asterion': 'Asterion', 'The Moonwell': 'Moonwell', 'The Stormglass Shore': 'Stormglass', 'Sunward Vale': 'Sunward Vale',
    'The Ribbonwild': 'Ribbonwild', 'The Tanglecrown': 'Tanglecrown', 'Veyrroot Canopy': 'Veyrroot', 'Veyrroot Heartwood': 'Heartwood', 'The Lapis Erg': 'Lapis Erg', 'Frostwake Shelf': 'Frostwake', 'The Cairnspine': 'Cairnspine', 'The Yearwheel': 'Yearwheel',
    'The Eye Below': 'Eye Below', 'The Elder Hollow': 'Elder Hollow', 'The Thousandfold Pavilion': 'Pavilion', 'Temple of the Rain Crown': 'Rain Crown', 'The Seed Vault': 'Seed Vault', 'The Sunken Astrolabe': 'Astrolabe', 'The Thunderheart Gate': 'Thunderheart',
    'The Blooming Labyrinth': 'Blooming', 'The Solar Crucible': 'Crucible', 'The Amber Archive': 'Amber Archive', 'The Silent Solstice': 'Solstice' };
  const labelName = z => NAMES[z.name] || shortName(z.name);
  // Names of the regions, set in the sea or across a continent (stage units).
  const REGIONS = [{ text: 'HEARTHLANDS', area: [1, 1, 44, 99], near: [16, 97] }, { text: 'THE STORMRIFT', area: [30, 1, 100, 99], near: [56, 26] }, { text: 'STARFALL REACHES', area: [70, 1, 159, 99], near: [112, 3] }];
  const DECOR = { ember: 'peak', cairnspine: 'peak', frost: 'snow', frostwake: 'snow', wyrd: 'pine', fen: 'reed', meadow: 'tree', sunward: 'tree', tanglecrown: 'palm', worldtree: 'palm', heartwood: 'palm', moonspore: 'shroom',
    lapiserg: 'dune', prismwaste: 'crystal', astral: 'crystal', ribbonwild: 'flag', yearwheel: 'tree', sky: 'cloud', deep: 'coral', nacre: 'coral', asterion: 'spire', orrery: 'spire', city: 'tree' };
  // One small scenery picture at (x, y), `u` stage units across, drawn into `g`.
  function sceneryIcon(g, kind, x, y, u, rnd) {
    const add = (tag, attrs) => g.append(svgNode(tag, attrs));
    const tri = (cx, base, w, h, fill) => add('path', { d: `M ${cx - w} ${base} L ${cx} ${base - h} L ${cx + w} ${base} Z`, fill });
    switch (kind) {
      case 'peak': case 'snow':
        tri(x - u * .45, y + u * .2, u * .55, u * .85, kind === 'peak' ? '#6a5750' : '#8d9db0'); tri(x + u * .2, y + u * .35, u * .7, u * 1.1, kind === 'peak' ? '#8a7467' : '#b9c9d8');
        add('path', { d: `M ${x + u * .2 - u * .22} ${y + u * .35 - u * .82} L ${x + u * .2} ${y + u * .35 - u * 1.1} L ${x + u * .2 + u * .22} ${y + u * .35 - u * .82} Z`, fill: kind === 'peak' ? '#ff9a4a' : '#ffffff' }); break;
      case 'pine': tri(x, y + u * .5, u * .42, u * .9, '#1e4a30'); tri(x, y + u * .1, u * .34, u * .7, '#2d6b43'); break;
      case 'tree': add('rect', { x: x - u * .07, y: y + u * .1, width: u * .14, height: u * .35, fill: '#5a3d26' }); add('circle', { cx: x, cy: y - u * .1, r: u * .42, fill: '#2f7a3c' }); add('circle', { cx: x - u * .12, cy: y - u * .2, r: u * .2, fill: '#4aa052' }); break;
      case 'palm': add('path', { d: `M ${x} ${y + u * .5} Q ${x + u * .12} ${y} ${x} ${y - u * .4}`, stroke: '#6a4a2a', 'stroke-width': u * .12, fill: 'none' });
        for (const a of [-2.5, -1.7, -.9, -.2]) add('path', { d: `M ${x} ${y - u * .4} q ${Math.cos(a) * u * .45} ${Math.sin(a) * u * .3 - u * .1} ${Math.cos(a) * u * .75} ${Math.sin(a) * u * .1 + u * .3}`, stroke: '#2f9a58', 'stroke-width': u * .13, fill: 'none', 'stroke-linecap': 'round' }); break;
      case 'reed': for (const dx of [-.3, 0, .3]) add('path', { d: `M ${x + dx * u} ${y + u * .4} q ${dx * u * .3} ${-u * .5} ${dx * u * .1} ${-u * .8}`, stroke: '#7a9a5a', 'stroke-width': u * .08, fill: 'none' }); break;
      case 'dune': add('path', { d: `M ${x - u * .7} ${y + u * .3} Q ${x - u * .2} ${y - u * .45} ${x + u * .25} ${y + u * .05} Q ${x + u * .5} ${y + u * .25} ${x + u * .75} ${y + u * .3} Z`, fill: '#e3bd80' }); break;
      case 'crystal': add('path', { d: `M ${x - u * .2} ${y + u * .4} L ${x - u * .3} ${y - u * .1} L ${x} ${y - u * .7} L ${x + u * .3} ${y - u * .1} L ${x + u * .2} ${y + u * .4} Z`, fill: '#c9b4ff' }); add('path', { d: `M ${x} ${y - u * .7} L ${x + u * .3} ${y - u * .1} L ${x + u * .2} ${y + u * .4} L ${x} ${y + u * .3} Z`, fill: '#9a84e0' }); break;
      case 'shroom': add('rect', { x: x - u * .08, y: y, width: u * .16, height: u * .4, fill: '#e8e4d0' }); add('path', { d: `M ${x - u * .42} ${y + u * .05} Q ${x} ${y - u * .7} ${x + u * .42} ${y + u * .05} Z`, fill: '#8fe8b8' }); break;
      case 'flag': add('path', { d: `M ${x} ${y + u * .45} L ${x} ${y - u * .5}`, stroke: '#ffe9a6', 'stroke-width': u * .08 }); add('path', { d: `M ${x} ${y - u * .5} L ${x + u * .55} ${y - u * .32} L ${x} ${y - u * .12} Z`, fill: '#ef6998' }); break;
      case 'cloud': add('path', { d: `M ${x - u * .5} ${y + u * .2} a ${u * .3} ${u * .3} 0 0 1 ${u * .15} ${-u * .45} a ${u * .4} ${u * .4} 0 0 1 ${u * .65} ${u * .1} a ${u * .25} ${u * .25} 0 0 1 ${u * .1} ${u * .35} Z`, fill: '#f0f4ff', 'fill-opacity': .9 }); break;
      case 'coral': add('path', { d: `M ${x} ${y + u * .4} L ${x} ${y - u * .2} M ${x} ${y} L ${x - u * .3} ${y - u * .4} M ${x} ${y - u * .1} L ${x + u * .3} ${y - u * .5}`, stroke: '#e0708a', 'stroke-width': u * .13, 'stroke-linecap': 'round', fill: 'none' }); break;
      case 'spire': add('path', { d: `M ${x - u * .18} ${y + u * .45} L ${x - u * .1} ${y - u * .5} L ${x} ${y - u * .8} L ${x + u * .1} ${y - u * .5} L ${x + u * .18} ${y + u * .45} Z`, fill: '#d9e8ff' }); break;
    }
  }
  function buildWorld() {
    const stage = $('wm-world'); stage.replaceChildren(); tiles = Array(zones.length).fill(null); roadRefs = []; nameNodes = [];
    tileY = stage.clientWidth / stage.clientHeight * STAGE.h / STAGE.w;
    const atlas = svgNode('svg', { viewBox: `0 0 ${STAGE.w} ${STAGE.h}`, preserveAspectRatio: 'none', class: 'wm-atlas', 'aria-hidden': 'true' });
    const defs = svgNode('defs', {});
    const sea = svgNode('pattern', { id: 'wm-sea-lines', width: 8, height: 5, patternUnits: 'userSpaceOnUse' });
    sea.append(svgNode('path', { d: 'M .5 3 Q 2 1.5 3.5 3 T 6.5 3', stroke: '#b5dfdf', 'stroke-opacity': '.13', 'stroke-width': '.16', fill: 'none' }));
    const region = { filterUnits: 'userSpaceOnUse', x: 0, y: 0, width: STAGE.w, height: STAGE.h };
    // Ragged, fractal coastlines: a turbulence field pushes the edge of the land about; the beach is the same shape grown a little.
    const rough = (id, extra = []) => {
      const f = svgNode('filter', { id, ...region, 'color-interpolation-filters': 'sRGB' });
      f.append(svgNode('feTurbulence', { type: 'fractalNoise', baseFrequency: '.07 .09', numOctaves: 3, seed: 11, result: 'n' }),
        svgNode('feDisplacementMap', { in: 'SourceGraphic', in2: 'n', scale: 3.4, xChannelSelector: 'R', yChannelSelector: 'G', result: 'd' }), ...extra);
      return f;
    };
    defs.append(sea, rough('wm-rough'),
      rough('wm-beach', [svgNode('feMorphology', { in: 'd', operator: 'dilate', radius: 1.1 })]),
      rough('wm-shallow', [svgNode('feMorphology', { in: 'd', operator: 'dilate', radius: 1.8, result: 'm' }), svgNode('feGaussianBlur', { in: 'm', stdDeviation: 2.2 })]));
    const soft = svgNode('filter', { id: 'wm-soft', ...region }); soft.append(svgNode('feGaussianBlur', { stdDeviation: 1.5 })); defs.append(soft);
    // The silhouette of all land: a blob under every zone, a rock under every dungeon, and an isthmus along every land link.
    const silhouette = svgNode('g', { id: 'wm-sil' }), landLinks = svgNode('g', { class: 'wm-land-links' });
    const seen = new Set(), roadList = [];
    zones.forEach((z, i) => {
      if (!onWorldSheet(z)) return;
      const c = [z.place.x + z.place.s / 2, z.place.y + z.place.s * tileY / 2];
      silhouette.append(z.players ? svgNode('circle', { cx: c[0], cy: c[1], r: z.place.s / 2 + 1.2 }) : svgNode('path', { d: pointPath(islandPoints(z.place, i, z.place.s * .08)) }));
    });
    zones.forEach((z, i) => z.portals.forEach(p => {
      const pair = [i, p.to].sort((a, b) => a - b).join('-'); if (!onWorldSheet(z) || seen.has(pair) || !onWorldSheet(zones[p.to])) return; seen.add(pair);
      const a = z.place, b = zones[p.to].place, sea = SEA_LANES.has(pair);
      const link = svgNode('g', { 'data-link': pair });
      if (!sea) {
        const w = z.players || zones[p.to].players ? 2.2 : Math.min(a.s, b.s) * .5;
        link.append(svgNode('path', { d: `M ${a.x + a.s / 2} ${a.y + a.s * tileY / 2} L ${b.x + b.s / 2} ${b.y + b.s * tileY / 2}`, fill: 'none', 'stroke-width': w, 'stroke-linecap': 'round' }));
        landLinks.append(link);
      }
      roadList.push({ z, i, p, pair, sea });
    }));
    silhouette.append(landLinks); defs.append(silhouette);
    const mask = svgNode('mask', { id: 'wm-landmask', maskUnits: 'userSpaceOnUse', ...{ x: 0, y: 0, width: STAGE.w, height: STAGE.h } });
    mask.append(svgNode('use', { href: '#wm-sil', fill: '#fff', stroke: '#fff', 'stroke-width': 0, filter: 'url(#wm-rough)' })); defs.append(mask);
    atlas.append(defs, svgNode('rect', { x: 0, y: 0, width: STAGE.w, height: STAGE.h, fill: 'url(#wm-sea-lines)' }));
    const layer = (fill, filter, cls) => svgNode('use', { href: '#wm-sil', fill, stroke: fill, 'stroke-width': 0, filter: `url(#${filter})`, class: cls });
    atlas.append(layer('#7fd0cf', 'wm-shallow', 'wm-shallows'), layer('#ecdcaa', 'wm-beach', 'wm-beach'), layer('#78a85e', 'wm-rough', 'wm-land-base'));
    // Each zone's biome colour is a soft blob over the land, so one terrain melts into the next.
    const land = svgNode('g', { class: 'wm-land-shapes', mask: 'url(#wm-landmask)' }), biomes = svgNode('g', { filter: 'url(#wm-soft)' }), scenery = svgNode('g', { class: 'wm-scenery', mask: 'url(#wm-landmask)' });
    land.append(biomes);
    zones.forEach((z, i) => {
      if (!onWorldSheet(z) || z.players) return;
      biomes.append(svgNode('path', { d: pointPath(islandPoints(z.place, i, z.place.s * .15)), class: 'wm-island', fill: GROUND[z.theme] || '#6f8e73', 'data-zone': i }));
      const kind = DECOR[z.theme]; if (!kind) return;
      const g = svgNode('g', { class: 'wm-decor', 'data-zone': i }), c = [z.place.x + z.place.s / 2, z.place.y + z.place.s * tileY / 2], R = z.place.s / 2;
      let seed = 31 + i * 17; const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
      const toward = z.portals.filter(p => onWorldSheet(zones[p.to])).map(p => { const b = zones[p.to].place; return Math.atan2(b.y + b.s * tileY / 2 - c[1], b.x + b.s / 2 - c[0]); });
      const count = Math.round(R * .75 + 2), size = Math.max(1.5, Math.min(2.6, R * .2));
      for (let k = 0, tries = 0; k < count && tries < 60; tries++) {
        const ang = rnd() * 6.2832; if (toward.some(t => Math.abs(Math.atan2(Math.sin(ang - t), Math.cos(ang - t))) < .5)) continue;
        const rad = R * (1.02 + rnd() * .2); sceneryIcon(g, kind, c[0] + Math.cos(ang) * rad, c[1] + Math.sin(ang) * rad * tileY, size * (.8 + rnd() * .5), rnd); k++;
      }
      scenery.append(g);
    });
    atlas.append(land, scenery);
    const labels = svgNode('g', { class: 'wm-regions' });
    for (const r of REGIONS) { const t = svgNode('text', { x: -50, y: -50, 'text-anchor': 'middle', 'data-region': r.text }); t.textContent = r.text; labels.append(t); }
    atlas.append(labels);
    const compass = svgNode('g', { class: 'wm-compass', transform: 'translate(10 10)' });
    compass.append(svgNode('circle', { r: 4.6 }), svgNode('circle', { r: 3.3 }),
      svgNode('path', { d: 'M 0 -5.7 L 1.1 -1.1 L 5.7 0 L 1.1 1.1 L 0 5.7 L -1.1 1.1 L -5.7 0 L -1.1 -1.1 Z' }),
      svgNode('path', { d: 'M 0 -4.7 L -1.1 -1.1 L 0 0 Z M 4.7 0 L 1.1 -1.1 L 0 0 Z M 0 4.7 L 1.1 1.1 L 0 0 Z M -4.7 0 L -1.1 1.1 L 0 0 Z', class: 'wm-compass-shadow' }));
    const north = svgNode('text', { x: 0, y: -6.6, 'text-anchor': 'middle' }); north.textContent = 'N'; compass.append(north);
    atlas.append(compass);
    const roads = svgNode('svg', { viewBox: `0 0 ${STAGE.w} ${STAGE.h}`, preserveAspectRatio: 'none', class: 'wm-roads', 'aria-hidden': 'true' });
    for (const { z, i, p, pair, sea } of roadList) {
      const a = z.place, b = zones[p.to].place, [x1, y1] = edgePoint(a, b), [x2, y2] = edgePoint(b, a);
      const road = svgNode('g', { 'data-road': pair, class: sea ? 'wm-sea-lane' : '' });
      const back = zones[p.to].portals.find(q => q.to === i), terrain = svgNode('g', {});
      const len = Math.hypot(x2 - x1, y2 - y1) || 1, bend = Math.min(2.6, len * .14) * (pair.length % 2 ? 1 : -1);
      const d = `M ${x1.toFixed(2)} ${y1.toFixed(2)} Q ${((x1 + x2) / 2 - (y2 - y1) / len * bend).toFixed(2)} ${((y1 + y2) / 2 + (x2 - x1) / len * bend).toFixed(2)} ${x2.toFixed(2)} ${y2.toFixed(2)}`;
      roadRefs.push({ node: road, terrain, pair, shown: () => known(i, p.x, p.y) || (back && known(p.to, back.x, back.y)) });
      road.append(svgNode('title', {}), svgNode('path', { d, class: 'wm-road-under', fill: 'none' }), svgNode('path', { d, class: 'wm-road', fill: 'none' }),
        svgNode('circle', { cx: x1, cy: y1, r: .75, class: 'wm-gate-dot' }), svgNode('circle', { cx: x2, cy: y2, r: .75, class: 'wm-gate-dot' }));
      road.firstChild.textContent = `${p.name[0].toUpperCase()}${p.name.slice(1)} joins ${z.name} and ${zones[p.to].name}`;
      roads.append(road);
    }
    const baked = el('canvas', '', 'wm-sea'); baked.width = STAGE.w * 10; baked.height = STAGE.h * 10; baked.hidden = true; baked.setAttribute('aria-hidden', 'true'); atlas.style.display = 'none';
    stage.append(baked, atlas, roads);
    zones.forEach((z, i) => {
      if (!onWorldSheet(z)) return;
      const { x, y, s } = z.place, tile = el('button', '', 'wm-tile'); tile.type = 'button'; tile.dataset.zone = String(i); tile.dataset.theme = z.theme;
      tile.dataset.size = String(s);
      Object.assign(tile.style, { left: `${x / STAGE.w * 100}%`, top: `${y / STAGE.h * 100}%`, width: `${s / STAGE.w * 100}%`, aspectRatio: '1' });
      tile.setAttribute('aria-label', `${z.name}, ${z.range ? `levels ${z.range[0]} to ${z.range[1]}` : 'a safe city'}. Open its map`);
      tile.dataset.branch = z.players ? 'dungeon' : ['city','nacre','asterion','worldtree','heartwood'].includes(z.theme) ? 'city' : 'wild';
      if (!z.players) tile.style.clipPath = islandClip(i); else tile.title = z.name;
      const canvas = el('canvas'); canvas.width = canvas.height = 220; copy(canvas, paint(i, 220));
      const fog = el('canvas', '', 'wm-tile-fog'); fog.width = fog.height = 220; fog.setAttribute('aria-hidden', 'true');
      const label = el('span', '', 'wm-tile-label'); label.append(el('b', z.name), el('small', rangeText(z)));
      label.querySelector('b').dataset.short = s < 8 ? String(i) : shortName(z.name);
      const you = el('i', '', 'wm-you'); you.hidden = true; you.title = 'You are here';
      tile.append(canvas, fog, label, you);
      if (travelMasters(z).length) {
        const badge = el('span', '✦', 'wm-travel-badge'); badge.setAttribute('aria-hidden', 'true');
        badge.title = travelMasters(z).map(n => n.name).join(', ');
        tile.append(badge);
      }
      tile.addEventListener('click', () => zoomTo(i, tile));
      stage.append(tile); tiles[i] = tile;
    });
    // Names hang beside their zone, on whichever side is free (measured, so they never sit on another zone or each other).
    const names = zones.map((z, i) => {
      if (!onWorldSheet(z)) return null;
      const n = el('span', '', 'wm-name'); n.dataset.zone = String(i); n.dataset.kind = z.players ? 'dungeon' : 'zone'; n.setAttribute('aria-hidden', 'true');
      n.append(el('b', labelName(z)), el('small', ''));
      stage.append(n); return n;
    });
    stage.append(el('div', 'Valhalla', 'wm-sheet-title'));
    nameNodes = names; refreshFog();
  }
  // The atlas is live SVG (ragged coasts come from filters), but filters are costly to redraw, so the sheet is baked once into a
  // canvas and the SVG stays in the DOM, undrawn, as the structure the tests and tools read. It is baked again when the fog changes.
  const ATLAS_CSS = '.wm-regions text{fill:#fff3cf;fill-opacity:.42;stroke:#0b2a3a;stroke-opacity:.35;stroke-width:.15;font-weight:700;font-family:Georgia,serif;letter-spacing:.5px}' +
    '.wm-compass{fill:#eedbad;stroke:#0f3447;stroke-width:.3;opacity:.78}.wm-compass circle{fill:none;stroke:#eedbad;stroke-width:.25}.wm-compass .wm-compass-shadow{fill:#51828d}.wm-compass text{stroke:none;fill:#f6e7bd;font:bold 2.3px Georgia,serif}';
  let bakeToken = 0;
  function bakeAtlas() {
    const stage = $('wm-world'), svg = stage.querySelector('.wm-atlas'), canvas = stage.querySelector('.wm-sea'); if (!svg || !canvas) return;
    const token = ++bakeToken, clone = svg.cloneNode(true);
    clone.removeAttribute('class'); clone.removeAttribute('style'); clone.setAttribute('xmlns', NS); clone.setAttribute('width', canvas.width); clone.setAttribute('height', canvas.height);
    clone.querySelectorAll('.wm-island[data-fog="full"]').forEach(n => n.setAttribute('fill', '#7f9a82'));
    const style = document.createElementNS(NS, 'style'); style.textContent = ATLAS_CSS; clone.prepend(style);
    const img = new Image();
    img.onload = () => { if (token !== bakeToken) return; const g = canvas.getContext('2d'); g.clearRect(0, 0, canvas.width, canvas.height); g.drawImage(img, 0, 0, canvas.width, canvas.height); canvas.hidden = false; svg.style.display = 'none'; };
    img.onerror = () => { if (token === bakeToken) { canvas.hidden = true; svg.style.display = ''; } };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(clone));
  }
  function placeNames(stage, names) {
    const px = stage.clientWidth / STAGE.w, boxes = [], circles = zones.map((z, i) => onWorldSheet(z) ? { x: z.place.x + z.place.s / 2, y: z.place.y + z.place.s * tileY / 2, r: z.place.s / 2 } : null);
    const hits = (b, c) => { const nx = Math.max(b.x, Math.min(c.x, b.x + b.w)), ny = Math.max(b.y, Math.min(c.y, b.y + b.h)); return Math.hypot(nx - c.x, ny - c.y) < c.r * .94; };
    const clash = (b, q, pad = .3) => b.x < q.x + q.w + pad && q.x < b.x + b.w + pad && b.y < q.y + q.h && q.y < b.y + b.h;
    const order = zones.map((z, i) => i).filter(i => names[i] && names[i].dataset.mute !== 'yes').sort((a, b) => (zones[a].players ? 1 : 0) - (zones[b].players ? 1 : 0));   // zones choose first
    const keep = [{ x: 0, y: 0, w: 22, h: 22 }];                                    // the compass
    for (const i of order) {
      const n = names[i], c = circles[i], w = n.offsetWidth / px, h = n.offsetHeight / px, g = .35;
      const options = [];
      for (const k of [1, 2.6]) options.push({ x: c.x - w / 2, y: c.y + c.r + g * k }, { x: c.x - w / 2, y: c.y - c.r - g * k - h }, { x: c.x + c.r + g * k, y: c.y - h / 2 }, { x: c.x - c.r - g * k - w, y: c.y - h / 2 },
        { x: c.x + c.r * .6 * k, y: c.y + c.r * .75 }, { x: c.x - c.r * .6 * k - w, y: c.y + c.r * .75 }, { x: c.x + c.r * .6 * k, y: c.y - c.r * .75 - h }, { x: c.x - c.r * .6 * k - w, y: c.y - c.r * .75 - h });
      if (!zones[i].players) options.push({ x: c.x - w / 2, y: c.y + c.r * .42 }, { x: c.x - w / 2, y: c.y - h / 2 });   // last resorts: on the zone's own ground
      let best = null;
      options.forEach((o, rank) => {
        const b = { x: o.x, y: o.y, w, h };
        let cost = rank * .15 + (rank >= options.length - 2 && !zones[i].players ? 4 : 0);
        if (b.x < .6 || b.y < .4 || b.x + w > STAGE.w - .6 || b.y + h > STAGE.h - .4) cost += 50;
        circles.forEach((other, j) => { if (other && j !== i && hits(b, other)) cost += 10; });
        for (const q of boxes) if (clash(b, q)) cost += 12;
        for (const q of keep) if (clash(b, q, 0)) cost += 6;
        if (!best || cost < best.cost) best = { cost, b };
      });
      n.hidden = zones[i].players && best.cost >= 10;            // a dungeon name with no room appears when its tile is hovered or focused
      if (!n.hidden) boxes.push(best.b);
      Object.assign(n.style, { left: `${best.b.x / STAGE.w * 100}%`, top: `${best.b.y / STAGE.h * 100}%` });
    }
    // Region names sit in the roomiest sea near where each belongs; a name that finds no clear water is shortened, then left off.
    const regions = [];
    for (const r of REGIONS) {
      let best = null, scale = 1;
      for (const k of [1, .78]) {
        const w = r.text.length * 2.2 * k, h = 2.8 * k; best = null;
        for (let y = r.area[1] + 1; y < r.area[3] - 1 - h; y += 1) for (let x = r.area[0] + w / 2 + 1; x < r.area[2] - w / 2 - 1; x += 1) {
          const b = { x: x - w / 2, y, w, h };
          let clear = 99;
          circles.forEach(c => { if (!c) return; const nx = Math.max(b.x, Math.min(c.x, b.x + w)), ny = Math.max(b.y, Math.min(c.y, b.y + h)); clear = Math.min(clear, Math.hypot(nx - c.x, ny - c.y) - c.r); });
          for (const q of [...boxes, ...regions, ...keep]) { const dx = Math.max(q.x - (b.x + w), b.x - (q.x + q.w), 0), dy = Math.max(q.y - (b.y + h), b.y - (q.y + q.h), 0); clear = Math.min(clear, Math.hypot(dx, dy)); }
          const score = Math.min(clear, 2.5) * 10 - Math.hypot(x - r.near[0], y - r.near[1]) * .12;
          if (clear >= 1 && (!best || score > best.score)) best = { score, b };
        }
        scale = k; if (best) break;
      }
      const t = stage.querySelector(`[data-region="${r.text}"]`);
      if (best) regions.push(best.b);
      if (t) { t.setAttribute('visibility', best ? 'visible' : 'hidden'); t.style.fontSize = `${2.4 * scale}px`; if (best) { t.setAttribute('x', best.b.x + best.b.w / 2); t.setAttribute('y', best.b.y + best.b.h * .8); } }
    }
    bakeAtlas();
  }
  // Repaint everything the fog touches on the world sheet. Cheap, and only runs when the saved masks change.
  function refreshFog() {
    fogSignature = JSON.stringify(window.Field.explored);
    roadRefs.forEach(r => r.node.setAttribute('visibility', r.shown() ? 'visible' : 'hidden'));
    zones.forEach((z, i) => {
      const island = $('wm-world').querySelector(`.wm-island[data-zone="${i}"]`);
      if (island) island.dataset.fog = visited(i) ? 'partial' : 'full';
    });
    zones.forEach((z, i) => {
      if (!onWorldSheet(z)) return;
      const tile = tiles[i], g = tile.querySelector('.wm-tile-fog').getContext('2d'), unseen = !visited(i);
      g.clearRect(0, 0, 220, 220); window.Field.fog.paint(g, 220, 220, i);
      tile.disabled = unseen; tile.dataset.fog = unseen ? 'full' : 'partial';
      tile.querySelector('b').textContent = unseen ? 'Unexplored' : z.name;
      tile.querySelector('b').dataset.short = unseen ? '?' : z.place.s < 8 ? String(i) : shortName(z.name);
      tile.querySelector('small').textContent = unseen ? 'Not yet visited' : `${rangeText(z)} · ${charted(i)}/${CELLS} charted`;
      tile.setAttribute('aria-label', unseen ? 'Unexplored zone' : `${z.name}, ${z.range ? `levels ${z.range[0]} to ${z.range[1]}` : 'a safe city'}, ${charted(i)} of ${CELLS} places charted${travelMasters(z).length ? `, ${travelMasters(z).length} travel master${travelMasters(z).length === 1 ? '' : 's'}` : ''}. Open its map`);
      const name = nameNodes[i];
      if (name) {
        name.dataset.fog = unseen ? 'full' : 'partial'; name.dataset.mute = unseen && z.players ? 'yes' : 'no';     // an unvisited dungeon has no name to give yet
        name.querySelector('b').textContent = unseen ? 'Unexplored' : labelName(z);
        name.querySelector('small').textContent = unseen || z.players ? '' : rangeText(z);
      }
      for (const decor of $('wm-world').querySelectorAll(`.wm-decor[data-zone="${i}"]`)) decor.setAttribute('visibility', unseen ? 'hidden' : 'visible');
    });
    if (nameNodes.length) placeNames($('wm-world'), nameNodes);
  }

  // ---------- zone view ----------
  function drawDots(z) {
    const canvas = $('wm-dots'), g = canvas.getContext('2d'), k = canvas.width / z.size;
    g.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of z.slimes || []) {
      if (!known(current, s.x, s.y)) continue;
      const [, , col] = kindInfo(s.kind), dim = highlight && highlight !== s.kind;
      g.globalAlpha = dim ? .18 : 1; g.fillStyle = col; g.strokeStyle = '#10141c'; g.lineWidth = highlight === s.kind ? 3 : 1.5;
      g.beginPath(); g.arc(s.x * k, s.y * k, (highlight === s.kind ? 1.3 : .95) * k, 0, 6.283); g.fill(); g.stroke();
    }
    g.globalAlpha = 1;
  }
  const pos = (z, x, y) => ({ left: `${x / z.size * 100}%`, top: `${y / z.size * 100}%` });
  // On the world sheet a zone is a round tile, so a hero standing in a corner of a square zone is drawn at the rim, not beyond it.
  const youPos = (z, x, y) => {
    let dx = x / z.size - .5, dy = y / z.size - .5; const d = Math.hypot(dx, dy);
    if (d > .44) { dx *= .44 / d; dy *= .44 / d; }
    return { left: `${(.5 + dx) * 100}%`, top: `${(.5 + dy) * 100}%` };
  };
  function renderZone(index) {
    const z = zones[index]; current = index;
    routePaint(index);
    copy($('wm-ground'), paint(index, 768)); highlight = null; drawDots(z);
    const fg = $('wm-fog').getContext('2d'); fg.clearRect(0, 0, 768, 768); window.Field.fog.paint(fg, 768, 768, index);
    const markers = $('wm-markers'); markers.replaceChildren();
    for (const p of z.portals) {
      const dest = zones[p.to]; if (!dest || !known(index, p.x, p.y)) continue;
      const gate = el('button', '', 'wm-gate'); gate.type = 'button'; gate.dataset.portal = p.id; gate.dataset.to = String(p.to); gate.style.setProperty('--glow', PORTAL[dest.theme]);
      Object.assign(gate.style, pos(z, p.x, p.y));
      gate.classList.toggle('low', p.y / z.size > .85); gate.classList.toggle('right', p.x / z.size > .72); gate.classList.toggle('high', p.y / z.size < .08);
      const near = z.portals.find(o => o !== p && known(index, o.x, o.y) && Math.hypot(o.x - p.x, o.y - p.y) < z.size * .14);   // close gates put their labels on opposite sides
      if (near) gate.classList.add(p.x < near.x ? 'west' : 'east');
      const away = visited(p.to);
      gate.append(el('span', away ? `to ${dest.name}` : 'to unexplored lands', 'wm-gate-label'));
      gate.setAttribute('aria-label', away ? `${p.name}, leads to ${dest.name}. Open its map` : `${p.name}, leads to unexplored lands`);
      if (!away) { gate.disabled = true; gate.dataset.unexplored = 'true'; }
      gate.addEventListener('click', () => { highlight = null; renderZone(p.to); setView('zone'); });
      markers.append(gate);
    }
    for (const o of z.objects || []) {
      const name = SEALED[o.kind]; if (!name || !known(index, o.x, o.y)) continue;
      const seal = el('span', `◆ ${name} · sealed`, 'wm-sealed');
      seal.setAttribute('role', 'img'); seal.setAttribute('aria-label', `${name}, sealed dungeon entrance`);
      Object.assign(seal.style, pos(z, o.x, o.y)); markers.append(seal);
    }
    for (const c of [z.city, ...(z.camps || [])].filter(Boolean)) if (known(index, c.plaza.x, c.plaza.y)) {
      const hub = el('span', c.name === z.name ? 'City centre' : c.name, 'wm-hub'); hub.dataset.hub = 'true';
      Object.assign(hub.style, pos(z, c.plaza.x, c.plaza.y)); markers.append(hub);
    }
    for (const n of travelMasters(z)) {
      const marker = el('span', '', 'wm-travel'); marker.dataset.npc = n.id;
      marker.setAttribute('role', 'img'); marker.setAttribute('aria-label', `${n.name}, travel master at ${n.travelStop}`);
      marker.append(el('i', '✦'), el('b', 'Travel Master'));
      Object.assign(marker.style, pos(z, n.x, n.y)); markers.append(marker);
    }
    const me = el('span', '', 'wm-me'); me.append(el('i'), el('b', 'You')); me.hidden = true; me.dataset.me = 'true'; markers.append(me);
    markers.append(el('div', '', 'wm-party'));
    side(z); tick();
  }
  function side(z) {
    const box = $('wm-side'); box.replaceChildren();
    box.append(el('h4', z.name, 'wm-side-name'), el('p', z.tagline || BLURB[z.theme] || '', 'wm-side-blurb'));
    const facts = el('ul', '', 'wm-facts');
    facts.append(el('li', z.range ? (z.players ? `Dungeon for ${z.players} players of level ${z.range[0]}` : `Recommended levels ${z.range[0]}–${z.range[1]}`) : 'No enemies inside the walls'));
    facts.append(el('li', `Charted ${charted(current)} of ${CELLS} places`, 'wm-charted'));
    const path = route(window.Field.zone || 0, current);
    facts.append(el('li', path.length === 1 ? 'You are here' : path.length ? `Route: ${path.map(i => zones[i].name).join(' → ')}` : 'No charted portal route yet', 'wm-route-text'));
    for (const c of [z.city, ...(z.camps || [])].filter(Boolean)) if (known(current, c.plaza.x, c.plaza.y)) facts.append(el('li', `${c.name}: sanctuary${z.camps?.length ? '' : `, ${(z.quests || []).length} quest${(z.quests || []).length === 1 ? '' : 's'}`}`));
    if (z.camps?.length) facts.append(el('li', `${(z.quests || []).length} quests across ${1 + z.camps.length} hubs`));
    box.append(facts);
    if (travelMasters(z).length) {
      box.append(el('h5', 'Travel Masters ✦', 'wm-side-title'));
      const list = el('ul', '', 'wm-travel-list');
      for (const n of travelMasters(z)) list.append(el('li', `${n.name} · ${n.travelStop}`));
      box.append(list);
    }
    const counts = new Map(); for (const s of (z.slimes || []).filter(s => known(current, s.x, s.y))) counts.set(s.kind, (counts.get(s.kind) || 0) + 1);
    if (counts.size) {
      box.append(el('h5', 'Enemies', 'wm-side-title'));
      const list = el('ul', '', 'wm-kinds');
      [...counts].sort((a, b) => kindInfo(a[0])[1] - kindInfo(b[0])[1]).forEach(([kind, n]) => {
        const [name, baseLevel, col] = kindInfo(kind), level = z.cathedralWing ? z.min_level : baseLevel, row = el('li'), b = el('button', '', 'wm-kind'); b.type = 'button'; b.dataset.kind = kind;
        const dot = el('i'); dot.style.background = col;
        b.append(dot, el('span', name), el('small', kind === 'big' ? 'king, rare' : `Lv ${level} · ${n}`));
        const on = () => { highlight = kind; drawDots(z); }, off = () => { highlight = null; drawDots(z); };
        b.addEventListener('pointerenter', on); b.addEventListener('pointerleave', off); b.addEventListener('focus', on); b.addEventListener('blur', off);
        row.append(b); list.append(row);
      });
      box.append(list);
    }
    const seenGates = z.portals.filter(p => zones[p.to] && known(current, p.x, p.y));
    if (seenGates.length) {
      box.append(el('h5', 'Gates', 'wm-side-title'));
      const list = el('ul', '', 'wm-gates');
      seenGates.forEach(p => {
        const row = el('li'), b = el('button', `${p.name[0].toUpperCase()}${p.name.slice(1)} → ${visited(p.to) ? zones[p.to].name : 'unexplored lands'}`, 'window-tool'); b.type = 'button'; b.dataset.to = String(p.to); b.disabled = !visited(p.to);
        b.addEventListener('click', () => { renderZone(p.to); setView('zone'); }); row.append(b); list.append(row);
      });
      box.append(list);
    }
  }

  // ---------- live markers ----------
  function tick() {
    if (!open()) return;
    if (window.Field?.hero?.dead || !window.Online?.connected) { close(); return; }
    if (JSON.stringify(window.Field.explored) !== fogSignature) { refreshFog(); if (view === 'zone') renderZone(current); }
    const hero = window.Field.hero, here = window.Field.zone || 0;
    zones.forEach((z, i) => {
      const you = tiles[i]?.querySelector('.wm-you'); if (!you) return;
      you.hidden = i !== here; if (i === here) Object.assign(you.style, youPos(z, hero.x, hero.y));
      tiles[i].dataset.here = String(i === here); if (nameNodes[i]) nameNodes[i].dataset.here = String(i === here);
    });
    if (view !== 'zone') return;
    const z = zones[current], me = $('wm-markers').querySelector('.wm-me');
    me.hidden = here !== current; if (!me.hidden) Object.assign(me.style, pos(z, hero.x, hero.y));
    const party = $('wm-markers').querySelector('.wm-party');
    const mates = here === current ? (window.Field.remotePlayers || []).filter(r => window.Social?.isPartyMember(r.id) && known(here, r.x, r.y)) : [];
    party.replaceChildren(...mates.map(r => { const m = el('i', '', 'wm-mate'); m.title = r.name || 'Party member'; Object.assign(m.style, pos(z, r.x, r.y)); return m; }));
    $('wm-here').textContent = here === current ? 'You are here' : `You are in ${zones[here].name}`;
  }

  // ---------- views and the zoom ----------
  function setView(next) {
    view = next; $('wm-body').dataset.view = next; $('wm-zone').hidden = next !== 'zone'; $('wm-world').hidden = next !== 'world';
    $('wm-back').hidden = next === 'world';
    $('wm-title-zone').textContent = next === 'zone' ? ` › ${zones[current].name}` : '';
    if (next === 'zone') { const zv = $('wm-zone'); zv.classList.remove('wm-fade'); void zv.offsetWidth; zv.classList.add('wm-fade'); }
    tick();
  }
  function zoomTo(index, tile) {
    if (!visited(index)) return;
    clearTimeout(timer); renderZone(index);
    const world = $('wm-world');
    if (reduced() || !tile) { world.style.transition = world.style.transform = world.style.opacity = world.style.willChange = ''; setView('zone'); return; }
    const st = world.getBoundingClientRect(), r = tile.getBoundingClientRect(), k = st.width / (world.offsetWidth || st.width);   // k: the window's UI scale
    const scale = Math.min(st.width / r.width, st.height / r.height) * .92;
    world.style.transformOrigin = `${(r.left + r.width / 2 - st.left) / k}px ${(r.top + r.height / 2 - st.top) / k}px`;
    world.style.willChange = 'transform, opacity';    // one raster scaled as a texture: the sheet's SVG filters would be redrawn at 8x every frame
    world.style.transition = 'transform .38s ease-in, opacity .38s ease-in';
    world.style.transform = `translate(${(st.left + st.width / 2 - r.left - r.width / 2) / k}px, ${(st.top + st.height / 2 - r.top - r.height / 2) / k}px) scale(${scale})`;
    world.style.opacity = '0';
    $('wm-body').dataset.view = 'zooming';
    timer = setTimeout(() => { world.style.transition = world.style.transform = world.style.opacity = world.style.willChange = ''; setView('zone'); $('wm-back').focus(); }, 390);
  }
  function toWorld() {
    clearTimeout(timer);
    const world = $('wm-world'), tile = tiles[current];
    setView('world');
    if (!reduced() && tile) {
      const st = world.getBoundingClientRect(), r = tile.getBoundingClientRect(), k = st.width / (world.offsetWidth || st.width);
      world.style.transformOrigin = `${(r.left + r.width / 2 - st.left) / k}px ${(r.top + r.height / 2 - st.top) / k}px`;
      world.style.willChange = 'transform, opacity'; world.style.transition = 'none'; world.style.opacity = '0';
      world.style.transform = `translate(${(st.left + st.width / 2 - r.left - r.width / 2) / k}px, ${(st.top + st.height / 2 - r.top - r.height / 2) / k}px) scale(${Math.min(st.width / r.width, st.height / r.height) * .92})`;
      void world.offsetWidth;
      world.style.transition = 'transform .32s ease-out, opacity .32s ease-out'; world.style.transform = 'none'; world.style.opacity = '1';
      timer = setTimeout(() => { world.style.transition = world.style.transform = world.style.opacity = world.style.willChange = ''; }, 340);
    }
    tile?.focus({ preventScroll: true });
  }
  const open = () => !$('worldmap').hidden;
  function canShow() {
    return !$('scene-game').hidden && window.Online?.connected && !window.Field?.hero?.dead && !open() && $('pause').hidden && $('equipment').hidden
      && $('npc-dialogue').hidden && !window.Skillbar?.open && !window.Quests?.open && !window.Social?.open && !window.City?.open && !window.Settings?.active;
  }
  function show() {
    if (!canShow()) return false;
    load(); previousFocus = document.activeElement;
    window.Field.setPaused(true); $('worldmap').hidden = false;
    if (!tiles.length) buildWorld(); else if (JSON.stringify(window.Field.explored) !== fogSignature) refreshFog();
    setView('world');
    const here = window.Field.zone || 0; (tiles[here] || tiles[0]).focus({ preventScroll: true });
    clearInterval(tickTimer); tickTimer = setInterval(tick, 250);
    return true;
  }
  function close(resume = true) {
    if (!open()) return;
    clearTimeout(timer); clearInterval(tickTimer);
    const world = $('wm-world'); world.style.transition = world.style.transform = world.style.opacity = world.style.willChange = '';
    $('worldmap').hidden = true; setView('world');
    if (resume) { window.Field?.setPaused(false); previousFocus?.focus?.({ preventScroll: true }); }
  }
  const back = () => view === 'zone' ? toWorld() : close();

  $('wm-close').addEventListener('click', () => close());
  $('wm-back').addEventListener('click', () => toWorld());
  $('wm-open').addEventListener('click', () => show());
  $('minimap').addEventListener('click', () => show());
  $('worldmap').addEventListener('pointerdown', event => { if (event.target === $('worldmap')) close(); });
  // Registered before game.js, so an open map keeps every key and M never reaches the other panels.
  addEventListener('keydown', event => {
    if ($('scene-game').hidden || event.ctrlKey || event.altKey || event.metaKey) return;
    const key = event.key.toLowerCase(), typing = Keys.typing(event);
    if (open()) {
      if (key === 'tab') {                                          // keep focus inside the panel
        const buttons = [...$('worldmap').querySelectorAll('button:not(:disabled)')].filter(b => b.offsetParent);
        const first = buttons[0], last = buttons.at(-1); event.stopImmediatePropagation();
        if (event.shiftKey && (document.activeElement === first || !buttons.includes(document.activeElement))) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || !buttons.includes(document.activeElement))) { event.preventDefault(); first.focus(); }
        return;
      }
      event.stopImmediatePropagation();
      if (key === 'enter' || key === ' ') return;                   // let the focused button act
      event.preventDefault();
      if (event.repeat) return;
      if (key === 'escape' || key === 'backspace') back();
      else if (Keys.is(event, 'map')) close();
      return;
    }
    if (!Keys.is(event, 'map') || event.repeat || typing) return;   // the other sound key mutes in the field
    if (show()) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);

  window.WorldMap = {
    show, close, get open() { return open(); }, get view() { return view; }, get zone() { return current; },
    reset() { close(false); },
    // For the tests: the layout and kind table the map was written against.
    _layout: LAYOUT, _kinds: KINDS, get _graph() { load(); return graph; }, _route: route,
  };
})();
