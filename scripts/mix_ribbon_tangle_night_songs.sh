#!/bin/sh
# Balance the saved night arrangements using measured stem levels.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const songs=[
 ['ribbonwild','5a0f5aed7413939b',[['Painted clav',0],['Bell garlands',-32],['Silk strings',-30],['Parade bass',1],['Night breakbeat',-4],['Chillhop hi-hat',-10]]],
 ['tanglecrown','b9a83443f1d8b949',[['Canopy marimba',-7],['Leaf glints',-30],['Rain mist',-28],['Root bass',2],['Night breakbeat',-4],['Chillhop hi-hat',-10]]]
];
const c=new Client({name:'valhallasc-ribbon-tangle-night-mix',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
for(const [zone,project_id,tracks]of songs){
 const opened=await c.callTool({name:'open_project',arguments:{project_id}});if(opened.isError)throw Error(`${zone}: ${opened.content[0].text}`);
 for(const [track,volume_db]of tracks){const r=await c.callTool({name:'set_mix',arguments:{project_id,track,volume_db}});if(r.isError)throw Error(`${zone}/${track}: ${r.content[0].text}`)}
 console.log('MIX',zone,project_id);
}
await c.close();
JS
