#!/bin/sh
# A spacious 64-bar Yearwheel score, composed as an editable dybase2 MCP project.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const client=new Client({name:'valhallasc-four-horizons',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}) {
  const r=await client.callTool({name,arguments:args},undefined,{timeout:180000});
  if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  const data=JSON.parse(r.content[0].text);
  console.log(name,JSON.stringify(data).slice(0,220));
  return data;
}
const project=await call('create_project',{name:'Valhalla Yearwheel - Four Horizons',bpm:100,time_signature:'4/4',key:'G major'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
  ['Horizon strings','sork60','Mellow Pad',-19],
  ['Distant choir','sork60','Juno Strings',-26],
  ['Earth bass','dexed','WOOD BASS',-20],
  ['Far horns','sork60','Soft Horn Section',-22],
  ['Rain notes','dexed','TINE PIANO',-29],
  ['Deep drum','dexed','LOG DRUM',-24],
]) await call('add_track',{name,instrument,preset,volume_db,...A});

const sections=[
  ['Dawn over the crossing','Em C G D Em C Am D'],
  ['Spring road','G D Em C G D C D'],
  ['Spring opens','G Bm Em C Am G C D'],
  ['Summer horizon','C G D Em C G Am D'],
  ['The wide sky','G D Em C G D C D'],
  ['Amber evening','Em C G D Em C Am D'],
  ['Winter stars','Bm G D A Bm G Em A'],
  ['Four horizons','C D G Em C D G G'],
];
for(let section=0;section<sections.length;section++) {
  const [name,progression]=sections[section],start_bar=1+section*8;
  await call('write_chords',{track:'Horizon strings',start_bar,bars:8,progression,style:'block',register:62,velocity:56,...A});
  await call('write_chords',{track:'Earth bass',start_bar,bars:8,progression,style:'root_fifth',octave:2,velocity:57,...A});
  if([2,3,4,6,7].includes(section))await call('write_chords',{track:'Distant choir',start_bar,bars:8,progression,style:'block',register:55,velocity:42,...A});
  await call('add_marker',{name,at_bar:start_bar,...A});
}

// Recurring four-bar theme with room between phrases; winter transposes it upward.
const melody=[];
function note(bar,pitch,beat,beats,velocity=65){melody.push({pitch,beat:(bar-1)*4+beat,beats,velocity});}
function motif(start,variant=0){
  const p=variant===1?['C5','E5','D5','E5','B4','D5']:variant===2?['B4','F#5','E5','F#5','C#5','E5']:['G4','D5','A4','B4','G4','D5'];
  note(start,p[0],0,1.4);note(start,p[1],2,1);
  note(start+1,p[2],0,2.6,60);
  note(start+2,p[3],.5,1.2);note(start+2,p[4],2.2,1.2,59);
  note(start+3,p[5],0,2.8,68);
}
motif(9);motif(17);motif(25,1);motif(33);motif(49,2);motif(57,1);
await call('write_notes',{track:'Far horns',start_bar:1,bars:64,notes:melody,name:'Across the seasons',...A});

// A little space and rain, heard only in the quieter stretches.
const droplets=[];
for(const [bar,pitches] of [[1,['E5','B4']],[3,['G5','D5']],[5,['E5','C5']],[7,['D5','A4']],
                              [13,['B4','G4']],[21,['E5','B4']],[41,['E5','B4']],[43,['G5','D5']],
                              [45,['E5','C5']],[47,['D5','A4']],[51,['F#5','D5']],[55,['E5','B4']]]){
  droplets.push({pitch:pitches[0],beat:(bar-1)*4,beats:1.2,velocity:44});
  droplets.push({pitch:pitches[1],beat:(bar-1)*4+2.5,beats:.7,velocity:35});
}
await call('write_notes',{track:'Rain notes',start_bar:1,bars:64,notes:droplets,name:'Far light',...A});

// Low, rare impacts give the peaks weight without a constant battle beat.
const drum=[];
for(let bar=25;bar<=40;bar++){
  drum.push({pitch:'A2',beat:(bar-1)*4,beats:.28,velocity:bar%8===1?76:57});
  if(bar%2===1)drum.push({pitch:'C3',beat:(bar-1)*4+2,beats:.2,velocity:41});
}
for(let bar=57;bar<=64;bar++){
  drum.push({pitch:'A2',beat:(bar-1)*4,beats:.28,velocity:bar===57?78:59});
  if(bar%2===1)drum.push({pitch:'C3',beat:(bar-1)*4+2,beats:.2,velocity:44});
}
await call('write_notes',{track:'Deep drum',start_bar:1,bars:64,notes:drum,name:'Distant thunder',...A});

await call('add_fx_return',{name:'Long valley',effect:'sorkverb',...A});
for(const [track,level_db] of [['Horizon strings',-26],['Distant choir',-25],['Far horns',-22],['Rain notes',-25]])
  await call('set_send',{track,fx_return:'Long valley',level_db,...A});
await call('analyse_song',A);
console.log('Four Horizons saved. Render with scripts/render_yearwheel_song.sh '+project.project_id);
await client.close();
JS
