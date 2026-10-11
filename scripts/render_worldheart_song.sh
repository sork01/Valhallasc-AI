#!/bin/sh
# Render a saved dybase2 Veyrroot project; pass the project ID from create_worldheart_song.sh.
set -eu
test "$#" -eq 1 || { echo 'usage: render_worldheart_song.sh PROJECT_ID' >&2; exit 2; }
cd "$(dirname "$0")/../../dybase2"
exec env WORLDHEART_PROJECT_ID="$1" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-worldheart-render',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
const project_id=process.env.WORLDHEART_PROJECT_ID;
for(const [name,args] of [['open_project',{project_id}],['render_audio',{project_id,path:'/tmp/valhallasc-worldheart-dybase2.wav',per_track:false,tail_seconds:2}]]){
 const r=await client.callTool({name,arguments:args},undefined,{timeout:240000});
 if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
 console.log(name,r.content[0].text.slice(0,450));
}
await client.close();
JS
