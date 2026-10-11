#!/bin/sh
# Four eight-bar seasonal movements in one editable dybase2 project.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-yearwheel-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args},undefined,{timeout:180000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,200));return data;}
const project=await call('create_project',{name:'Valhalla Yearwheel - The Turning Sky',bpm:112,time_signature:'4/4',key:'C major'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,preset,volume_db] of [['Season marimba','MARIMBA',-16],['Four winds flute','WHISTLE FLUTE',-20],['Clock bells','GLASS VIBES',-25],['Sky pad','GLASS PAD',-29],['Earth bass','WOOD BASS',-18],['Turning drum','LOG DRUM',-21]])await call('add_track',{name,instrument:'dexed',preset,volume_db,...A});
const seasons=[
 {name:'Springmere',chords:'C Am F G C Am Dm G',notes:[['E5',0,.5],['G5',.75,.5],['A5',1.5,.5],['G5',2.5,1]]},
 {name:'Solhaven',chords:'F G Am C F Dm G C',notes:[['C6',0,.5],['A5',.75,.5],['G5',1.5,.5],['C6',2.5,1]]},
 {name:'Harvestwatch',chords:'Am F C G Am Dm F E',notes:[['A5',0,.75],['G5',1,.5],['E5',2,.5],['C5',3,.75]]},
 {name:'Rimehold',chords:'Em C G D Em Am D G',notes:[['E5',0,.75],['B4',1,.5],['D5',2,.5],['G5',3,.75]]},
];
for(let i=0;i<4;i++){
 const {name,chords,notes}=seasons[i],start_bar=1+i*8;
 await call('write_chords',{track:'Earth bass',start_bar,bars:8,progression:chords,style:'root_fifth',octave:2,velocity:74,...A});
 await call('write_chords',{track:'Season marimba',start_bar,bars:8,progression:chords,style:i%2?'arp_up':'arp_updown',register:65,rate:1,velocity:68,...A});
 await call('write_chords',{track:'Sky pad',start_bar,bars:8,progression:chords,style:'block',register:55,velocity:42,...A});
 await call('write_chords',{track:'Clock bells',start_bar,bars:8,progression:chords,style:'arp_updown',register:82,rate:1,velocity:i===3?34:43,...A});
 const phrase=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of notes)phrase.push({pitch,beat:bar*4+beat,beats,velocity:65+i*4});
 await call('write_notes',{track:'Four winds flute',start_bar,bars:8,notes:phrase,name,...A});
 await call('add_marker',{name,at_bar:start_bar,...A});
}
const beats=[];for(let bar=0;bar<32;bar++){
 beats.push({pitch:'A2',beat:bar*4,beats:.25,velocity:bar%8===0?81:63});
 beats.push({pitch:'C3',beat:bar*4+2,beats:.25,velocity:56});
 beats.push({pitch:'E3',beat:bar*4+3.5,beats:.15,velocity:39});
}
await call('write_notes',{track:'Turning drum',start_bar:1,bars:32,notes:beats,name:'The year turns',...A});
await call('add_fx_return',{name:'Open sky',effect:'sorkverb',...A});
for(const [track,level_db] of [['Four winds flute',-22],['Clock bells',-27],['Sky pad',-25]])await call('set_send',{track,fx_return:'Open sky',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_yearwheel_song.sh '+project.project_id);
await client.close();
JS
