#!/bin/sh
# Original 5/4 chamber procession; no foreground lead. Editable source is dybase2.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
const c=new Client({name:'valhallasc-nornroot-song',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const call=async(name,args)=>{const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(v=>v.text).join('\n')}`);return JSON.parse(r.content[0].text);};
try {
 const project=await call('create_project',{name:'Valhalla Nornroot Barrow - Threads Without a King',bpm:88,time_signature:'5/4',key:'D minor'});
 const A={project_id:project.project_id};
 fs.writeFileSync('/tmp/nornroot-music-project.json',JSON.stringify(project,null,2));
 for(const [name,instrument,preset,volume_db] of [['Spindles','dexed','HARPSICHORD',-8],['Stone steps','dexed','WOOD BASS',-12],['Burial cloth','sork60','Mellow Pad',-19],['Amber answer','dexed','LOG DRUM',-1],['Procession','axiom8','Chillhop',-2]])await call('add_track',{name,instrument,preset,volume_db,...A});
 const chords=['Dm','Bb','Gm','A7','Dm','Dm','F','C','Bb','A7','Gm','Dm','Bb','Gm','Dm','A7','F','A7','Dm','Bb','Gm','A7','A7','Dm'];
 const tones={Dm:['D3','F3','A3','D4'],Bb:['Bb2','D3','F3','Bb3'],Gm:['G2','Bb2','D3','G3'],A7:['A2','C#3','E3','G3'],F:['F2','A2','C3','F3'],C:['C3','E3','G3','C4']};
 const bass=[],cloth=[],spindles=[],answer=[],drums=[];
 const n=(pitch,beat,beats,velocity)=>({pitch,beat,beats,velocity});
 chords.forEach((chord,i)=>{const b=i*5,t=tones[chord],end=i===23;
  bass.push(n(t[0].replace('3','2'),b,end?4.4:2.5,64));if(!end)bass.push(n(t[0].replace('3','2'),b+3,1.6,51));
  for(const pitch of t.slice(1))cloth.push(n(pitch,b,4.55,37));
  const shape=i>=12&&i<18?[0,2,1,3,2]:[0,1,2,1,3];
  for(let k=0;k<(end?3:5);k++)spindles.push(n(t[shape[k]],b+k,.44,k===0||k===3?65:47));
  if(i>=6&&i<22&&i%2===1)for(const [j,k] of [[1,2],[3,1],[4,0]])answer.push(n(t[k],b+j+.5,.3,45));
  if(!end){drums.push(n(36,b,.2,61),n(45,b+1,.15,39),n(45,b+2,.15,35),n(36,b+3,.2,52),n(48,b+4,.15,38));}
  else drums.push(n(45,b,.4,44));
 });
 for(const [track,notes] of [['Spindles',spindles],['Stone steps',bass],['Burial cloth',cloth],['Amber answer',answer],['Procession',drums]])await call('write_notes',{track,start_bar:1,bars:24,notes,name:track,...A});
 await call('add_fx_return',{name:'Barrow chamber',effect:'sorkverb',...A});
 for(const track of ['Spindles','Burial cloth','Amber answer'])await call('set_send',{track,fx_return:'Barrow chamber',level_db:track==='Burial cloth'?-30:-23,...A});
 for(const [at_bar,name] of [[1,'Three steps, two threads'],[7,'The amber promise'],[13,'The spindle turns'],[19,'An unwritten ending']])await call('add_marker',{name,at_bar,...A});
 for(const [parameter,value] of [['env.attack',.08],['env.release',.35]])await call('automate',{...A,track:'Burial cloth',parameter,points:[{bar:1,value},{bar:25,value}]});
 const analysis=await call('analyse_song',A);fs.writeFileSync('/tmp/nornroot-music-analysis.json',JSON.stringify(analysis,null,2));
 const render=await call('render_audio',{...A,path:'/tmp/valhallasc-nornroot-dybase2.wav',per_track:true,tail_seconds:3});
 fs.writeFileSync('/tmp/nornroot-music-render.json',JSON.stringify(render,null,2));
 console.log(JSON.stringify({project,render}));
}finally{await c.close();}
JS
