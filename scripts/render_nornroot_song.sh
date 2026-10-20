#!/bin/sh
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
const c=new Client({name:'valhallasc-nornroot-mix',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const A={project_id:'3f288c16e36ca5c2'};
const call=async(name,args)=>{const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(JSON.stringify(r.content));return JSON.parse(r.content[0].text);};
try{
 await call('open_project',A);
 for(const [track,volume_db] of [['Spindles',-8],['Stone steps',-12],['Burial cloth',-19],['Amber answer',-1],['Procession',-2]])await call('set_mix',{...A,track,volume_db});
 for(const [parameter,value] of [['env.attack',.08],['env.release',.35]])await call('automate',{...A,track:'Burial cloth',parameter,points:[{bar:1,value},{bar:25,value}]});
 const render=await call('render_audio',{...A,path:'/tmp/valhallasc-nornroot-dybase2.wav',per_track:true,tail_seconds:3});
 fs.writeFileSync('/tmp/nornroot-music-render.json',JSON.stringify(render,null,2));console.log(JSON.stringify(render));
}finally{await c.close();}
JS
