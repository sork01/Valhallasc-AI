#!/bin/sh
# Align every intro and section's kick with recurring bass attacks.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-next-four-night-kick-alignment',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
function row(steps,hits,accent=[]){const out=Array(steps).fill('.');for(const i of hits)out[i]=accent.includes(i)?'X':'x';return out.join('')}
for(const [zone,project_id,steps,kick,snare,hat,rim,velocity] of [
  ['moonspore','294d9f52ebb469b4',12,[0,8],[6],[2,4,6,10],[11],56],
  ['asterion','aede47903c7017fe',16,[0,11],[8],[2,6,10,14],[15],60],
  ['stormglass','7cfe6a386dd3266f',16,[0,7,13],[8],[2,5,10,14],[15],58],
  ['sunward','d33fdacfd0720334',16,[0,10],[4,12],[2,6,10,14],[15],54],
]){
  await call('open_project',{project_id});
  await call('clear_bars',{project_id,track:'Night breakbeat'});
  for(let section=0;section<4;section++)await call('write_drums',{project_id,track:'Night breakbeat',start_bar:section*8+1,bars:8,
    pattern:{kick:row(steps,kick,[0]),snare:row(steps,snare),hat:row(steps,section===0?hat.filter((_,i)=>i%2===0):section===3?hat.filter((_,i)=>i%2===1):hat),clap:row(steps,section===1?rim:[])},
    swing:0,velocity:section===0?velocity-5:section===3?velocity-3:velocity,name:['Dusk break','Lantern theme break','Night answer break','Before dawn break'][section]});
  const a=await call('analyse_song',{project_id});
  if(a.problems?.length)throw Error(`${zone}: ${a.problems.join('; ')}`);
  console.log('ALIGNED',zone,project_id);
}
await c.close();
JS
