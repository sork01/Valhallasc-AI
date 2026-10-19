#!/bin/sh
# Render the active Valhalla scores whose Axiom8 hats switched to Chillhop.
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const scores=[
  // label, project id, owner, game output kind
  ['meadow-night','6c52c389c99ed898','codex','night'],
  ['crags-night','90d3be446ee5a58f','codex','night'],
  ['rime-night','4091d2184af5bf68','codex','night'],
  ['fen-night','631d2ccf54a0ea32','codex','night'],
  ['city-night','32550162e477d9e7','codex','night'],
  ['wyrd-night','a2ac7b7ae8fa8ad8','codex','night'],
  ['sky-night','f8d95f2b7456bee1','codex','night'],
  ['nacre-night','f0c6df77cbbaed17','codex','night'],
  ['astral-night','c452ba1d09acef9f','codex','night'],
  ['prism-night','5f35d1f41f52775f','codex','night'],
  ['meadow-day','e2041a0c18b333d3','claude','day'],
  ['crags-day','7cb1d78917291ca2','claude','day'],
  ['rime-day','cce5d9367601343c','claude','day'],
  ['fen-day','78ccaf9528b4f367','claude','day'],
  ['city-day','33779c41b20628f0','claude','day'],
  ['wyrd-day','75b165ad74a360fb','claude','day'],
  ['sky-day','0c009f9d39d87dc3','claude','day'],
  ['asterion-day','5e715b4a47a849bc','claude','day'],
];
const wanted=process.env.SCORES?.split(',');
for(const owner of ['codex','claude']){
  const pending=scores.filter(([label,,source])=>source===owner&&(!wanted||wanted.includes(label)));
  if(!pending.length)continue;
  const client=new Client({name:`valhallasc-chillhop-render-${owner}`,version:'1'});
  await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:owner}}));
  for(const [label,project_id,,kind] of pending){
    const opened=await client.callTool({name:'open_project',arguments:{project_id}},undefined,{timeout:300000});
    if(opened.isError)throw Error(`${label}: ${opened.content.map(x=>x.text).join('\n')}`);
    const project=JSON.parse(opened.content[0].text);
    if(project.project_id!==project_id)throw Error(`${label}: unexpected project copy`);
    const path=`/tmp/valhallasc-${label}-dybase2.wav`;
    const result=await client.callTool({name:'render_audio',arguments:{project_id,path,per_track:false,tail_seconds:2}},undefined,{timeout:300000});
    if(result.isError)throw Error(`${label}: ${result.content.map(x=>x.text).join('\n')}`);
    const audio=JSON.parse(result.content[0].text);
    console.log(label,JSON.stringify({kind,path:audio.wav,seconds:audio.seconds,peak_dbfs:audio.peak_dbfs,clipped_samples:audio.clipped_samples,problems:audio.problems,warnings:audio.warnings}));
    if(audio.problems?.length||audio.clipped_samples)throw Error(`${label}: render has problems`);
  }
  await client.close();
}
JS
