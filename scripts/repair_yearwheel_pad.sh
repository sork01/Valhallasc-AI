#!/bin/sh
# Replace the drifting OB-Xd pad and untried choir in Four Horizons with proven Sork-60 patches.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec env YEARWHEEL_PROJECT_ID="${1:-c7ab959e2d451253}" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-yearwheel-pad-repair',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
const project_id=process.env.YEARWHEEL_PROJECT_ID;
async function call(name,args){
 const r=await client.callTool({name,arguments:{project_id,...args}},undefined,{timeout:180000});
 if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
 console.log(name,r.content[0].text.slice(0,300));
}
await call('open_project',{});
await call('set_instrument',{track:'Horizon strings',instrument:'sork60',preset:'Mellow Pad'});
await call('set_mix',{track:'Horizon strings',volume_db:-19});
await call('set_instrument',{track:'Distant choir',instrument:'sork60',preset:'Juno Strings'});
await call('set_mix',{track:'Distant choir',volume_db:-26});
await call('analyse_song',{});
await client.close();
JS
