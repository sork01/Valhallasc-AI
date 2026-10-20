#!/bin/sh
# Remix the active Z16, Z17, Z19 and Z20 daytime dybase2 projects.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

async function connect(owner) {
  const c = new Client({name:`valhallasc-next-four-night-${owner}`,version:'1'});
  await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:owner}}));
  return c;
}
async function call(c,name,args) {
  const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});
  if(r.isError) throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  return JSON.parse(r.content[0].text);
}
const n=(pitch,beat,beats,velocity=55)=>({pitch,beat,beats,velocity});
const sectionNames=['Dusk','Lantern theme','Night answer','Before dawn'];
const specs=[
  {zone:'moonspore',source:'84f85129e73403dd',title:'Valhalla Moonspore Night - Spores Beneath the Stars',bpm:82,meter:'6/8',key:'G dorian',beats:3,
    pad:'Moonlit leaves',bass:'Root pulse',pluck:'Spore drops',lead:'Lantern song',
    instruments:[['Moonlit leaves','sork60','Mellow Pad'],['Root pulse','sorkbass2','Fingered'],['Spore drops','dexed','GLASS VIBES'],['Lantern song','sork60','Unison Lead']],
    mix:[['Moonlit leaves',-28,0],['Root pulse',-4,0],['Spore drops',-19,.24],['Lantern song',-19,-.12]],
    cycles:[['Gm7','C7','Gm7','Fmaj7','Bbmaj7','C7','Fmaj7','Gm7'],['Gm7','C7','Fmaj7','Bbmaj7','Gm7','C7','Fmaj7','Gm7'],['C7','Fmaj7','Bbmaj7','C7','Gm7','Fmaj7','C7','Gm7'],['Gm7','C7','Fmaj7','Bbmaj7','C7','C7','Gm7','Gm7']],
    roots:{Gm7:'G2',C7:'C2',Fmaj7:'F2',Bbmaj7:'Bb1'},
    tones:{Gm7:['G4','Bb4','D5','F5'],C7:['G4','Bb4','C5','E5'],Fmaj7:['A4','C5','E5','F5'],Bbmaj7:['A4','Bb4','D5','F5']},
    padRegister:54,padVelocity:43,bassHits:[[0,2.2,55]],pluckHits:[[.5,1,.42,51],[2,2,.42,44]],
    motifs:{8:[['G4',.5,.45],['Bb4',1,.45],['D5',1.5,.9]],9:[['E5',.5,.8],['D5',1.5,.4],['C5',2,.65]],16:[['D5',.5,.7],['Bb4',1.5,.4],['G4',2,.7]],17:[['C5',.5,.7],['A4',1.5,.4],['G4',2,.65]]},
    drum:{kick:[0,8],snare:[6],hat:[2,4,6,10],rim:[11]},drumVelocity:56,
    markers:['Spore dusk','Lanterns wake','Roots answer','The canopy sleeps']},
  {zone:'asterion',source:'5e715b4a47a849bc',title:'Valhalla Asterion Night - The Eighth Quiet Ring',bpm:92,meter:'4/4',key:'E minor',beats:4,
    pad:'City strings',bass:'Deep pulse',pluck:'Glass wheel',lead:'Brass procession',bell:'Thirteen bells',other:'Sky choir',oldDrum:'Moon drums',
    instruments:[['City strings','sork60','Mellow Pad'],['Deep pulse','sorkbass2','Fingered'],['Glass wheel','sork60','Clavinet'],['Brass procession','sork60','Juno Brass'],['Thirteen bells','dexed','TUB BELLS'],['Sky choir','sork60','Juno Strings']],
    mix:[['City strings',-27,0],['Deep pulse',-5,0],['Glass wheel',-17,-.24],['Brass procession',-23,.08],['Thirteen bells',-23,.3],['Sky choir',-28,-.1]],
    cycles:[['Em7','Cmaj7','Gmaj7','D7','Em7','Am7','Cmaj7','B7'],['Em7','Cmaj7','Gmaj7','D7','Am7','Cmaj7','B7','Em7'],['Cmaj7','Gmaj7','Am7','Em7','Cmaj7','D7','B7','Em7'],['Em7','D7','Cmaj7','Gmaj7','Am7','Cmaj7','B7','Em7']],
    roots:{Em7:'E2',Cmaj7:'C2',Gmaj7:'G2',D7:'D2',Am7:'A1',B7:'B1'},
    tones:{Em7:['E4','G4','B4','E5'],Cmaj7:['E4','G4','B4','C5'],Gmaj7:['G4','B4','D5','F#5'],D7:['F#4','A4','C5','D5'],Am7:['E4','G4','A4','C5'],B7:['F#4','A4','B4','D#5']},
    padRegister:54,padVelocity:41,bassHits:[[0,1.4,55],[2.75,.6,40]],pluckHits:[[.5,1,.42,48],[3,2,.35,40]],
    motifs:{8:[['E5',.5,.6],['G5',1.5,.6],['B5',2.5,1]],9:[['G5',.5,.6],['E5',2,1]],16:[['D5',.5,.7],['B4',1.75,.6],['G4',3,.65]],17:[['E5',.5,.6],['B4',2,1]]},
    drum:{kick:[0,11],snare:[8],hat:[2,6,10,14],rim:[15]},drumVelocity:60,
    markers:['Balcony at dusk','Seven rings remembered','The choir replies','Last bell']},
  {zone:'stormglass',source:'2c200357fd474fbb',title:'Valhalla Stormglass Night - The Lighthouse Tide',bpm:88,meter:'4/4',key:'E minor',beats:4,
    pad:'Sea mist',bass:'Undertow bass',pluck:'Glass current',lead:'Breaker strings',bell:'Storm bell',oldDrum:'Shore pulse',
    instruments:[['Sea mist','sork60','Mellow Pad'],['Undertow bass','sorkbass2','Fingered'],['Glass current','sork60','Clavinet'],['Breaker strings','sork60','Vibrato Lead'],['Storm bell','dexed','TUB BELLS']],
    mix:[['Sea mist',-27,0],['Undertow bass',-6,0],['Glass current',-16,-.25],['Breaker strings',-20,.12],['Storm bell',-24,.32]],
    cycles:[['Em7','A7','Dmaj7','Gmaj7','Em7','Cmaj7','B7','Em7'],['Em7','A7','Dmaj7','Gmaj7','Cmaj7','A7','B7','Em7'],['Cmaj7','Gmaj7','Dmaj7','A7','Em7','Cmaj7','B7','Em7'],['Em7','A7','Dmaj7','Gmaj7','Cmaj7','B7','Em7','Em7']],
    roots:{Em7:'E2',A7:'A1',Dmaj7:'D2',Gmaj7:'G2',Cmaj7:'C2',B7:'B1'},
    tones:{Em7:['E4','G4','B4','E5'],A7:['E4','G4','A4','C#5'],Dmaj7:['F#4','A4','C#5','D5'],Gmaj7:['G4','B4','D5','F#5'],Cmaj7:['E4','G4','B4','C5'],B7:['F#4','A4','B4','D#5']},
    padRegister:53,padVelocity:42,bassHits:[[0,1.45,55],[3.25,.5,43]],pluckHits:[[.5,1,.4,50],[2.5,2,.4,43]],
    motifs:{8:[['E5',.5,.6],['G5',1.5,.6],['B5',2.5,1]],9:[['G5',.5,.7],['E5',2,1]],16:[['A5',.5,.65],['G5',1.75,.6],['E5',3,.7]],17:[['E5',.5,.7],['D5',2,1]]},
    drum:{kick:[0,7,13],snare:[8],hat:[2,5,10,14],rim:[15]},drumVelocity:58,
    markers:['The dark surf','A lamp beyond water','The breakers answer','Harbor glow']},
  {zone:'sunward',source:'e59a59732cb42ace',title:'Valhalla Sunward Night - Orchard Lanterns',bpm:90,meter:'4/4',key:'G major',beats:4,
    pad:'Warm strings',bass:'Walking bass',pluck:'Millwheel marimba',lead:'Hillside flute',other:'Plucked strings',oldDrum:'Wooden hand drum',
    instruments:[['Warm strings','sork60','Mellow Pad'],['Walking bass','sorkbass2','Fingered'],['Millwheel marimba','dexed','MARIMBA'],['Hillside flute','dexed','WHISTLE FLUTE'],['Plucked strings','sork60','Clavinet']],
    mix:[['Warm strings',-26,0],['Walking bass',-5,0],['Millwheel marimba',-12,-.25],['Hillside flute',-13,.12],['Plucked strings',-20,.3]],
    cycles:[['Gmaj7','D7','Em7','Cmaj7','Gmaj7','Am7','D7','Gmaj7'],['Gmaj7','D7','Em7','Cmaj7','Am7','Cmaj7','D7','Gmaj7'],['Cmaj7','Gmaj7','Am7','Em7','Cmaj7','D7','Am7','Gmaj7'],['Gmaj7','D7','Em7','Cmaj7','Am7','D7','Gmaj7','Gmaj7']],
    roots:{Gmaj7:'G2',D7:'D2',Em7:'E2',Cmaj7:'C2',Am7:'A1'},
    tones:{Gmaj7:['G4','B4','D5','F#5'],D7:['F#4','A4','C5','D5'],Em7:['E4','G4','B4','E5'],Cmaj7:['E4','G4','B4','C5'],Am7:['E4','G4','A4','C5']},
    padRegister:55,padVelocity:42,bassHits:[[0,1.8,53],[2.5,.6,40]],pluckHits:[[0,1,.38,48],[2.5,2,.45,44]],
    motifs:{8:[['G5',.5,.6],['B5',1.5,.6],['D6',2.5,1]],9:[['A5',.5,.7],['G5',2,1]],16:[['E5',.5,.7],['D5',1.75,.6],['B4',3,.7]],17:[['D5',.5,.7],['B4',2,1]]},
    drum:{kick:[0,10],snare:[4,12],hat:[2,6,10,14],rim:[15]},drumVelocity:54,
    markers:['The orchard dims','Hillside flute','Millwheel answer','Morning on the path']},
];

