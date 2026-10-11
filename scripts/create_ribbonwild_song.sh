#!/bin/sh
# Compose an editable bright festival score through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'EOF'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const client=new Client({name:'valhallasc-ribbonwild-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,
  args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){
  const r=await client.callTool({name,arguments:args});
  if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  const data=JSON.parse(r.content[0].text);
  console.log(name,JSON.stringify(data).slice(0,240));return data;
}
const project=await call('create_project',{name:'Valhalla Ribbonwild - March of Many Colors',
  bpm:118,time_signature:'4/4',key:'D major'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
  ['Festival brass','dexed','BRASS SECT',-15],
  ['Painted clav','dexed','CLAV FUNK',-20],
  ['Bell garlands','dexed','TUB BELLS',-23],
  ['Silk strings','sork60','Juno Strings',-24],
  ['Parade bass','sorkbass2','Fingered',-17],
  ['Drum cart','dexed','LOG DRUM',-22],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const harmony=[
  'D A Bm G D Em A7 D',
  'G D Em A D Bm G A7',
  'Bm G D A Bm G Em A7',
  'D A Bm G Em A7 D D',
].join(' ');
await call('write_chords',{track:'Parade bass',start_bar:1,bars:32,progression:harmony,
  style:'root_fifth',octave:2,velocity:75,...A});
await call('write_chords',{track:'Painted clav',start_bar:1,bars:32,progression:harmony,
  style:'stabs',register:68,velocity:67,...A});
await call('write_chords',{track:'Silk strings',start_bar:1,bars:32,progression:harmony,
  style:'block',register:58,velocity:57,...A});
await call('write_chords',{track:'Bell garlands',start_bar:9,bars:24,
  progression:harmony.split(' ').slice(8).join(' '),style:'arp_updown',
  register:77,rate:1,velocity:46,...A});
const tune=[
 [['D5',0,.5],['F#5',.75,.5],['A5',1.5,.5],['D6',2.5,1]],
 [['C#6',0,.75],['B5',1,.5],['A5',2,1],['F#5',3,.5]],
 [['B5',0,.5],['D6',.75,.5],['F#6',1.5,.5],['D6',2.5,1]],
 [['B5',0,.75],['A5',1,.5],['G5',2,1.5]],
 [['A5',0,.5],['D6',.75,.5],['F#6',1.5,.5],['E6',2.5,1]],
 [['B5',0,.75],['G5',1,.5],['E5',2,1.5]],
 [['E5',0,.5],['G5',.75,.5],['A5',1.5,.5],['C#6',2.5,1]],
 [['D6',0,1],['A5',1.5,.75],['F#5',2.5,.5],['D5',3,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
  const notes=[];
  for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar]){
    const high=section===2&&bar%2===0?({'D5':'A5','F#5':'D6','A5':'F#6'}[pitch]||pitch):pitch;
    notes.push({pitch:high,beat:bar*4+beat,beats,velocity:section===0?72:section===3?91:82});
  }
  await call('write_notes',{track:'Festival brass',start_bar:start,bars:8,notes,
    name:['Opening procession','The color courts','Masks in motion','Curtain call'][section],...A});
}
const beats=[];
for(let bar=0;bar<32;bar++){
  beats.push({pitch:'D2',beat:bar*4,beats:.26,velocity:bar%8===0?77:64});
  beats.push({pitch:'A2',beat:bar*4+1.5,beats:.18,velocity:49});
  beats.push({pitch:'D3',beat:bar*4+2,beats:.24,velocity:60});
  beats.push({pitch:'A2',beat:bar*4+3.5,beats:.18,velocity:48});
}
await call('write_notes',{track:'Drum cart',start_bar:1,bars:32,notes:beats,
  name:'Processional wheels',...A});
for(const [name,at_bar] of [['Jubilee market',1],['Four color courts',9],
                             ['The parade gryphon',17],['Thousandfold Pavilion',25]])
  await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Open festival air',effect:'sorkverb',...A});
for(const [track,level_db] of [['Festival brass',-20],['Bell garlands',-26],['Silk strings',-25]])
  await call('set_send',{track,fx_return:'Open festival air',level_db,...A});
await call('analyse_song',A);
try{
  const render=await call('render_audio',{path:'/tmp/valhallasc-ribbonwild-dybase2.wav',
    per_track:false,tail_seconds:2,...A});
  console.log('WAV='+render.wav);
}catch(error){console.error('Render request timed out; check WAV:',error.message);}
await client.close();
EOF
