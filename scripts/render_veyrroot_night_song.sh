#!/bin/sh
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const project_id='f72407011081b07f';
const c=new Client({name:'valhallasc-veyrroot-night-render',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
for(const [name,args]of [['open_project',{project_id}],['render_audio',{project_id,path:'/tmp/valhallasc-veyrroot-night-dybase2.wav',per_track:process.env.TRACKS!=='0',tail_seconds:2}]]){
 const r=await c.callTool({name,arguments:args},undefined,{timeout:600000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
 const x=JSON.parse(r.content[0].text);if(name==='render_audio'){console.log('RENDER',JSON.stringify(x));if(x.problems?.length||x.clipped_samples)throw Error('Render needs repair')}
}
await c.close();
JS
