#!/bin/sh
# Remix editable transcriptions of the Python-rendered daytime scores.
# Source projects are 73ea9204eccdcd51 (Nacrehold) and 458db937b39462af (Astralhollow).
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-nacre-astral-night-remixes',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=55)=>({pitch,beat,beats,velocity});
const phrase=(bars,meter,offset)=>bars.flatMap((bar,i)=>bar.map(([pitch,at,length,velocity])=>n(pitch,(i+offset)*meter+at,length,velocity)));
const projects=(await call('list_projects',{mine_only:true})).projects;
async function openCopy(sourceId,title){
  const existing=projects.find(p=>p.name===title);
  const opened=await call('open_project',{project_id:existing?.id||sourceId});
  if(opened.copied_from?.id!==sourceId&&!existing)throw Error(`Expected a copy of ${sourceId}`);
  await call('rename_project',{project_id:opened.project_id,name:title});
  return {project_id:opened.project_id};
}

// Nacrehold: the daytime A-C question and G-E reply become longer 6/8
// phrases above relative-minor harmony. Two offbeat keys replace the broken
// three-note figure; the original score's absence of drums is preserved.
{
  const A=await openCopy('73ea9204eccdcd51','Valhalla Nacrehold Night - Pearls Beneath the Moon');
  await call('set_tempo',{bpm:90,...A});
  await call('set_time_signature',{numerator:6,denominator:8,...A});
  await call('set_key',{key:'D minor',...A});
  for(const track of ['Pad','Keys','Bass','Melody'])await call('clear_bars',{track,...A});
  for(const [track,volume_db,pan] of [['Pad',-27,0],['Keys',-11,-.2],['Bass',3,0],['Melody',-9,.15]])await call('set_mix',{track,volume_db,pan,...A});
  const chords=('Dm9 Bbmaj7 Fmaj7 Cadd9 Dm9 Gm7 Bbmaj7 Cadd9 '+
                'Fmaj7 Cadd9 Dm9 Bbmaj7 Gm7 Dm9 A7 Dm9 '+
                'Bbmaj7 Fmaj7 Gm7 Cadd9 Dm9 Bbmaj7 Gm7 A7 '+
                'Dm9 Cadd9 Bbmaj7 Fmaj7 Gm7 A7 Dm9 Dm9').split(' ');
  await call('write_chords',{track:'Pad',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:54,velocity:43,name:'Moonlit waterglass',...A});
  const roots={Dm9:'D2',Bbmaj7:'Bb1',Fmaj7:'F2',Cadd9:'C2',Gm7:'G1',A7:'A1'};
  const tones={Dm9:['D4','F4','A4'],Bbmaj7:['Bb3','D4','F4'],Fmaj7:['F3','A3','C4'],Cadd9:['C4','E4','G4'],Gm7:['G3','Bb3','D4'],A7:['A3','C#4','E4']};
  const bass=[],keys=[];
  chords.forEach((chord,i)=>{const b=i*3,t=tones[chord];
    bass.push(n(roots[chord],b,2.35,i%8===0?57:47));
    keys.push(n(t[1],b+.75,.65,53),n(t[2],b+2,.5,45));
  });
  await call('write_notes',{track:'Bass',start_bar:1,bars:32,notes:bass,name:'Tide under the streets',...A});
  await call('write_notes',{track:'Keys',start_bar:1,bars:32,notes:keys,name:'Two pearl reflections',...A});
  const callBars=[
    [['A4',.4,.7,59],['C5',1.35,.8,62]],
    [['G4',.45,.9,55],['E4',1.9,.7,51]],
    [['F4',.4,.7,55],['A4',1.4,.8,58]],
    [['G4',.45,.7,55],['C5',1.5,.9,60]],
    [['A4',.4,.95,59],['F4',1.95,.7,53]],
    [['G4',.45,.75,54],['Bb4',1.55,.8,57]],
    [['D5',.45,.8,59],['Bb4',1.8,.75,53]],
    [['G4',.45,.75,53],['E4',1.8,.85,51]],
  ];
  const answer=[
    [['C5',.4,.75,60],['A4',1.7,.8,54]],
    [['G4',.45,.75,54],['E4',1.8,.8,51]],
    [['A4',.4,.7,56],['D5',1.5,.85,60]],
    [['F5',.45,.75,59],['D5',1.8,.8,53]],
    [['Bb4',.4,.75,56],['G4',1.8,.8,52]],
    [['A4',.45,.8,58],['F4',1.8,.75,52]],
    [['E5',.45,.7,57],['C#5',1.5,.8,54]],
    [['D5',.45,2.1,61]],
  ];
  await call('write_notes',{track:'Melody',start_bar:1,bars:32,notes:[...phrase(callBars,3,8),...phrase(answer,3,16),...phrase(callBars.slice(0,4),3,24),...phrase([[['F4',.4,.8,54]],[['E4',.4,.8,51]],[['C#5',.4,.7,54]],[['D5',.4,2.1,59]]],3,28)],name:'Pearl question and moonlit answer',...A});
  for(const [name,at_bar] of [['City at rest',1],['Waterglass question',9],['Pearls reply',17],['Tide settles',25]])await call('add_marker',{name,at_bar,...A});
  const a=await call('analyse_song',A);
  console.log('NACRE_NIGHT',JSON.stringify({id:A.project_id,length:a.length,problems:a.problems,warnings:a.warnings}));
}

