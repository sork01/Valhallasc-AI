#!/bin/sh
# Render Stormglass's editable dybase2 project to a WAV for loop finishing.
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec env STORMGLASS_PROJECT_ID="${1:-2c200357fd474fbb}" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-stormglass-render',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env}}));
const project_id=process.env.STORMGLASS_PROJECT_ID;
for(const [name,args] of [['open_project',{project_id}],['render_audio',{project_id,path:'/tmp/valhallasc-stormglass-dybase2.wav',per_track:false,tail_seconds:2}]]) {
  const result=await client.callTool({name,arguments:args},undefined,{timeout:240000});
  if(result.isError) throw Error(`${name}: ${result.content.map(x=>x.text).join('\n')}`);
  console.log(name,result.content[0].text.slice(0,500));
}
await client.close();
JS
