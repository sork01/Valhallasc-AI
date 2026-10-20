#!/bin/sh
# Balance the four saved night mixes from measured individual dybase2 stems.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const scores=[
  ['moonspore','294d9f52ebb469b4', [['Root pulse',2],['Moonlit leaves',-22],['Spore drops',-12],['Lantern song',-19],['Night breakbeat',-4]]],
  ['asterion','aede47903c7017fe', [['Deep pulse',3],['Glass wheel',0],['City strings',-20],['Sky choir',-15],['Brass procession',-10],['Thirteen bells',-35],['Night breakbeat',-4]]],
  ['stormglass','7cfe6a386dd3266f', [['Undertow bass',2],['Sea mist',-19],['Glass current',3],['Storm bell',-36],['Night breakbeat',-4],['Chillhop hi-hat',-10]]],
  ['sunward','d33fdacfd0720334', [['Plucked strings',-10],['Millwheel marimba',-15],['Warm strings',-25],['Walking bass',3],['Night breakbeat',-4],['Chillhop hi-hat',-10]]],
];
const c=new Client({name:'valhallasc-next-four-night-mix',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
for(const [zone,project_id,mix] of scores){
  if(process.env.ZONES&&!process.env.ZONES.split(',').includes(zone))continue;
  const project=await call('open_project',{project_id});
  if(project.project_id!==project_id)throw Error(`${zone}: unexpected copy`);
  if(zone==='sunward')await call('set_instrument',{project_id,track:'Plucked strings',instrument:'sork60',preset:'Hiphop Chorus Keys'});
  for(const [track,volume_db] of mix)await call('set_mix',{project_id,track,volume_db});
  console.log('MIX',zone,project_id);
}
await c.close();
JS
