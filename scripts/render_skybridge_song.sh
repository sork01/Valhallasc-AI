#!/bin/sh
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
const c=new Client({name:'valhallasc-skybridge-mix',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const A={project_id:'5d59c0df33cd65c9'};
const call=async(name,args)=>{const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(JSON.stringify(r.content));return JSON.parse(r.content[0].text);};
try{
 await call('open_project',A);
 for(const [track,volume_db] of [['Shard harp',-8],['Arch bass',-11],['Rainbow veil',-18],['Prism chimes',-9],['Toll step',-2]])await call('set_mix',{...A,track,volume_db});
 for(const [parameter,value] of [['env.attack',.08],['env.release',.35]])await call('automate',{...A,track:'Rainbow veil',parameter,points:[{bar:1,value},{bar:25,value}]});
 const render=await call('render_audio',{...A,path:'/tmp/valhallasc-skybridge-dybase2.wav',per_track:true,tail_seconds:3});
 fs.writeFileSync('/tmp/skybridge-music-render.json',JSON.stringify(render,null,2));console.log(JSON.stringify(render));
}finally{await c.close();}
JS
