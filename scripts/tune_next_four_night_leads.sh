#!/bin/sh
# Fit the night-answer lead notes to their actual bar chords.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-next-four-night-lead-fit',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=57)=>({pitch,beat,beats,velocity});
for(const [zone,id,track,bars] of [
  ['moonspore','294d9f52ebb469b4','Lantern song',[[18,[n('C5',.5,.7),n('A4',1.5,.4),n('G4',2,.65)]]]],
  ['asterion','aede47903c7017fe','Brass procession',[[18,[n('E5',.5,.6),n('B4',2,1)]]]],
]){
  await call('open_project',{project_id:id});
  for(const [start_bar,notes] of bars)await call('write_notes',{project_id:id,track,start_bar,bars:1,notes,name:'Night answer in harmony'});
  const a=await call('analyse_song',{project_id:id});
  if(a.problems?.length)throw Error(`${zone}: ${a.problems.join('; ')}`);
  console.log('TUNED',zone,id);
}
await c.close();
JS
