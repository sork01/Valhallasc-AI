const fs = require('node:fs');
const path = require('node:path');
const kit = require('./tools.cjs');
const map = JSON.parse(fs.readFileSync(path.join(__dirname, '../../world/map.txt'), 'utf8'));
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../../world/cathedral.txt'), 'utf8'));
const bossKind = kind => catalog.find(e => e.kind === kind)?.boss;
const levels = JSON.parse(fs.readFileSync(path.join(__dirname, '../../world/levels.txt'), 'utf8'));
const totalXp = p => p.xp + levels.slice(0, p.level - 1).reduce((a,b)=>a+b,0);

module.exports = {
  description: 'Three Cathedral wings: real level-gated entries, party/private-copy isolation, shared and exclusive enemies, real combat, boss rolls, all-four clears, exits, reconnect and restart.',
  startLevel: 50, godMode: true, levelSpread: 0,
  async run(w, check) {
    const bot='Cathedral', mate='Choirfriend', stranger='OtherChoir';
    for (const [b,c] of [[bot,'warrior'],[mate,'priest'],[stranger,'mage']]) await w.connect({bot:b,class:c});
    for (const b of [bot,mate]) for (let n=0;n<4;n++) await w.debug(b,{op:'give_item',item:'traveler_pack',quantity:1});
    await w.social(bot,{op:'party_invite',bot:mate});
    await w.social(mate,{op:'party_accept',bot});
    const view=b=>w.views.get(b);
    const enter = async (b,zone) => {
      const door=map.zones[8].portals.find(p=>p.to===zone);
      await kit.teleport(w,b,{zone:9,x:door.x,y:door.y+4});
      await w.action(b,{type:'move',x:door.x,y:door.y});
      await w.waitFor(()=>w.player(b)?.zone===zone,10000,'Walk through Cathedral door');
      await w.action(b,{type:'stop'});
    };
    for (const zone of [10,11,12]) {
      const z=map.zones[zone-1], level=z.min_level;
      check(z.players===5 && z.copies===4 && z.levels.join()===`${level},${level}`,`${z.name}: five-player level-${level} wing with four copies`);
      await kit.setupCharacter(w,bot,{level:level-1});
      const door=map.zones[8].portals.find(p=>p.to===zone);
      await kit.teleport(w,bot,{zone:9,x:door.x,y:door.y+4});
      const before=new Set(w.events);
      await w.action(bot,{type:'move',x:door.x,y:door.y});
      await w.waitFor(()=>w.events.some(e=>!before.has(e)&&e.bot===bot&&e.type==='error'&&e.text.includes(`level ${level}`)),10000,'Level gate refusal');
      await w.action(bot,{type:'stop'});
      check(w.player(bot).zone===9,`Level ${level-1} cannot enter ${z.cathedralWing}`);
      await kit.teleport(w,bot,{zone:9,x:door.x,y:door.y+4});
      await kit.setupCharacter(w,bot,{level:50});
      await enter(bot,zone);await enter(mate,zone);await enter(stranger,zone);
      await w.waitFor(()=>view(mate).slimes.length===20 && view(stranger).slimes.length===20);
      check(view(bot).slimes.every(s=>s.level===level&&s.zone===zone),`Every encounter is exactly level ${level}, labelled with its public wing`);
      check(view(bot).slimes.map(s=>s.id).join()===view(mate).slimes.map(s=>s.id).join(),'Party members see the same private enemy IDs');
      check(view(bot).slimes.every(s=>!view(stranger).slimes.some(q=>q.id===s.id)),'Strangers see distinct private enemy IDs');
      const exclusive=['tideleech','reliccrab','abysszealot'][zone-10];
      check(view(bot).slimes.filter(s=>s.kind===exclusive).length===4 && view(bot).slimes.filter(s=>bossKind(s.kind)).length===4,'Four exclusive trash enemies and four unique bosses');
      const target=view(bot).slimes.find(s=>s.kind==='tidetemplar');
      await kit.teleport(w,bot,{zone,x:target.x-2,y:target.y});
      await w.action(bot,{type:'target',id:target.id});
      await w.waitFor(()=>view(bot).slimes.find(s=>s.id===target.id).hp<target.maxHp,10000,'A real Cathedral combat hit');
      await w.action(bot,{type:'stop'});
      check(view(stranger).slimes.filter(s=>s.kind==='tidetemplar').every(s=>s.hp===s.maxHp),'Real combat cannot hurt the other private copy');
      const bosses=view(bot).slimes.filter(s=>bossKind(s.kind)).sort((a,b)=>Number(b.kind===z.final_boss)-Number(a.kind===z.final_boss));
      for (let n=0;n<bosses.length;n++) {
        const boss=bosses[n];
        await kit.teleport(w,bot,{zone,x:boss.x-3,y:boss.y});
        await kit.teleport(w,mate,{zone,x:boss.x-4,y:boss.y+1});
        const earlier=new Set(w.events);
        const xpBefore=[totalXp(w.player(bot)),totalXp(w.player(mate))];
        const goldBefore=w.player(bot).gold+w.player(mate).gold;
        await w.debug(bot,{op:'kill_enemy',id:boss.id});
        await w.advance(550); // A fellowship level can change on this kill; allow its party packet to arrive.
        const xpPercent=w.bots.get(bot).social.party.xp.xpPercent;
        const expectedXp=Math.max(1,Math.floor(((45+5*boss.level)*12*xpPercent+50)/100));
        await w.waitFor(()=>[bot,mate].every((b,i)=>totalXp(w.player(b))-xpBefore[i]===expectedXp),3000,'Both party XP snapshots');
        check([bot,mate].every((b,i)=>totalXp(w.player(b))-xpBefore[i]===expectedXp),`${boss.kind}: level-derived boss XP reaches both nearby party members`);
        const count=boss.kind===z.final_boss?2:1;
        const rolls=await w.waitFor(()=>{
          const all=w.events.filter(e=>!earlier.has(e)&&e.bot===bot&&e.type==='roll'&&e.op==='start');return all.length>=count&&all;
        },5000,'Guaranteed shared boss loot rolls');
        check(rolls.every(r=>w.events.some(e=>!earlier.has(e)&&e.bot===mate&&e.type==='roll'&&e.op==='start'&&e.id===r.id)),`${boss.kind}: one shared roll per pool, both nearby party members eligible`);
        for (const r of rolls) { await w.action(bot,{type:'roll',id:r.id,choice:'greed'});await w.action(mate,{type:'roll',id:r.id,choice:'pass'}); }
        const corpse=view(bot).slimes.find(s=>s.id===boss.id);
        await w.action(bot,{type:'move',x:corpse.x,y:corpse.y});
        await w.waitFor(()=>w.player(bot).gold+w.player(mate).gold>goldBefore,5000,'Collect real shared boss gold');
        const material=catalog.find(e=>e.kind===boss.kind).material;
        await w.waitFor(()=>[bot,mate].some(b=>w.player(b).inventory.some(i=>i.item===material)),5000,'Collect real boss material');
        check([bot,mate].some(b=>w.player(b).inventory.some(i=>i.item===material)),`${boss.kind}: shared gold and its unique material collect through real movement`);
        await w.action(bot,{type:'stop'});
        await w.waitFor(()=>view(bot).instance.cleared===(n===3));
        check(view(bot).instance.cleared===(n===3),`${boss.kind}: exit ${n===3?'opens after all four':'stays closed'}`);
        check(!view(stranger).instance.cleared && view(stranger).slimes.filter(s=>bossKind(s.kind)).every(s=>!s.dead),'Other party bosses and exit remain untouched');
      }
      const exit=z.portals.find(p=>p.after_clear);
      await kit.teleport(w,bot,{zone,x:exit.x,y:exit.y});
      await w.waitFor(()=>w.player(bot).zone===9,5000,'Cleared exit');
      check(Math.hypot(w.player(bot).x-exit.tx,w.player(bot).y-exit.ty)<1,'Cleared exit returns safely to Nacrehold');
      await kit.teleport(w,mate,{zone:9,x:96,y:35});
      await kit.teleport(w,stranger,{zone:9,x:108,y:35});
      await w.advance(300);
      await enter(bot,zone);
      check(!view(bot).instance.cleared && view(bot).slimes.every(s=>!s.dead && s.level===level),'Empty private wing resets all bosses, trash levels and exit');
      await w.disconnect(bot);await w.connect({bot});
      check(w.player(bot).zone===9,'Logging back in leaves the transient private wing at its city entrance');
    }
    await w.restart();
    check(w.player(bot).zone===9 && w.player(mate).zone===9,'Rust restart preserves safe character positions');
  },
};
