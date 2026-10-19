#!/bin/sh
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-two-night-renders',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
for(const [label,project_id,path] of [
  ['crags','90d3be446ee5a58f','/tmp/valhallasc-crags-night-dybase2.wav'],
  ['rime','4091d2184af5bf68','/tmp/valhallasc-rime-night-dybase2.wav'],
]) {
  const opened=await c.callTool({name:'open_project',arguments:{project_id}});
  if(opened.isError) throw Error(opened.content[0].text);
  const rendered=await c.callTool({name:'render_audio',arguments:{project_id,path,per_track:true,tail_seconds:2}},undefined,{timeout:300000});
  if(rendered.isError) throw Error(rendered.content[0].text);
  const d=JSON.parse(rendered.content[0].text);
  console.log(label,JSON.stringify({path:d.wav,seconds:d.seconds,integrated_lufs:d.integrated_lufs,peak_dbfs:d.peak_dbfs,clipped_samples:d.clipped_samples,tracks:d.tracks,problems:d.problems,warnings:d.warnings,notes:d.notes}));
}
await c.close();
JS
