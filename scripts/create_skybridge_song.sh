#!/bin/sh
# Original 3/4 prismatic arch waltz; no foreground lead. Editable source is dybase2.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
const c=new Client({name:'valhallasc-skybridge-song',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const call=async(name,args)=>{const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(v=>v.text).join('\n')}`);return JSON.parse(r.content[0].text);};
try {
 const project=await call('create_project',{name:'Valhalla The Shattered Span - Seven Broken Arches',bpm:96,time_signature:'3/4',key:'E minor'});
 const A={project_id:project.project_id};
 fs.writeFileSync('/tmp/skybridge-music-project.json',JSON.stringify(project,null,2));
 for(const [name,instrument,preset,volume_db] of [['Shard harp','dexed','HARPSICHORD',-8],['Arch bass','dexed','WOOD BASS',-11],['Rainbow veil','sork60','Mellow Pad',-18],['Prism chimes','dexed','GLASS VIBES',-9],['Toll step','axiom8','Chillhop',-2]])await call('add_track',{name,instrument,preset,volume_db,...A});
 const chords=['Em','C','G','D','Em','Am','C','B7','Em','G','C','D','Am','Em','C','B7','G','D','Am','C','Em','Am','B7','Em'];
 const tones={Em:['E3','G3','B3','E4'],C:['C3','E3','G3','C4'],G:['G2','B2','D3','G3'],D:['D3','F#3','A3','D4'],Am:['A2','C3','E3','A3'],B7:['B2','D#3','F#3','B3']};
 const bass=[],veil=[],harp=[],chimes=[],drums=[];
 const n=(pitch,beat,beats,velocity)=>({pitch,beat,beats,velocity});
 chords.forEach((chord,i)=>{const b=i*3,t=tones[chord],end=i===23;
  bass.push(n(t[0].replace('3','2'),b,end?2.7:1.8,65));if(!end)bass.push(n(t[0].replace('3','2'),b+2,.8,50));
  for(const pitch of t.slice(1))veil.push(n(pitch,b,2.75,38));
  const shape=i>=8&&i<16?[0,2,3,1,2,3]:[0,1,2,3,2,1];
  for(let k=0;k<(end?3:6);k++)harp.push(n(t[shape[k]],b+k*.5,.38,k%3===0?64:48));
  if(i%2===0&&!end)chimes.push(n(t[3],b+1,.9,46),n(t[2],b+2.5,.45,40));
  if(!end){drums.push(n(36,b,.2,60),n(45,b+1,.15,38),n(48,b+2,.15,36));}
  else drums.push(n(45,b,.4,44));
 });
 for(const [track,notes] of [['Shard harp',harp],['Arch bass',bass],['Rainbow veil',veil],['Prism chimes',chimes],['Toll step',drums]])await call('write_notes',{track,start_bar:1,bars:24,notes,name:track,...A});
 await call('add_fx_return',{name:'Span vault',effect:'sorkverb',...A});
 for(const track of ['Shard harp','Rainbow veil','Prism chimes'])await call('set_send',{track,fx_return:'Span vault',level_db:track==='Rainbow veil'?-29:-22,...A});
 for(const [at_bar,name] of [[1,'The Rainbow Threshold'],[9,'West and East Galleries'],[17,'The Archon Keystone']])await call('add_marker',{name,at_bar,...A});
 for(const [parameter,value] of [['env.attack',.08],['env.release',.35]])await call('automate',{...A,track:'Rainbow veil',parameter,points:[{bar:1,value},{bar:25,value}]});
 const analysis=await call('analyse_song',A);fs.writeFileSync('/tmp/skybridge-music-analysis.json',JSON.stringify(analysis,null,2));
 const render=await call('render_audio',{...A,path:'/tmp/valhallasc-skybridge-dybase2.wav',per_track:true,tail_seconds:3});
 fs.writeFileSync('/tmp/skybridge-music-render.json',JSON.stringify(render,null,2));
 console.log(JSON.stringify({project,render}));
}finally{await c.close();}
JS
