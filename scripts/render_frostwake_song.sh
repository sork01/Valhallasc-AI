#!/bin/sh
# Render the saved dybase2 project with a longer MCP timeout for six synth tracks.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec env FROSTWAKE_PROJECT_ID="${1:-75951aa438eab92b}" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-frostwake-render',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
const project_id=process.env.FROSTWAKE_PROJECT_ID;
for(const [name,args] of [['open_project',{project_id}],['render_audio',{project_id,path:'/tmp/valhallasc-frostwake-dybase2.wav',per_track:false,tail_seconds:2}]]){
 const r=await client.callTool({name,arguments:args},undefined,{timeout:240000});
 if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
 console.log(name,r.content[0].text.slice(0,500));
}
await client.close();
JS
