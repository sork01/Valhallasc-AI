#!/bin/sh
# Render the saved Elder Hollow project through dybase2's own export engine.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec env ELDER_PROJECT_ID="${1:-}" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-elder-hollow-render',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
const project_id=process.env.ELDER_PROJECT_ID;
for(const [name,args] of [['open_project',{project_id}],['render_audio',{project_id,path:'/tmp/valhallasc-elder-hollow-dybase2.wav',per_track:true,tail_seconds:2}]]){
 const r=await client.callTool({name,arguments:args},undefined,{timeout:300000});
 if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
 console.log(name,r.content[0].text.slice(0,4000));
}
await client.close();
JS
