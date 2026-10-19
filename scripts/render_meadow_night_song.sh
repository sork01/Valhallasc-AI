#!/bin/sh
# Render the saved Greenmeadow night remix through dybase2's MCP.
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec env MEADOW_NIGHT_PROJECT_ID="${1:-6c52c389c99ed898}" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-meadow-night-render',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const project_id=process.env.MEADOW_NIGHT_PROJECT_ID;
for(const [name,args] of [['open_project',{project_id}],['render_audio',{project_id,path:'/tmp/valhallasc-meadow-night-dybase2.wav',per_track:true,tail_seconds:2}]]) {
  const result=await client.callTool({name,arguments:args},undefined,{timeout:300000});
  if(result.isError) throw Error(`${name}: ${result.content.map(x=>x.text).join('\n')}`);
  const data=JSON.parse(result.content[0].text);
  if(name==='open_project') console.log(name,JSON.stringify({project_id:data.project_id,name:data.name,tempo:data.tempo,bars:data.bars}));
  else console.log(name,JSON.stringify({keys:Object.keys(data),wav:data.wav,integrated_lufs:data.integrated_lufs,peak_dbfs:data.peak_dbfs,tracks:data.tracks,problems:data.problems,warnings:data.warnings,notes:data.notes}).slice(0,7500));
}
await client.close();
JS
