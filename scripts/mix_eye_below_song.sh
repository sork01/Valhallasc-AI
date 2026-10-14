#!/bin/sh
# Balance the saved score after its first dybase2 render showed quiet mids and bass transients.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec env EYE_PROJECT_ID="${1:-}" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-eye-below-mix',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
const project_id=process.env.EYE_PROJECT_ID;
async function call(name,args){const r=await client.callTool({name,arguments:{project_id,...args}},undefined,{timeout:240000});if(r.isError)throw Error(r.content.map(x=>x.text).join('\n'));console.log(name,args.track||'',r.content[0].text.slice(0,150));}
await call('open_project',{});
for(const [track,volume_db,pan] of [
 ['Deepglass pulse',-22,-.14],['Iris voice',-8,.04],['Far lens',-15,.22],
 ['Undertide air',-15,-.18],['Stone current',-23,0],['Three knocks',-17,0],
])await call('set_mix',{track,volume_db,pan});
await client.close();
JS
