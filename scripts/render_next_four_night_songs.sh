#!/bin/sh
# Render the four current night-remix projects, including track measurements.
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const scores=[['moonspore','294d9f52ebb469b4'],['asterion','aede47903c7017fe'],['stormglass','7cfe6a386dd3266f'],['sunward','d33fdacfd0720334']];
const c=new Client({name:'valhallasc-next-four-night-render',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:600000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
for(const [zone,project_id] of scores){
  if(process.env.ZONES&&!process.env.ZONES.split(',').includes(zone))continue;
  const project=await call('open_project',{project_id});
  if(project.project_id!==project_id)throw Error(`${zone}: unexpected project copy`);
  const render=await call('render_audio',{project_id,path:`/tmp/valhallasc-${zone}-night-dybase2.wav`,per_track:process.env.TRACKS!=='0',tail_seconds:2});
  console.log('RENDER',JSON.stringify({zone,id:project_id,wav:render.wav,seconds:render.seconds,integrated_lufs:render.integrated_lufs,peak_dbfs:render.peak_dbfs,clipped_samples:render.clipped_samples,load_problems:render.load_problems,problems:render.problems,warnings:render.warnings,tracks:render.tracks}));
  if(render.problems?.length||render.clipped_samples)throw Error(`${zone}: render needs repair`);
}
await c.close();
JS
