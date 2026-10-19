#!/bin/sh
# Night arrangements on dybase2 copies of Lanternmere Dusk and Skaldholm Square.
# Original IDs: 78ccaf9528b4f367 (fen), 33779c41b20628f0 (city).
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-fen-city-night-remixes',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args) {
  const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});
  if(r.isError) throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  const d=JSON.parse(r.content[0].text);
  if(name==='analyse_song') console.log(name,JSON.stringify({project_id:d.project_id,length:d.length,harmony:d.harmony?.slice(0,8),problems:d.problems,warnings:d.warnings}));
  return d;
}
const n=(pitch,beat,beats,velocity=56)=>({pitch,beat,beats,velocity});
const phrase=(bars,meter,offset=0)=>bars.flatMap((bar,i)=>bar.map(([pitch,at,length,velocity])=>n(pitch,(i+offset)*meter+at,length,velocity)));

// Gloamfen: an A-F-G-A recollection sits over new chords and a 4/4 pulse.
// The source's six quick lantern eighths become two long offbeat replies.
{
  const project_id='631d2ccf54a0ea32',A={project_id};
  await call('open_project',A);
  await call('rename_project',{name:'Valhalla Gloamfen Night - Lights Across the Mere',...A});
  await call('set_tempo',{bpm:90,...A});
  await call('set_time_signature',{numerator:4,denominator:4,...A});
  await call('set_key',{key:'D dorian',...A});
  try { await call('remove_track',{track:'Bubbles',...A}); } catch { /* already removed */ }
  for(const [track,preset] of [['Pad','Mellow Pad'],['Strings','Juno Strings']])
    await call('set_instrument',{track,instrument:'sork60',preset,...A});
  await call('set_instrument',{track:'Flute',instrument:'dexed',preset:'WHISTLE FLUTE',...A});
  for(const [track,volume_db,pan] of [['Lanterns',-11,-.25],['Pad',-27,0],['Bass',-4,0],['Flute',-19,.15],['Fireflies',-21,.3],['Strings',-18,-.1],['Drums',-4,0]])
    await call('set_mix',{track,volume_db,pan,...A});
  const chords=[
    'Dm9 Fmaj7 G7 Am7 Dm7 G6 Cmaj7 Am7',
    'Dm9 Fmaj7 Bbmaj7 G7 Em7 Am7 Dm7 Dm7',
    'Dm9 Cmaj7 G7 Am7 Fmaj7 Bbmaj7 G7 Dm7',
    'G6 Am7 Fmaj7 Cmaj7 Dm9 G7 Am7 Dm7',
  ].join(' ').split(' ');
  await call('write_chords',{track:'Pad',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:54,velocity:45,name:'Stillwater harmony',...A});
  const roots={Dm9:'D2',Fmaj7:'F2',G7:'G2',Am7:'A1',Dm7:'D2',G6:'G2',Cmaj7:'C2',Bbmaj7:'Bb1',Em7:'E2'};
  const tones={Dm9:['D4','F4','A4'],Fmaj7:['F4','A4','C5'],G7:['G4','B4','D5'],Am7:['A3','C4','E4'],Dm7:['D4','F4','A4'],G6:['G4','B4','E5'],Cmaj7:['C4','E4','G4'],Bbmaj7:['Bb3','D4','F4'],Em7:['E4','G4','B4']};
  const bass=[],lanterns=[],fireflies=[],strings=[],drums=[];
  chords.forEach((chord,i)=>{
    const b=i*4,t=tones[chord];
    bass.push(n(roots[chord],b,2.5,i%8===0?59:49));
    lanterns.push(n(t[0],b+.75,.5,56),n(t[2],b+2.5,.45,49));
    if(i%4===3 && i>=8) fireflies.push(n(i%8===3?'A5':'D6',b+3,.5,35));
    if(i>=16 && i<28) strings.push(n(t[1],b+.25,3.2,41));
    if(i>=8 && i<28){drums.push(n(36,b,.12,42),n(38,b+2,.1,25));for(const at of [1.5,3.5])drums.push(n(42,b+at,.08,22));}
  });
  for(const [track,notes,name] of [['Bass',bass,'One step through the marsh'],['Lanterns',lanterns,'Two lantern replies'],['Fireflies',fireflies,'Distant sparks'],['Strings',strings,'Mere counterlight'],['Drums',drums,'Lantern pulse']])
    await call('write_notes',{track,start_bar:1,bars:32,notes,name,...A});
  const callBars=[
    [['A4',.5,1.15,65],['F4',2.1,.5,54],['G4',3.1,.5,56]],
    [['A4',.5,1.3,64],['C5',2.35,.5,55],['A4',3.1,.55,54]],
    [['B4',.5,.7,60],['A4',1.75,.65,54],['G4',2.9,.75,56]],
    [['F4',.5,1,57],['A4',2,.6,59],['D5',3,.7,62]],
    [['A4',.5,.6,57],['F4',1.5,.6,53],['G4',2.5,.6,55],['A4',3.35,.5,59]],
    [['C5',.5,1,61],['B4',2,.5,53],['G4',3,.65,55]],
    [['E5',.5,.8,62],['D5',1.75,.6,55],['C5',2.75,.8,56]],
    [['A4',.5,.6,55],['G4',1.5,.5,53],['D4',2.75,1,58]],
  ];
  const answerBars=[
    [['D5',.25,.9,60],['A4',1.75,.55,53],['F4',2.75,.85,55]],
    [['C5',.5,.7,58],['A4',1.75,.65,54],['F4',3,.5,52]],
    [['B4',.5,.6,56],['D5',1.6,.6,59],['G5',2.8,.7,58]],
    [['E5',.5,1,61],['C5',2,.5,54],['A4',3,.65,54]],
    [['F4',.5,.6,54],['A4',1.5,.65,58],['D5',2.75,.8,61]],
    [['D5',.5,.7,58],['Bb4',1.75,.65,53],['A4',3,.55,54]],
    [['G4',.5,.5,54],['B4',1.5,.65,56],['D5',2.75,.8,60]],
    [['A4',.5,.6,57],['G4',1.5,.5,53],['D4',2.75,1,58]],
  ];
  await call('write_notes',{track:'Flute',start_bar:1,bars:32,notes:[...phrase(callBars,4,8),...phrase(answerBars,4,16),...phrase(callBars.slice(0,4),4,24),...phrase([[['D5',.5,1,59],['A4',2,.75,53]],[['G4',.5,.75,54],['F4',2,.75,51]],[['A4',.5,.8,57],['G4',2,.6,53]],[['D4',.5,2.7,59]]],4,28)],name:'Lantern call and water answer',...A});
  for(const [name,at_bar] of [['Dark water',1],['Lantern call',9],['Mere answers',17],['Fog returns',29]])await call('add_marker',{name,at_bar,...A});
  await call('analyse_song',A);
  console.log('FEN_NIGHT_PROJECT_ID='+project_id);
}

