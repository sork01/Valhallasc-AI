import { Client } from '/home/serveperry/webserver/www/dybase2/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StdioClientTransport } from '/home/serveperry/webserver/www/dybase2/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, 'test-results/raid-music');
fs.mkdirSync(out, { recursive: true });
const client = new Client({ name: 'valhallasc-raid-music', version: '1' });
await client.connect(new StdioClientTransport({ command: process.execPath,
  args: ['--import', 'tsx', 'mcp/server.mjs'], cwd: '/home/serveperry/webserver/www/dybase2',
  stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' } }));
const call = async (name, args = {}) => {
  console.error('[raid music] ' + name);
  const reply = await client.callTool({ name, arguments: args }, undefined, { timeout: 1200000 });
  if (reply.isError) throw Error(reply.content.map(x => x.text).join('\n'));
  return JSON.parse(reply.content[0].text);
};
const save = (name, data) => fs.writeFileSync(path.join(out, name + '.json'), JSON.stringify(data, null, 2) + '\n');
const specs = [
  { key: 'forge', title: 'Nine Chains Below', bpm: 152, boss: false },
  { key: 'eldmarr', title: 'The Table He Was Promised', bpm: 160, boss: true },
];

function score(boss) {
  const tracks = [
    ['Furnace kick', 'axiom8', 'Hardstyle', -13, 0],
    ['Iron backbeat', 'axiom8', 'Techno', -7, 0],
    ['Vent hats', 'axiom8', 'Chillhop', 2, .12],
    ['Chain strikes', 'dexed', 'TUB BELLS', -18, -.22],
    ['Pressure bass', 'sork303', 'Deep Rubber', -13, 0],
    ['Ratchet signal', 'sork60', 'Hardstyle Stab', -24, -.12],
    ['Heat behind iron', 'sork60', 'Mellow Pad', -29, .1],
    ...(boss ? [['Throne drums', 'dexed', 'LOG DRUM', -12, .23], ['Falling steel', 'axiom8', 'Techno', -6, -.15]] : []),
  ];
  const parts = Object.fromEntries(tracks.map(t => [t[0], []]));
  const grid = ['F#m', 'F#m', 'D', 'D', 'E', 'E', 'F#m', 'F#m'];
  const chords = { 'F#m': [54, 57, 61], D: [50, 54, 57], E: [52, 56, 59] };
  const audit = [];
  const note = (track, pitch, beat, beats, velocity) => parts[track].push({ pitch, beat, beats, velocity });
  for (let bar = 0; bar < 64; bar++) {
    const b = bar * 4, chord = bar === 63 ? 'F#m' : grid[bar % 8], c = chords[chord];
    const intro = bar < 8, breath = bar >= 32 && bar < (boss ? 34 : 36), last = bar === 63;
    const peak = bar >= 40 && bar < 56, fill = bar % 8 === 7 && !last;
    audit.push({ bar: bar + 1, chord, section: last ? 'resolve' : breath ? 'pressure release' : peak ? 'full forge' : intro ? 'ignition' : 'drive' });
    // Four-to-the-floor pulse; bass attacks share its anchors. Intentional short
    // breakdowns keep the pulse on beats one/three, rather than drifting the grid.
    for (let k = 0; k < (last ? 1 : 4); k++) {
      if (!breath || k % 2 === 0) {
        note('Furnace kick', 36, b + k, .15, (k === 0 ? 108 : 100) + (boss ? 4 : 0));
        note('Pressure bass', c[0] - 24, b + k, last ? 3.5 : .3, k === 0 ? 88 : 79);
      }
      if (!last && !intro && !breath && k % 2 === 1) {
        note('Iron backbeat', 38, b + k, .12, boss ? 94 : 82);
        if (peak || boss) note('Iron backbeat', 39, b + k, .1, 58);
      }
      if (!last && (!intro || bar >= 4) && !breath) {
        note('Vent hats', k === 3 && bar % 4 === 3 ? 46 : 42, b + k + .5, .1, 67 + (k % 2) * 8);
        if (peak || boss) note('Vent hats', 42, b + k + .75, .07, 39 + (bar % 3) * 4);
      }
      if (boss && !last && !breath && (k === 0 || k === 2)) {
        note('Throne drums', 48, b + k + .75, .12, peak ? 87 : 71);
        note('Falling steel', 51, b + k + .5, .12, peak ? 65 : 48);
      }
    }
    // Four-note machine call, followed in the next bar by a three-note answer.
    // It lives inside the accompaniment and uses only that bar's chord tones.
    const signal = bar % 2 === 0 ? [[0, 0], [.75, 0], [1.5, 2], [2.5, 1]] : [[.5, 2], [2, 1], [3.25, 0]];
    if (!last) for (const [offset, tone] of signal)
      note('Ratchet signal', c[tone] + 12, b + offset, .16, breath ? 43 : 56);
    else note('Ratchet signal', 66, b, .8, 48);
    // Tight envelope and a rest before every chord boundary prevent harmonic smear.
    for (const pitch of c) note('Heat behind iron', pitch, b, last ? 3.5 : 3.65, breath ? 46 : 38);
    if (bar % 2 === 0 || fill || last) {
      note('Chain strikes', c[2] + 12, b + (last ? 0 : 1.5), last ? 2 : .2, last ? 46 : (peak || boss ? 73 : 61));
      if (boss && !last && !intro) note('Chain strikes', c[0] + 24, b + 3.25, .14, 52);
    }
    if ((fill || bar === 39) && !last) {
      for (const [k, pitch] of [[3, 45], [3.5, 48], [3.75, 50]])
        note('Iron backbeat', pitch, b + k, .1, 65 + (k - 3) * 24);
    }
    // Cymbal/noise punctuations, not a continuous noise wash.
    if ([8, 24, 40, 56, 63].includes(bar)) note('Iron backbeat', 49, b, .3, last ? 42 : 65);
  }
  for (const [track, notes] of Object.entries(parts)) {
    notes.sort((a, b) => a.beat - b.beat);
    for (const n of notes) {
      if (n.beat + n.beats > 256 || n.velocity % 1) throw Error('Invalid note in ' + track);
      if (['Pressure bass', 'Ratchet signal', 'Heat behind iron', 'Chain strikes'].includes(track)) {
        const allowed = chords[audit[Math.floor(n.beat / 4)].chord].map(x => x % 12);
        if (!allowed.includes(n.pitch % 12)) throw Error('Harmony mismatch: ' + track);
      }
    }
  }
  return { tracks, parts, audit };
}

async function compose(spec, project) {
  const A = { project_id: project.project_id }, s = score(spec.boss);
  const current = await call('get_project', A);
  const existing = new Set(current.tracks?.map(t => t.name) || []);
  for (const [name, instrument, preset, volume_db, pan] of s.tracks) {
    if (!existing.has(name)) {
      await call('add_track', { ...A, name, instrument, preset, volume_db, pan });
      if (['Furnace kick', 'Chain strikes'].includes(name)) await call('add_effect', { ...A, track: name, effect: 'sorkcrush', slot: 0 });
    }
    await call('write_notes', { ...A, track: name, start_bar: 1, bars: 64, notes: s.parts[name], name });
  }
  const hold = async (track, parameter, value, effect) => call('automate', { ...A, track, parameter,
    ...(effect ? { effect } : {}), points: [{ bar: 1, value }, { bar: 65, value }] });
  for (const track of ['Furnace kick', 'Chain strikes']) {
    for (const [param, value] of Object.entries({ bits: 16, rate: 32000, drive: track === 'Furnace kick' ? (spec.boss ? 13 : 10) : 6,
      mix: track === 'Furnace kick' ? 80 : 42, output: -7, cutoff: 11000, noise: 0 })) await hold(track, param, value, 'sorkcrush');
  }
  for (const [track, parameters] of [
    ['Ratchet signal', { 'env.attack': 0, 'env.decay': 2.4, 'env.sustain': 2, 'env.release': .8,
      'vcf.reso': 3.5, 'dco.lfo': 0, 'vcf.envPolarity': 0, 'vcf.env': 3, 'vcf.keyFollow': 4 }],
    ['Heat behind iron', { 'env.attack': 1, 'env.release': .5, 'dco.lfo': 0 }],
    ['Pressure bass', { 'delay.mix': 0, 'amp.release': 5, 'amp.decay': 150, 'filter.resonance': 25 }],
  ]) for (const [parameter, value] of Object.entries(parameters)) await hold(track, parameter, value);
  await call('automate', { ...A, track: 'Ratchet signal', parameter: 'vcf.freq', points:
    [{ bar: 1, value: 4.4 }, { bar: 9, value: 5.8 }, { bar: 25, value: 6.2 }, { bar: 33, value: 4.4 },
      { bar: 40, value: 5.2 }, { bar: 41, value: 6.4 }, { bar: 57, value: 5.7 }, { bar: 65, value: 4.4 }] });
  if (!existing.has('Forge warehouse')) await call('add_fx_return', { ...A, name: 'Forge warehouse', effect: 'sorkverb' });
  for (const [param, value] of Object.entries({ mix: 100, decay: spec.boss ? 1.8 : 2.2, lowcut: 350, damping: 62, predelay: 20, width: 110 }))
    await hold('Forge warehouse', param, value, 'sorkverb');
  for (const [track, level_db] of [['Chain strikes', -10], ['Iron backbeat', -19], ['Heat behind iron', -24], ['Ratchet signal', -25]])
    await call('set_send', { ...A, track, fx_return: 'Forge warehouse', level_db });
  for (const [at_bar, name] of [[1, 'Ignition'], [9, 'Nine chains'], [25, 'Pressure'], [33, 'Release valve'], [41, 'Full forge'], [57, 'Return to the furnace']])
    await call('add_marker', { ...A, at_bar, name });
  save(spec.key + '-score', s);
  save(spec.key + '-analysis', await call('analyse_song', A));
  // Read the complete saved note grid back through MCP, including every boundary.
  const views = {};
  for (const [track] of s.tracks) {
    views[track] = [];
    for (let from_bar = 1; from_bar <= 64; from_bar += 8)
      views[track].push(await call('view_track', { ...A, track, from_bar, bars: 8, as: 'notes' }));
  }
  save(spec.key + '-saved-grid', views);
}

async function mix(spec, project) {
  const A = { project_id: project.project_id };
  for (const [track, , , volume_db] of score(spec.boss).tracks) await call('set_mix', { ...A, track, volume_db });
  for (const [parameter, value] of Object.entries({ 'env.decay': 2.4, 'env.sustain': 2, 'env.release': .8,
    'vcf.envPolarity': 0, 'vcf.env': 3, 'vcf.keyFollow': 4 }))
    await call('automate', { ...A, track: 'Ratchet signal', parameter, points: [{ bar: 1, value }, { bar: 65, value }] });
  await call('automate', { ...A, track: 'Ratchet signal', parameter: 'vcf.freq', points:
    [{ bar: 1, value: 4.4 }, { bar: 9, value: 5.8 }, { bar: 25, value: 6.2 }, { bar: 33, value: 4.4 },
      { bar: 40, value: 5.2 }, { bar: 41, value: 6.4 }, { bar: 57, value: 5.7 }, { bar: 65, value: 4.4 }] });
  save(spec.key + '-score', score(spec.boss));
  save(spec.key + '-final-project', await call('get_project', A));
}
try {
  if (process.argv.includes('--inspect')) {
    const catalog = { instruments: await call('list_instruments'), presets: {} };
    for (const instrument of ['axiom8', 'rumble', 'shield', 'dexed', 'sork60', 'sork303'])
      catalog.presets[instrument] = await call('list_presets', { instrument });
    catalog.parameters = {};
    for (const plugin of ['sork60', 'sork303', 'sorkcrush', 'sorkverb'])
      catalog.parameters[plugin] = await call('list_parameters', { plugin });
    fs.writeFileSync(path.join(out, 'catalog.json'), JSON.stringify(catalog, null, 2));
    const schema = await client.listTools();
    fs.writeFileSync(path.join(out, 'tools.json'), JSON.stringify(schema, null, 2));
    console.log('Saved instrument catalog, parameters and tool schemas in ' + out);
  } else {
    for (const spec of specs.filter(s => !process.env.RAID_SONG || s.key === process.env.RAID_SONG)) {
      const state = path.join(out, spec.key + '-project.json');
      let project;
      if (fs.existsSync(state)) {
        project = JSON.parse(fs.readFileSync(state));
        await call('open_project', { project_id: project.project_id });
      } else {
        project = await call('create_project', { name: spec.title, bpm: spec.bpm, time_signature: '4/4', key: 'F# minor' });
        save(spec.key + '-project', project);
      }
      if (process.argv.includes('--compose')) await compose(spec, project);
      if (process.argv.includes('--mix')) await mix(spec, project);
      if (process.argv.includes('--snapshot')) {
        save(spec.key + '-score', score(spec.boss));
        save(spec.key + '-final-project', await call('get_project', { project_id: project.project_id }));
      }
      if (process.argv.includes('--probe')) {
        for (const track of ['Ratchet signal', 'Heat behind iron', 'Furnace kick', 'Iron backbeat', 'Vent hats']) {
          const name = spec.key + '-probe-' + track.replaceAll(' ', '-');
          await call('set_mix', { project_id: project.project_id, track, solo: true });
          try {
            save(name, await call('render_audio', { project_id: project.project_id, from_bar: 9, bars: 1,
              per_track: false, tail_seconds: .5, path: path.join(out, name + '.wav') }));
          } finally { await call('set_mix', { project_id: project.project_id, track, solo: false }); }
        }
      }
      if (process.argv.includes('--render')) {
        const render = await call('render_audio', { project_id: project.project_id,
          path: path.join(out, spec.key + '-render.wav'), per_track: true, tail_seconds: 4 });
        save(spec.key + '-render', render);
        console.log(JSON.stringify({ key: spec.key, project_id: project.project_id,
          lufs: render.integrated_lufs, peak: render.peak_dbfs, problems: render.problems, notes: render.notes }));
      }
    }
  }
} finally { await client.close(); }
