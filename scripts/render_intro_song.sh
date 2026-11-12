#!/usr/bin/env bash
# Render two dybase project copies so fewer synths share an offline graph.
# The five-part editable score is preserved, and the host cap stays unchanged.
set -euo pipefail
score_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export INTRO_SCORE_OUT="${INTRO_SCORE_OUT:-$score_repo/test-results/intro-strings}"
mkdir -p "$INTRO_SCORE_OUT"
cd "${DYBASE2_DIR:-/home/serveperry/webserver/www/dybase2}"
for intro_group in ${INTRO_GROUPS:-low high}; do
export INTRO_GROUP="$intro_group"
/home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import fs from 'node:fs';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'veyrheim-intro-render',version:'1'}),out=process.env.INTRO_SCORE_OUT,group=process.env.INTRO_GROUP;
const low=['Basses','Cellos','Violas'],high=['Second violins','First violins'];
if(!['low','high'].includes(group))throw Error('Expected low or high string group');
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args},undefined,{timeout:540000});if(r.isError)throw Error(r.content.map(x=>x.text).join('\n'));const d=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(d).slice(0,220));return d;}
try {
 // The source belongs to claude: dybase copies it on open for owner codex.
 const source=process.env.INTRO_PROJECT||'2930e63d0705e3be';
 const project=await call('open_project',{project_id:source});
 if(project.project_id===source)throw Error('Export requires a copy of the source project');
 const project_id=project.project_id;
 fs.writeFileSync(`${out}/project-${group}.json`,JSON.stringify(project,null,2)+'\n');
 await call('rename_project',{project_id,name:`Veyrheim intro render - ${group} strings`});
 for(const track of group==='low'?high:low)await call('remove_track',{project_id,track});
 const report=await call('render_audio',{project_id,per_track:false,tail_seconds:2,path:`${out}/strings-${group}.wav`});
 fs.writeFileSync(`${out}/render-${group}.json`,JSON.stringify(report,null,2)+'\n');
}finally{await client.close();}
JS
done
