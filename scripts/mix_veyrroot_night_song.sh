#!/bin/sh
# Bring the quiet bell and flute replies into the finished Veyrroot night mix.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const project_id='f72407011081b07f';
const c=new Client({name:'valhallasc-veyrroot-night-mix',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args){const r=await c.callTool({name,arguments:{project_id,...args}});if(r.isError)throw Error(`${name}: ${r.content[0].text}`)}
await call('open_project',{});
for(const [track,volume_db]of [['Branch kalimba',-10],['Amber bells',-15],['Canopy flute',-14],['Heartwood air',-30]])await call('set_mix',{track,volume_db});
console.log('MIX',project_id);
await c.close();
JS
