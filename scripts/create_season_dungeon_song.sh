#!/bin/sh
# Compose and render a new dungeon score with dybase2's MCP server.
set -eu
theme="$1"
case "$theme" in blooming_labyrinth|solar_crucible|amber_archive|silent_solstice) ;; *) echo 'Choose a Yearwheel dungeon theme' >&2; exit 2;; esac
cd "$(dirname "$0")/../../dybase2"
exec env DUNGEON_THEME="$theme" /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const theme=process.env.DUNGEON_THEME;
const bloom=theme==='blooming_labyrinth';
const scores={
 blooming_labyrinth:{title:'Petals Beyond the Door',bpm:84,key:'D major',chords:'D G Bm A D Em G A D G Bm A D Em G A',melody:['D4','F#4','A4','B4','A4','G4','F#4','E4']},
 solar_crucible:{title:'The Furnace of Noon',bpm:112,key:'E major',chords:'E A C#m B E F#m A B E A C#m B E F#m A B',melody:['E4','G#4','B4','C#5','B4','A4','G#4','F#4']},
 amber_archive:{title:'The Book of Falling Leaves',bpm:90,key:'G major',chords:'G Em C D G Bm C D G Em C D Am Bm C D',melody:['G4','B4','D5','C5','B4','A4','G4','E4']},
 silent_solstice:{title:'The Longest Night',bpm:72,key:'B minor',chords:'Bm G Em F# Bm D G F# Bm G Em F# D A G F#',melody:['B3','D4','F#4','A4','F#4','E4','D4','C#4']}
};
const client=new Client({name:`valhallasc-${theme}-music`,version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}) {const r=await client.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text);}
const {title,bpm,key,chords,melody}=scores[theme];
const project=await call('create_project',{name:`Valhalla ${theme} - ${title}`,bpm,time_signature:'4/4',key});
const A={project_id:project.project_id};
for(const [name,preset,volume_db] of [
 ['Foundation','WOOD BASS',-17],['Pulse','MARIMBA',-19],['Theme','WHISTLE FLUTE',-18],
 ['Halo','GLASS PAD',-26],['Echo','GLASS VIBES',-27],['Steps','LOG DRUM',-23]
])await call('add_track',{name,instrument:'dexed',preset,volume_db,...A});
await call('write_chords',{track:'Foundation',start_bar:1,bars:16,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Pulse',start_bar:1,bars:16,progression:chords,style:'arp_updown',register:63,rate:1,velocity:62,...A});
await call('write_chords',{track:'Halo',start_bar:1,bars:16,progression:chords,style:'block',register:53,velocity:39,...A});
await call('write_chords',{track:'Echo',start_bar:9,bars:8,progression:chords.split(' ').slice(8).join(' '),style:'arp_updown',register:76,rate:1,velocity:36,...A});
const notes=[];
for(let bar=0;bar<16;bar++) {
 const b=bar*4,shift=(bar%4)*2;
 for(const [beat,idx,dur] of [[0,0,.75],[1,2,.5],[2,4,.75],[3,6,.5]])
  notes.push({pitch:melody[(idx+shift)%melody.length],beat:b+beat,beats:dur,velocity:bar>=8?74:61});
}
await call('write_notes',{track:'Theme',start_bar:1,bars:16,notes,name:title,...A});
const steps=[];for(let bar=0;bar<16;bar++){steps.push({pitch:'A2',beat:bar*4,beats:.25,velocity:62});steps.push({pitch:'C3',beat:bar*4+2,beats:.2,velocity:bloom?37:48});}
await call('write_notes',{track:'Steps',start_bar:1,bars:16,notes:steps,name:'Chamber pulse',...A});
await call('add_marker',{name:title,at_bar:1,...A});
await call('add_marker',{name:'The inner hall',at_bar:9,...A});
await call('add_fx_return',{name:'Chamber',effect:'sorkverb',...A});
for(const track of ['Theme','Halo','Echo'])await call('set_send',{track,fx_return:'Chamber',level_db:-27,...A});
await call('analyse_song',A);
const path=`/tmp/valhallasc-${theme}-dybase2.wav`;
const render=await call('render_audio',{project_id:project.project_id,path,per_track:true,tail_seconds:2});
console.log(JSON.stringify({theme,title,project_id:project.project_id,path,render}));
await client.close();
JS
