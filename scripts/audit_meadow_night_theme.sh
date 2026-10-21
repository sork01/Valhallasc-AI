#!/bin/sh
# Inspect rendered attacks with short solo exports; always restore the project mix.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
export MEADOW_NIGHT_ROOT="$ROOT"
export MEADOW_NIGHT_AUDIT_DIR="${1:-$ROOT/test-results/meadow-night-hiphop}"
export DYB2_CHROME="${DYB2_CHROME:-/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell}"
cd "$ROOT/../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { readFileSync, writeFileSync } from 'node:fs';
const directory = process.env.MEADOW_NIGHT_AUDIT_DIR;
const score = JSON.parse(readFileSync(`${directory}/score.json`, 'utf8'));
const { project_id } = score;
const client = new Client({ name: 'meadow-night-attack-audit', version: '1' });
await client.connect(new StdioClientTransport({ command: process.execPath,
  args: ['--import', 'tsx', 'mcp/server.mjs'], cwd: process.cwd(), stderr: 'inherit',
  env: { ...process.env, DYB2_MCP_USER: 'codex' } }));
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(JSON.stringify(result.content));
  return JSON.parse(result.content[0].text);
}
const project = await call('open_project');
if (project.project_id !== project_id || project.bars !== score.project.bars ||
  project.tempo !== score.project.tempo || project.meter !== score.project.meter) throw Error('Wrong song');
const results = [];
for (const track of project.tracks.filter(t => t.instrument &&
  (!process.env.AUDIT_TRACKS || process.env.AUDIT_TRACKS.split(',').includes(t.name)))) {
  const path = `${directory}/attack-${track.name.toLowerCase().replaceAll(' ', '-')}.wav`;
  try {
    await call('set_mix', { track: track.name, solo: true });
    const result = await call('render_audio', { from_bar: track.name === 'Night pad' ? 9 : 1,
      bars: 2, path, per_track: false, tail_seconds: .8 });
    results.push({ track: track.name, ...result });
    if (result.problems?.length || result.clipped_samples) throw Error(`Bad solo render: ${track.name}`);
    console.log(track.name, path);
  } finally {
    await call('set_mix', { track: track.name, solo: track.soloed });
  }
}
writeFileSync(`${directory}/attacks.json`, JSON.stringify(results, null, 2));
await client.close();
JS
