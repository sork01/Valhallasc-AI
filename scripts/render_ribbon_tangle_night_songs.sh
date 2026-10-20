#!/bin/sh
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-ribbon-tangle-night-render',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
for(const [zone,project_id]of [['ribbonwild','5a0f5aed7413939b'],['tanglecrown','b9a83443f1d8b949']]){
 if(process.env.ZONES&&!process.env.ZONES.split(',').includes(zone))continue;
 const opened=await c.callTool({name:'open_project',arguments:{project_id}},undefined,{timeout:300000});if(opened.isError)throw Error(`${zone}: ${opened.content.map(x=>x.text).join('\n')}`);
 const r=await c.callTool({name:'render_audio',arguments:{project_id,path:`/tmp/valhallasc-${zone}-night-dybase2.wav`,per_track:process.env.TRACKS!=='0',tail_seconds:2}},undefined,{timeout:600000});
 if(r.isError)throw Error(`${zone}: ${r.content.map(x=>x.text).join('\n')}`);
 const x=JSON.parse(r.content[0].text);console.log('RENDER',JSON.stringify({zone,id:project_id,wav:x.wav,seconds:x.seconds,integrated_lufs:x.integrated_lufs,peak_dbfs:x.peak_dbfs,clipped_samples:x.clipped_samples,problems:x.problems,warnings:x.warnings,tracks:x.tracks}));
 if(x.problems?.length||x.clipped_samples)throw Error(`${zone}: render needs repair`);
}
await c.close();
JS
