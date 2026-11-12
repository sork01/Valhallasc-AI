#!/usr/bin/env bash
# Create the original, editable 62-second Veyrheim intro score through dybase2 MCP.
set -euo pipefail
score_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export INTRO_SCORE_OUT="${INTRO_SCORE_OUT:-$score_repo/test-results/intro-strings}"
mkdir -p "$INTRO_SCORE_OUT"
cd "${DYBASE2_DIR:-/home/serveperry/webserver/www/dybase2}"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import fs from 'node:fs';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'veyrheim-intro-strings',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
const out=process.env.INTRO_SCORE_OUT, log=[];
async function call(name,args={}) {
 const r=await client.callTool({name,arguments:args},undefined,{timeout:540000});
 if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
 const data=JSON.parse(r.content[0].text);log.push({tool:name,args,result:data});
 fs.writeFileSync(`${out}/mcp-calls.json`,JSON.stringify(log,null,2)+'\n');
 console.log(name,JSON.stringify(data).slice(0,220));return data;
}
try {
 const project=await call('create_project',{name:'Veyrheim - Beyond the Nine Chains',bpm:96,time_signature:'4/4',key:'D minor'});
 fs.writeFileSync(`${out}/project.json`,JSON.stringify(project,null,2)+'\n');
 const A={project_id:project.project_id};
 const tracks=[['Basses',-9,.08,3,3,4.6],['Cellos',-11,.12,1.1,2,5.0],['Violas',-12,.22,4,3,5.0],['Second violins',-13,.3,2,2.2,5.6],['First violins',-8,-.25,3.5,3,6.0]];
 for(const [name,volume_db,pan,attack,release,cutoff] of tracks) {
  await call('add_track',{...A,name,instrument:'sork60',preset:'Juno Strings',volume_db,pan});
  for(const [parameter,value] of [['env.attack',attack],['env.release',release],['vcf.freq',cutoff],['dco.lfo',0],['ext.velocity',1]])
   await call('automate',{...A,track:name,parameter,points:[{bar:1,value}]});
 }
 // One chord per 2.5-second bar. A major is the harmonic-minor dominant;
 // the final D major is an intentional Picardy third for the welcome home.
 const harmony=[
  ['Dm','D2',['D3','F3','A3'],['D4','F4','A4']],['Dm/C','C2',['D3','F3','A3'],['D4','F4','A4']],
  ['Bbmaj7','Bb1',['D3','F3','A3'],['D4','F4','Bb4']],['Asus4','A1',['D3','E3','A3'],['D4','E4','A4']],
  ['Dm','D2',['D3','F3','A3'],['D4','F4','A4']],['Bb','Bb1',['D3','F3','Bb3'],['D4','F4','Bb4']],
  ['F','F2',['C3','F3','A3'],['C4','F4','A4']],['C','C2',['C3','E3','G3'],['E4','G4','C5']],
  ['Gm','G1',['D3','G3','Bb3'],['D4','G4','Bb4']],['Dm/F','F2',['D3','F3','A3'],['D4','F4','A4']],
  ['Bb','Bb1',['D3','F3','Bb3'],['D4','F4','Bb4']],['A','A1',['C#3','E3','A3'],['C#4','E4','A4']],
  ['Dm','D2',['D3','F3','A3'],['D4','F4','A4']],['C','C2',['C3','E3','G3'],['C4','E4','G4']],
  ['Bb','Bb1',['D3','F3','Bb3'],['D4','F4','Bb4']],['A','A1',['C#3','E3','A3'],['C#4','E4','A4']],
  ['Gm','G1',['D3','G3','Bb3'],['D4','G4','Bb4']],['A','A1',['C#3','E3','A3'],['C#4','E4','A4']],
  ['Dm','D2',['D3','F3','A3'],['D4','F4','A4']],['Bb','Bb1',['D3','F3','Bb3'],['D4','F4','Bb4']],
  ['F','F2',['C3','F3','A3'],['C4','F4','A4']],['C','C2',['C3','E3','G3'],['C4','E4','G4']],
  ['Bb','Bb1',['D3','F3','Bb3'],['D4','F4','Bb4']],['D','D2',['D3','F#3','A3'],['D4','F#4','A4']]
 ];
 const parts=Object.fromEntries(tracks.map(([n])=>[n,[]]));
 function note(track,pitch,beat,beats,velocity){parts[track].push({pitch,beat,beats,velocity});}
 const octave=(p,n=1)=>p.replace(/\d$/,x=>Number(x)+n);
 for(let bar=0;bar<24;bar++) {
  const [chord,root,lower,upper]=harmony[bar], b=bar*4;
  const v=bar<4?45:bar<12?57:bar<18?68:bar<23?78:66;
  note('Basses',root,b,bar===23?3.4:3.65,v);
  for(const p of lower.slice(0,2)) note('Violas',p,b+.06,bar===23?3.5:3.65,v-9);
  if(bar<4){note('Cellos',octave(root),b,3.4,v-5);continue;}
  if(bar===23){note('Cellos','D3',b,3.3,70);for(const p of upper)note('Second violins',p,b,3.4,65);continue;}
  // Bowed eighth-note pulse, with every onset on the grid and explicit gaps.
  const root3=octave(root,root.endsWith('1')?2:1),fifth=lower.at(-1);
  const pulse=[root3,fifth,octave(root3),fifth,root3,lower[1],fifth,lower[1]];
  for(let i=0;i<8;i++)note('Cellos',pulse[i],b+i*.5,.32,v+(i%4===0?7:-7));
  if(bar>=12&&bar<18)for(let i=0;i<8;i++)note('Second violins',upper[[0,1,2,1,0,1,2,1][i]],b+i*.5,.29,v-15+(i%4===0?6:0));
  if(bar>=18)for(const p of upper.slice(0,2))note('Second violins',p,b,3.55,v-12);
 }
 const melody={
  4:[['D5',0,1.4],['A4',1.5,.4],['D5',2,.9],['F5',3,.8]],
  5:[['F5',0,1.9],['D5',2,.9],['Bb4',3,.8]],
  6:[['C5',0,.9],['F5',1,.9],['A5',2,1.7]],
  7:[['G5',0,1.4],['E5',1.5,.9],['D5',2.5,.4],['C5',3,.7]],
  12:[['A4',0,1.4],['D5',1.5,.9],['F5',2.5,1.1]],
  13:[['E5',0,1.9],['D5',2,.8],['C5',3,.8]],
  14:[['D5',0,1.9],['F5',2,.9],['Bb5',3,.8]],
  15:[['A5',0,1.4],['E5',1.5,.9],['C#5',2.5,1.1]],
  16:[['D5',0,1.4],['G5',1.5,.9],['Bb5',2.5,1.1]],
  17:[['A5',0,.9],['E5',1,.9],['C#5',2,1.5]],
  18:[['D5',0,.9],['A5',1,.9],['D6',2,1.65]],
  19:[['Bb5',0,1.4],['F5',1.5,.4],['D5',2,1.65]],
  20:[['F5',0,.9],['A5',1,.9],['C6',2,1.6]],
  21:[['G5',0,1.4],['E5',1.5,.9],['C5',2.5,1.1]],
  22:[['D5',0,.9],['F5',1,.9],['Bb5',2,1.1],['A5',3.25,.4]],
  23:[['A5',0,.9],['F#5',1,.9],['D5',2,1.6]]
 };
 for(const [b,phrase] of Object.entries(melody))for(const [pitch,at,len]of phrase)note('First violins',pitch,+b*4+at,len,+b<8?62:+b<18?72:83);
 for(const [track,notes]of Object.entries(parts))await call('write_notes',{...A,track,start_bar:1,bars:24,notes,name:'Beyond the Nine Chains'});
 for(const [name,seconds]of [['The buried forge',0],['The broken promise',12.5],['Nine chains breaking',25],['Beyond the world',35],['A hero is found',46.8],['The Grey Gull',51],['Welcome to Veyrheim',58]])
  await call('add_marker',{...A,name:`${name} (${seconds}s)`,at_bar:1+Math.floor(seconds/2.5)});
 await call('add_fx_return',{...A,name:'Hall of roots',effect:'sorkverb'});
 for(const [track]of tracks)await call('set_send',{...A,track,fx_return:'Hall of roots',level_db:track==='Basses'?-30:track==='Cellos'?-25:-22});
 // Restrained opening, growing into the theme, then a natural closing release.
 for(const [track,db]of tracks)await call('automate',{...A,track,parameter:'volume',points:[{bar:1,value:db-5},{bar:5,value:db-2},{bar:13,value:db},{bar:18.5,value:db+1},{bar:19,value:db+1},{bar:23,value:db},{bar:24,value:db-2},{bar:24.65,value:db-3},{bar:25,value:db-14}]});
 fs.writeFileSync(`${out}/score.json`,JSON.stringify({title:'Beyond the Nine Chains',project,harmony,bpm:96,bars:24,seconds:62,parts},null,2)+'\n');
 await call('analyse_song',A);
}finally{await client.close();}
JS