const c=await connect('codex');
async function openNight(spec) {
  const my=(await call(c,'list_projects',{mine_only:true})).projects;
  const old=my.find(p=>p.name===spec.title);
  if(old) return (await call(c,'open_project',{project_id:old.id})).project_id;
  let source=spec.source;
  if(spec.zone==='moonspore') {
    // Same-owner open would edit the daytime source. Copy it under a bridge owner first.
    const bridge=await connect('valhallasc_night_source');
    const copied=await call(bridge,'open_project',{project_id:source});
    if(copied.copied_from?.id!==source) throw Error('Moonspore bridge did not copy the day source');
    source=copied.project_id;
    await call(bridge,'rename_project',{project_id:source,name:'Valhalla Moonspore night source bridge'});
    await bridge.close();
  }
  const opened=await call(c,'open_project',{project_id:source});
  if(opened.copied_from?.id!==source) throw Error(`${spec.zone}: expected an editable copy`);
  return opened.project_id;
}
function line(spec,chords,section) {
  const out=[];
  for(let bar=0;bar<8;bar++) {
    const absolute=section*8+bar, base=bar*spec.beats;
    const motif=spec.motifs[absolute];
    if(motif) {for(const [pitch,at,duration] of motif) out.push(n(pitch,base+at,duration,section===1?62:57));continue;}
    const t=spec.tones[chords[absolute]], compound=spec.beats===3;
    const shape=section===2 ? [[t[3],.5,.7],[t[2],compound?1.5:2,.5],[t[0],compound?2:3,.6]]
      : section===3 && bar>=5 ? [[t[2],.5,.6],[t[0],compound?1.5:2.5,compound?1.2:1]]
      : bar%2 ? [[t[2],.5,.65],[t[0],compound?1.75:2.5,compound?.7:1]]
      : [[t[0],.5,.55],[t[1],compound?1.25:1.5,.55],[t[2],compound?2:2.75,.6]];
    for(const [pitch,at,duration] of shape) out.push(n(pitch,base+at,duration,section===0?48:section===2?57:54));
  }
  return out;
}
function drumRow(steps,hits,accent=[]) {const row=Array(steps).fill('.');for(const p of hits)row[p]=accent.includes(p)?'X':'x';return row.join('')}
for(const spec of specs) {
  if(process.env.ZONES&&!process.env.ZONES.split(',').includes(spec.zone)) continue;
  const project_id=await openNight(spec), A={project_id};
  const day=await call(c,'open_project',A);
  if(day.project_id===spec.source) throw Error(`${spec.zone}: refusing to edit daytime project`);
  await call(c,'rename_project',{...A,name:spec.title});
  await call(c,'set_tempo',{...A,bpm:spec.bpm});
  await call(c,'set_key',{...A,key:spec.key});
  for(const t of day.tracks.filter(t=>t.instrument)) await call(c,'clear_bars',{...A,track:t.name});
  if(spec.oldDrum&&day.tracks.some(t=>t.name===spec.oldDrum)) await call(c,'remove_track',{...A,track:spec.oldDrum});
  const noLead=['stormglass','sunward'].includes(spec.zone);
  for(const [track,instrument,preset] of spec.instruments) if(!noLead||track!==spec.lead) await call(c,'set_instrument',{...A,track,instrument,preset});
  for(const [track,volume_db,pan] of spec.mix) if(!noLead||track!==spec.lead) await call(c,'set_mix',{...A,track,volume_db,pan});
  for(const [parameter,value] of [['env.attack',.08],['env.release',.45]]) await call(c,'automate',{...A,track:spec.pad,parameter,points:[{bar:1,value},{bar:33,value}]});
  if(spec.other==='Sky choir') for(const [parameter,value] of [['env.attack',.08],['env.release',.5]]) await call(c,'automate',{...A,track:spec.other,parameter,points:[{bar:1,value},{bar:33,value}]});
  const chords=spec.cycles.flat();
  await call(c,'write_chords',{...A,track:spec.pad,start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:spec.padRegister,velocity:spec.padVelocity,name:'Night harmony'});
  const bass=[],pluck=[],bell=[],other=[];
  chords.forEach((chord,i)=>{
    const beat=i*spec.beats,t=spec.tones[chord];
    for(const [at,duration,velocity] of spec.bassHits) bass.push(n(spec.roots[chord],beat+at,duration,velocity+(i%8===0?5:0)));
    for(const [at,index,duration,velocity] of spec.pluckHits) pluck.push(n(t[index],beat+at,duration,velocity));
    if(spec.bell&&i%4===0) bell.push(n(t[3],beat,.55,i>=16&&i<24?43:35));
    if(spec.other==='Sky choir'&&i>=16&&i<28) other.push(n(t[0],beat,Math.min(spec.beats-.3,3.6),36));
    if(spec.other==='Plucked strings'&&i>=8&&i<24) other.push(n(t[1],beat+1.5,.45,34));
  });
  for(const [track,notes,name] of [[spec.bass,bass,'Steady night steps'],[spec.pluck,pluck,'Night reflections'],...(spec.bell?[[spec.bell,bell,'Distant landmark bells']]:[]),...(spec.other?[[spec.other,other,'Passing night colour']]:[])])
    await call(c,'write_notes',{...A,track,start_bar:1,bars:32,notes,name});
  if(noLead&&day.tracks.some(t=>t.name===spec.lead)) await call(c,'remove_track',{...A,track:spec.lead});
  if(!noLead) for(let section=0;section<4;section++) await call(c,'write_notes',{...A,track:spec.lead,start_bar:section*8+1,bars:8,notes:line(spec,chords,section),name:sectionNames[section]});
  if(!day.tracks.some(t=>t.name==='Night breakbeat')) await call(c,'add_track',{...A,name:'Night breakbeat',instrument:'axiom8',preset:'Hip-hop',volume_db:-12});
  else {await call(c,'clear_bars',{...A,track:'Night breakbeat'});await call(c,'set_preset',{...A,track:'Night breakbeat',preset:'Hip-hop'});}
  if(!day.tracks.some(t=>t.name==='Chillhop hi-hat')) await call(c,'add_track',{...A,name:'Chillhop hi-hat',instrument:'axiom8',preset:'Chillhop',volume_db:-10});
  else {await call(c,'clear_bars',{...A,track:'Chillhop hi-hat'});await call(c,'set_preset',{...A,track:'Chillhop hi-hat',preset:'Chillhop'});}
  const steps=spec.beats*4;
  for(let section=0;section<4;section++) {
    const b=spec.drum;
    const kick=b.kick;
    const hat=section===0?b.hat.filter((_,i)=>i%2===0):section===3?b.hat.filter((_,i)=>i%2===1):b.hat;
    await call(c,'write_drums',{...A,track:'Night breakbeat',start_bar:section*8+1,bars:8,
      pattern:{kick:drumRow(steps,kick,[0]),snare:drumRow(steps,b.snare),clap:drumRow(steps,section===1?b.rim:[])},
      swing:0,velocity:section===0?spec.drumVelocity-5:section===3?spec.drumVelocity-3:spec.drumVelocity,name:`${sectionNames[section]} break`});
    await call(c,'write_drums',{...A,track:'Chillhop hi-hat',start_bar:section*8+1,bars:8,
      pattern:{hat:drumRow(steps,hat)},swing:0,velocity:section===0?spec.drumVelocity-5:section===3?spec.drumVelocity-3:spec.drumVelocity,name:`${sectionNames[section]} Chillhop hats`});
  }
  for(const [index,name] of spec.markers.entries()) await call(c,'add_marker',{...A,name,at_bar:index*8+1});
  const a=await call(c,'analyse_song',A);
  if(a.problems?.length) throw Error(`${spec.zone}: ${a.problems.join('; ')}`);
  console.log('NIGHT',JSON.stringify({zone:spec.zone,source:spec.source,id:project_id,bpm:spec.bpm,meter:spec.meter,bars:32,seconds:32*spec.beats*60/spec.bpm,warnings:a.warnings}));
}
await c.close();
JS
