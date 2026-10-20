#!/bin/sh
# Copy and remix Saltglass Mirage (daytime project 252658ec51f98316).
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
async function connect(owner,name){
  const c=new Client({name,version:'1'});
  await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:owner}}));
  return c;
}
async function call(c,name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const sourceName='Valhalla Prismwaste Editable Daytime Source - Saltglass Mirage';
const nightName='Valhalla Prismwaste Night - Saltglass Afterglow';
const src=await connect('valhallasc_source','valhallasc-prism-day-source');
const sources=(await call(src,'list_projects',{mine_only:true})).projects;
let sourceId=sources.find(p=>p.name===sourceName)?.id;
if(!sourceId){
  const p=await call(src,'open_project',{project_id:'252658ec51f98316'});
  if(p.copied_from?.id!=='252658ec51f98316')throw Error('Expected a daytime copy');
  sourceId=p.project_id;
  await call(src,'rename_project',{project_id:sourceId,name:sourceName});
}
await src.close();
const c=await connect('codex','valhallasc-prism-night-remix');
const nights=(await call(c,'list_projects',{mine_only:true})).projects;
const existing=nights.find(p=>p.name===nightName);
const opened=await call(c,'open_project',{project_id:existing?.id||sourceId});
if(!existing&&opened.copied_from?.id!==sourceId)throw Error('Expected a night copy');
const A={project_id:opened.project_id};
await call(c,'rename_project',{name:nightName,...A});
await call(c,'set_tempo',{bpm:84,...A});
await call(c,'set_key',{key:'E phrygian',...A});
for(const track of ['Dune bass','Mirror wash','Salt glints','Mirage call'])await call(c,'clear_bars',{track,...A});
await call(c,'set_instrument',{track:'Mirror wash',instrument:'sork60',preset:'Mellow Pad',...A});
await call(c,'set_instrument',{track:'Mirage call',instrument:'sork60',preset:'Unison Lead',...A});
for(const [track,volume_db,pan] of [['Dune bass',-13,0],['Mirror wash',-25,0],['Salt glints',-13,.25],['Mirage call',-21,-.1]])await call(c,'set_mix',{track,volume_db,pan,...A});
const chords=('Em7 Cmaj7 Am7 Fmaj7 Em7 G7 Dm7 Fmaj7 '+
              'Em7 Cmaj7 G7 Dm7 Am7 Fmaj7 G7 Em7 '+
              'Am7 Cmaj7 Dm7 Fmaj7 Em7 G7 Fmaj7 Em7 '+
              'Em7 Cmaj7 Am7 Fmaj7 Dm7 G7 Em7 Em7').split(' ');
await call(c,'write_chords',{track:'Mirror wash',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:54,velocity:42,name:'Cool saltglass harmony',...A});
const n=(pitch,beat,beats,velocity=55)=>({pitch,beat,beats,velocity});
const roots={Em7:'E2',Cmaj7:'C2',Am7:'A1',Fmaj7:'F2',G7:'G2',Dm7:'D2'};
const tones={Em7:['E4','G4','B4'],Cmaj7:['C4','E4','G4'],Am7:['A3','C4','E4'],Fmaj7:['F4','A4','C5'],G7:['G4','B4','D5'],Dm7:['D4','F4','A4']};
const bass=[],glints=[];
chords.forEach((chord,i)=>{const b=i*4,t=tones[chord];
  bass.push(n(roots[chord],b,2.8,i%8===0?57:47));
  glints.push(n(t[1],b+.85,.42,52),n(t[2],b+2.75,.48,44));
});
await call(c,'write_notes',{track:'Dune bass',start_bar:1,bars:32,notes:bass,name:'Night dune steps',...A});
await call(c,'write_notes',{track:'Salt glints',start_bar:1,bars:32,notes:glints,name:'Two saltglass reflections',...A});
const phrase=(bars,offset)=>bars.flatMap((bar,i)=>bar.map(([pitch,at,length,velocity])=>n(pitch,(i+offset)*4+at,length,velocity)));
const theme=[
  [['E5',.5,1,62],['F5',2,.5,55],['G5',3,.7,59]],
  [['E5',.6,1,57],['C5',2.4,1,53]],
  [['A4',.5,.85,55],['C5',1.9,.65,56],['E5',3,.7,59]],
  [['F5',.5,.9,57],['C5',2.4,1,52]],
  [['E5',.5,1.1,60],['G5',2.6,.85,56]],
  [['D5',.55,.8,54],['B4',2.4,1,51]],
  [['F5',.5,.85,56],['D5',2.3,1,52]],
  [['E5',.5,2.7,60]],
];
const answer=[
  [['G5',.5,.9,59],['F5',2,.6,54],['E5',3,.7,57]],
  [['E5',.5,.8,56],['C5',2.3,1,52]],
  [['D5',.5,.8,55],['B4',2.3,1,51]],
  [['A4',.5,.8,53],['F4',2.3,1,50]],
  [['B4',.5,.75,54],['E5',1.9,.7,58],['G5',3,.7,57]],
  [['D5',.5,.9,54],['B4',2.4,.9,51]],
  [['C5',.5,.85,54],['A4',2.3,1,51]],
  [['E5',.5,2.7,59]],
];
await call(c,'write_notes',{track:'Mirage call',start_bar:1,bars:32,notes:[...phrase(theme,8),...phrase(answer,16),...phrase(theme.slice(0,4),24),...phrase([[['E5',.5,1,56]],[['D5',.5,1,52]],[['F5',.5,.75,53]],[['E5',.5,2.6,59]]],28)],name:'E-F-G mirage and falling answer',...A});
for(const [name,at_bar] of [['Salt after sunset',1],['The old mirage',9],['Glass answers',17],['Dune settles',25]])await call(c,'add_marker',{name,at_bar,...A});
const a=await call(c,'analyse_song',A);
console.log('PRISM_DAY_SOURCE',sourceId);
console.log('PRISM_NIGHT',JSON.stringify({id:A.project_id,length:a.length,problems:a.problems,warnings:a.warnings}));
await c.close();
JS