// Skaldholm: the daytime B-E-G ascent becomes a triple-time night waltz.
// Harp and bells converse in the square after the market drums have stopped.
{
  const project_id='32550162e477d9e7',A={project_id};
  await call('open_project',A);
  await call('rename_project',{name:'Valhalla Skaldholm Night - The Last Lantern',...A});
  await call('set_tempo',{bpm:90,...A});
  await call('set_time_signature',{numerator:3,denominator:4,...A});
  await call('set_key',{key:'E minor',...A});
  try { await call('remove_track',{track:'Drums',...A}); } catch { /* already removed */ }
  for(const track of ['Harp','Pad','Bass','Flute','Strings','Bells'])
    await call('clear_bars',{track,from_bar:33,bars:12,...A});
  for(const [track,preset] of [['Pad','Mellow Pad'],['Flute','Unison Lead'],['Strings','Juno Strings']])
    await call('set_instrument',{track,instrument:'sork60',preset,...A});
  for(const [track,volume_db,pan] of [['Harp',-12,-.25],['Pad',-27,0],['Bass',0,0],['Flute',-27,.1],['Strings',-17,.2],['Bells',-17,.35]])
    await call('set_mix',{track,volume_db,pan,...A});
  const chords=[
    'Em7 Bm7 Cmaj7 B7 Em7 Am7 D7 Gmaj7',
    'Cmaj7 B7 Em7 D7 Am7 Cmaj7 B7 Em7',
    'Em7 Gmaj7 Cmaj7 Am7 F#m7 B7 Em7 Cmaj7',
    'Gmaj7 D7 Am7 B7 Cmaj7 B7 Em7 Em7',
  ].join(' ').split(' ');
  await call('write_chords',{track:'Pad',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:55,velocity:44,name:'Empty square chords',...A});
  const roots={Em7:'E2',Bm7:'B1',Cmaj7:'C2',B7:'B1',Am7:'A1',D7:'D2',Gmaj7:'G2','F#m7':'F#2'};
  const tones={Em7:['E4','G4','B4'],Bm7:['B3','D4','F#4'],Cmaj7:['C4','E4','G4'],B7:['B3','D#4','F#4'],Am7:['A3','C4','E4'],D7:['D4','F#4','A4'],Gmaj7:['G3','B3','D4'],'F#m7':['F#3','A3','C#4']};
  const harp=[],bass=[],bells=[],strings=[];
  chords.forEach((chord,i)=>{
    const b=i*3,t=tones[chord];
    bass.push(n(roots[chord],b,2.3,i%8===0?59:48));
    harp.push(n(t[0],b,.55,55),n(t[1],b+1.1,.42,45),n(t[2],b+2.1,.42,47));
    if(i>=8 && i%4===3) bells.push(n(i%8===3?'E5':'B4',b+2,.65,38));
    if(i>=16 && i<28) strings.push(n(t[1],b+.1,2.6,39));
  });
  for(const [track,notes,name] of [['Bass',bass,'Quiet steps around the square'],['Harp',harp,'Lantern waltz'],['Bells',bells,'Town clock replies'],['Strings',strings,'Sleep over the rooftops']])
    await call('write_notes',{track,start_bar:1,bars:32,notes,name,...A});
  const cityTheme=[
    [['B4',.25,.6,59],['E5',1.1,.7,64],['G5',2.15,.6,62]],
    [['F#5',.4,.8,58],['D5',1.65,.8,53]],
    [['E5',.3,.55,59],['G5',1.2,.6,61],['B5',2.2,.55,59]],
    [['A5',.4,.6,56],['F#5',1.35,.6,54],['D#5',2.25,.5,55]],
    [['G5',.4,.9,61],['E5',1.75,.6,56]],
    [['C5',.35,.6,54],['E5',1.35,.65,59],['A5',2.3,.5,57]],
    [['F#5',.4,.65,58],['D5',1.45,.65,53],['B4',2.4,.45,51]],
    [['E5',.4,2.25,61]],
  ];
  const cityAnswer=[
    [['G4',.35,.55,55],['B4',1.25,.55,59],['E5',2.1,.7,61]],
    [['F#5',.45,.8,57],['D#5',1.8,.65,53]],
    [['B4',.35,.6,55],['E5',1.35,.7,60],['G5',2.25,.55,58]],
    [['A5',.4,.8,58],['F#5',1.8,.65,54]],
    [['C5',.35,.55,54],['E5',1.25,.55,58],['G5',2.1,.7,59]],
    [['B4',.5,.75,56],['G4',1.75,.7,52]],
    [['F#4',.4,.6,52],['A4',1.4,.6,56],['B4',2.3,.55,58]],
    [['E5',.4,2.25,60]],
  ];
  await call('write_notes',{track:'Flute',start_bar:1,bars:32,notes:[...phrase(cityTheme,3,8),...phrase(cityAnswer,3,16),...phrase(cityTheme.slice(0,7),3,24),...phrase([[['E5',.4,2.2,60]]],3,31)],name:'Square melody at night',...A});
  for(const [name,at_bar] of [['The square empties',1],['Last lantern',9],['Rooftop answer',17],['The town sleeps',25]])await call('add_marker',{name,at_bar,...A});
  await call('analyse_song',A);
  console.log('CITY_NIGHT_PROJECT_ID='+project_id);
}
await c.close();
JS