// Astralhollow: retain the source's C#-E-F# rise and five-beat measure, but
// exchange the busy wood figure for two starglass steps and a falling answer.
{
  const A=await openCopy('458db937b39462af','Valhalla Astralhollow Night - Garden of Distant Stars');
  await call('set_tempo',{bpm:96,...A});
  await call('set_key',{key:'F# minor',...A});
  for(const track of ['Strings','Bass','Wood','Melody','Glass'])await call('clear_bars',{track,...A});
  await call('set_instrument',{track:'Strings',instrument:'sork60',preset:'Mellow Pad',...A});
  for(const [track,volume_db,pan] of [['Strings',-27,0],['Bass',1,0],['Wood',-9,-.25],['Melody',-24,.12],['Glass',-9,.28]])await call('set_mix',{track,volume_db,pan,...A});
  const chords=('F#m9 Dmaj7 Eadd9 C#m7 F#m9 Amaj7 Bm7 C#m7 '+
                'Dmaj7 Amaj7 Eadd9 Bm7 F#m9 Dmaj7 C#m7 F#m9 '+
                'Bm7 Dmaj7 Eadd9 Amaj7 F#m9 C#m7 Dmaj7 Eadd9 '+
                'F#m9 Eadd9 Dmaj7 Amaj7 Bm7 C#m7 F#m9 F#m9').split(' ');
  await call('write_chords',{track:'Strings',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:56,velocity:42,name:'Quiet orbit harmony',...A});
  const roots={'F#m9':'F#2',Dmaj7:'D2',Eadd9:'E2','C#m7':'C#2',Amaj7:'A1',Bm7:'B1'};
  const tones={'F#m9':['F#3','A3','C#4','E4'],Dmaj7:['D4','F#4','A4','C#5'],Eadd9:['E4','G#4','B4','F#5'],'C#m7':['C#4','E4','G#4','B4'],Amaj7:['A3','C#4','E4','G#4'],Bm7:['B3','D4','F#4','A4']};
  const bass=[],wood=[],glass=[];
  chords.forEach((chord,i)=>{const b=i*5,t=tones[chord];
    bass.push(n(roots[chord],b,3.3,i%8===0?57:47));
    wood.push(n(t[1],b+.8,.5,52),n(t[3],b+3.2,.6,47));
    if(i>=8&&i<28&&i%4===3)glass.push(n(i%8===3?'C#6':'F#5',b+4,.7,34));
  });
  for(const [track,notes,name] of [['Bass',bass,'One orbit per bar'],['Wood',wood,'Two starglass steps'],['Glass',glass,'Far stars']])await call('write_notes',{track,start_bar:1,bars:32,notes,name,...A});
  const theme=[
    [['C#5',.5,.7,60],['E5',1.65,.65,56],['F#5',3.1,1.1,63]],
    [['E5',.6,.95,56],['C#5',2.7,1.25,53]],
    [['B4',.6,.75,54],['C#5',1.9,.7,55],['F#5',3.35,1,60]],
    [['G#4',.6,.9,53],['B4',2.3,.75,55],['C#5',3.7,.75,56]],
    [['C#5',.5,.75,58],['E5',1.85,.75,55],['F#5',3.35,.9,61]],
    [['A5',.6,1.15,60],['E5',3,1,53]],
    [['D5',.6,.85,55],['C#5',2.25,.8,53],['B4',3.65,.75,52]],
    [['C#5',.6,2.9,58]],
  ];
  const answer=[
    [['F#5',.6,1.05,60],['C#5',2.55,.75,53],['A4',3.7,.75,51]],
    [['D5',.6,.95,55],['A4',2.55,1.2,51]],
    [['E5',.6,.9,57],['C#5',2.35,.85,52],['B4',3.7,.7,51]],
    [['C#5',.6,.85,55],['G#4',2.4,1.25,51]],
    [['A4',.6,.75,53],['C#5',1.9,.7,56],['F#5',3.3,.95,60]],
    [['E5',.6,1.1,56],['C#5',2.9,1.1,52]],
    [['D5',.6,.9,55],['B4',2.7,1.1,52]],
    [['F#4',.6,3,57]],
  ];
  await call('write_notes',{track:'Melody',start_bar:1,bars:32,notes:[...phrase(theme,5,8),...phrase(answer,5,16),...phrase(theme.slice(0,4),5,24),...phrase([[['A4',.6,1,53]],[['G#4',.6,1,51]],[['E4',.6,1,50]],[['F#4',.6,2.9,57]]],5,28)],name:'Falling garden motif and star answer',...A});
  for(const [name,at_bar] of [['The impact sleeps',1],['Falling garden',9],['Distant stars answer',17],['Quiet orbit',25]])await call('add_marker',{name,at_bar,...A});
  const a=await call('analyse_song',A);
  console.log('ASTRAL_NIGHT',JSON.stringify({id:A.project_id,length:a.length,problems:a.problems,warnings:a.warnings}));
}
await c.close();
JS
