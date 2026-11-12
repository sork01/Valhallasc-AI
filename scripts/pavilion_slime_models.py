"""Six distinct Thousandfold Pavilion creatures, articulated in y-up coordinates."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, PEARL, GOLD, GREEN, BROWN, PINK, CORAL, CRIMSON, AMBER, PURPLE, VIOLET, AZURE, SLATE


def foldling(setup,clip,n):
    a,r,w,s,d,ph,b=setup('pavilion_foldling',clip,n,(0,12),-.08)
    cx=10*s-4*w;cy=29+b-13*d
    for i,x in enumerate((-8,8)):
        step=math.sin(ph+i*math.pi)*4 if clip=='walk' else 0
        lift=max(0,math.sin(ph+i*math.pi))*4 if clip=='walk' else 0
        foot=x+step+5*d
        r.limb([(x+cx,cy-7),(x+cx-4,13+lift+6*d),(foot,2+lift+10*d)],VIOLET,2)
        r.limb([(foot-4,1+lift+10*d),(foot+5,1+lift+10*d)],VIOLET,2)
    # Broad paper planes keep crisp creases rather than a soft oval bird body.
    r.poly([(cx-23,cy+7),(cx-7,cy+20),(cx+15,cy+5),(cx+11,cy-15),(cx-10,cy-9)],PEARL[2],OUTLINE)
    r.poly([(cx-23,cy+7),(cx+15,cy+5),(cx-8,cy-8)],PEARL[-1])
    r.line([(cx-7,cy+20),(cx-8,cy-8),(cx+11,cy-15)],PEARL[0],1)
    # Pleated rose wing fans fan back in the wind-up and fold into a paper heap on death.
    wingx=cx-12-9*w+5*s;wingy=cy+9+7*w-14*d
    for i in range(4):
        xx=wingx-10-i*3-4*d;yy=wingy+15+i*3-18*d
        r.poly([(cx+2,cy),(xx,yy),(xx+6,yy+2),(cx+5,cy-4)],CORAL[1+i%3],OUTLINE)
    r.poly([(cx-19,cy+5),(cx-34,cy+17-17*d),(cx-32,cy-3),(cx-12,cy-5)],CORAL[2],OUTLINE)
    hx=15+19*s-6*w;hy=56+b+5*w-8*s-34*d
    r.poly([(cx+10,cy-3),(cx+8,cy+9),(hx-5,hy+2),(hx+2,hy-3),(cx+14,cy-5)],PEARL[3],OUTLINE)
    r.line([(cx+10,cy+6),(hx-3,hy-1)],PEARL[0],1)
    r.poly([(hx-8,hy+5),(hx+4,hy+9),(hx+11,hy),(hx-2,hy-7)],PEARL[-1],OUTLINE)
    # An angular ink slash and a tiny pinpoint, never a round shared eye.
    r.poly([(hx+1,hy+4),(hx+8,hy+2),(hx+3,hy)],VIOLET[0])
    if d<.6:r.ellipse(hx+5,hy+2,1,1,WHITE)
    gape=2+7*s+2*w+3*d
    r.poly([(hx+9,hy+1),(hx+24,hy-3),(hx+10,hy-3)],GOLD[3],OUTLINE)
    r.poly([(hx+9,hy-3),(hx+22,hy-4-gape),(hx+9,hy-5-gape)],GOLD[2],OUTLINE)
    if d>.2:r.line([(cx-8,cy+13),(cx+3,cy+1),(cx-5,cy-6)],VIOLET[1],1)
    return a


def inkmoth(setup,clip,n):
    a,r,w,s,d,ph,b=setup('pavilion_inkmoth',clip,n,(0,36),.80)
    x=17*s-6*w;y=61+b+6*w-5*s-29*d
    span=(.48+.18*math.sin(ph*1.5)) if clip in ('idle','walk') else .48+.45*w-.20*s
    # Wings are ink-soaked, ragged pages: ink gathers in a connected pool during death.
    if d>.3:a.ball(x-2,y-23,11+23*d,2+4*d,VIOLET)
    for side in (-1,1):
        xx=x+side*(9+37*span*(1-.7*d));yy=y+6-12*d
        r.poly([(x+side*3,y+6),(xx,yy+21),(xx+side*9,yy-3),(xx+side*3,yy-17),(x+side*7,y-21)],VIOLET[0],OUTLINE)
        r.poly([(x+side*5,y+5),(xx,yy+16),(xx+side*3,yy-1),(x+side*9,y-17)],VIOLET[2])
        r.line([(x+side*5,y+3),(xx,yy+7),(xx+side*4,yy-5)],VIOLET[-1],1)
        r.ball(xx,yy+4,4,5,PURPLE)
        r.poly([(xx-3,yy+6),(xx+3,yy+5),(xx+1,yy+2)],GOLD[3])
        r.taper([(x+side*4,y+17),(x+side*9,y+30-18*d),(x+side*15,y+28-19*d)],VIOLET,2,1)
        for j in range(3):
            r.limb([(x+side*4,y+5-j*5),(x+side*(10-5*d),y+1-j*5),(x+side*(13-11*d),y-4-j*6+8*d)],VIOLET,2)
    r.ball(x,y-7,6,15*(1-.2*d),VIOLET)
    for j in range(3):r.line([(x-3,y-15+j*6),(x+3,y-14+j*6)],PURPLE[-1],1)
    r.ball(x,y+12,8,9,VIOLET)
    # Hooded, sharp amber compound-eye wedges, crossed by black vein markings.
    for side in (-1,1):
        r.poly([(x+side*2,y+15),(x+side*9,y+18),(x+side*7,y+10)],GOLD[3] if d<.6 else VIOLET[1],OUTLINE)
        if d<.6:r.line([(x+side*5,y+15),(x+side*6,y+12)],OUTLINE,1)
    r.taper([(x+1,y+8),(x+10+13*s,y+4+8*w),(x+13+22*s,y+5-3*s)],VIOLET,3,1)
    return a


def silkguard(setup,clip,n):
    a,r,w,s,d,ph,b=setup('pavilion_silkguard',clip,n,(0,10),.27)
    cy=28+b-14*d;hx=-1+6*s-4*w;hy=52+b-24*d
    for i,x in enumerate((-8,9)):
        step=math.sin(ph+i*math.pi)*4 if clip=='walk' else 0
        r.limb([(x,cy),(x-6*d,12),(x+step-9*d,3)],CRIMSON,5)
        r.ball(x+step-9*d,3,6,3,SLATE)
    r.ball(0,cy+5,13,18*(1-.35*d),CRIMSON)
    r.poly([(-12,cy+8),(-17-5*d,5),(0,9+3*d),(14,5),(11,cy+8)],CRIMSON[2],OUTLINE)
    for xx in (-8,0,8):r.line([(xx*.6,cy+8),(xx+3*d,9)],CRIMSON[-1],1)
    r.limb([(-11,cy+3),(11,cy+3)],GOLD,3)
    r.ball(hx,hy,9,10,PEARL)
    # A red lacquer half-mask and hard diagonal black eye cuts.
    r.poly([(hx-8,hy+2),(hx+8,hy+1),(hx+6,hy-8),(hx,hy-11),(hx-7,hy-7)],CRIMSON[1],OUTLINE)
    for dx in (-4,4):
        r.line([(hx+dx-2,hy+4),(hx+dx+2,hy+2)],OUTLINE,2)
        if d<.5:r.ellipse(hx+dx+1,hy+3,1,1,WHITE)
    # Hat is a rigid cone, with a visible two-tone fold and a low brim.
    r.poly([(hx-19,hy+8),(hx,hy+24),(hx+19,hy+8)],GOLD[2],OUTLINE)
    r.poly([(hx,hy+24),(hx+19,hy+8),(hx,hy+9)],GOLD[-1])
    r.limb([(hx-19,hy+8),(hx+19,hy+8)],GOLD,2)
    handx=16+20*s-11*w;handy=cy+7+17*w-5*s
    r.limb([(-11,cy+12),(-18,cy+3),(-4+12*s,cy+7)],CRIMSON,4)
    r.limb([(11,cy+12),(17+8*s,cy+5),(handx,handy)],CRIMSON,4)
    # Rigid spear sweeps above the hands then projects forward; death tips it to the floor.
    angle=.18-.45*w+1.12*s+1.12*d
    vx,vy=math.sin(angle),math.cos(angle)
    tip=(handx+vx*35,handy+vy*35);butt=(handx-vx*22,handy-vy*22)
    r.limb([butt,tip],BROWN,2)
    r.poly([tip,(tip[0]-vy*4-vx*9,tip[1]+vx*4-vy*9),(tip[0]+vy*4-vx*9,tip[1]-vx*4-vy*9)],SLATE[-1],OUTLINE)
    r.taper([(tip[0]-vx*9,tip[1]-vy*9),(tip[0]-vx*13-6*w,tip[1]-vy*13-5)],CRIMSON,3,1)
    return a


def mirror(setup,clip,n):
    a,r,w,s,d,ph,b=setup('pavilion_mirror',clip,n,(0,9),-.24)
    cy=27+b-13*d;hx=-1+7*s-6*w;hy=52+b-25*d
    # Long dark ponytail and ribbon trails stay connected behind the porcelain mask.
    r.taper([(hx-5,hy+6),(hx-18-4*w,hy-5),(hx-24+math.sin(ph)*2,cy-7+5*d)],VIOLET,6,2)
    r.ball(0,3,17+6*d,3,AZURE)
    r.poly([(-15-5*d,3),(-11,cy+12),(9,cy+14),(16+6*d,3)],AZURE[2],OUTLINE)
    r.ball(0,cy,12,17*(1-.4*d),AZURE)
    for xx in (-9,-3,4,10):r.taper([(xx*.6,cy+9),(xx+math.sin(ph)*1.4,5)],AZURE,3,1)
    r.ball(hx,hy,10,11,PEARL)
    # The face itself is half black mirror, one silver diamond slit and a painted frown.
    r.poly([(hx,hy+10),(hx+8,hy+6),(hx+8,hy-6),(hx,hy-9)],VIOLET[0])
    r.line([(hx,hy+9),(hx,hy-8)],GOLD[2],1)
    r.poly([(hx+2,hy+3),(hx+5,hy+5),(hx+7,hy+2),(hx+4,hy+1)],PEARL[-1] if d<.6 else VIOLET[1])
    r.line([(hx-7,hy+3),(hx-2,hy+5)],OUTLINE,2)
    r.line([(hx-4,hy-5),(hx-1,hy-4),(hx+2,hy-6)],CRIMSON[1],1)
    r.ball(hx-1,hy+10,10,3,VIOLET)
    for i,dx in enumerate((-6,0,6)):
        r.poly([(hx+dx-2,hy+12),(hx+dx,hy+18-abs(i-1)*3),(hx+dx+2,hy+12)],GOLD[3],OUTLINE)
    # Two separate mirrors cross inward then sweep out; they crack while the cloth kneels.
    for side in (-1,1):
        handx=side*(23-12*w)+(27*s if side==1 else -5*s)
        handy=cy+7+11*w-8*s-4*d
        r.limb([(side*10,cy+10),(side*16+8*s,cy+2),(handx,handy)],AZURE,4)
        r.ball(handx,handy+3,10,13*(1-.66*d),GOLD,side*.22*d)
        r.ball(handx,handy+3,7,10*(1-.66*d),PEARL,side*.22*d)
        r.line([(handx-3,handy+8*(1-d)),(handx+2,handy+11*(1-d))],WHITE,1)
        if d>.25:r.line([(handx-3,handy+8*(1-d)),(handx+1,handy+3),(handx-2,handy-2)],SLATE[0],1)
    return a


def weaver(setup,clip,n):
    a,r,w,s,d,ph,b=setup('pavilion_weaver',clip,n,(0,12),.70)
    cy=22+b+5*w-10*d;lean=9*s-3*w
    # Eight distinct articulated legs; opposite corners lift in diagonal pairs.
    for side in (-1,1):
        for j in range(4):
            xx=-16+j*9;reach=side*(27+j*2)
            phase=ph+j*math.pi/2+(0 if side==1 else math.pi)
            step=math.sin(phase)*3 if clip=='walk' else 0
            lift=max(0,math.sin(phase))*4 if clip=='walk' else 0
            root=(lean+xx,cy)
            knee=(lean+xx+side*(8+5*w)*(1-d),cy+8-14*d)
            foot=(xx+reach*.44+step*(1-d),2+lift+17*d)
            r.limb([root,knee,foot],VIOLET if side==1 else PURPLE,3)
    r.ball(lean-12,cy+5,20,14,VIOLET)
    for i in range(3):
        xx=lean-23+i*9
        r.poly([(xx,cy+12),(xx+3,cy+17),(xx+6,cy+12),(xx+3,cy+8)],CORAL[3],OUTLINE)
    # A silk loom around the abdomen, with attached white thread spools.
    for j in range(3):
        yy=cy-3+j*5
        r.line([(lean-29,yy),(lean-19,yy-3),(lean-9,yy+1)],PEARL[2],1)
    hx=18+18*s-5*w;hy=cy+2+4*w
    r.limb([(lean+3,cy),(hx-5,hy)],VIOLET,8)
    r.ball(hx,hy,12,10,VIOLET)
    # Six unequal ruby pin-eyes in a low triangular cluster above separate hinged fangs.
    for i,(dx,dy,rr) in enumerate(((-7,3,2),(-3,7,2.3),(3,8,2),(8,4,2),(-2,1,1.5),(4,1,1.5))):
        r.ellipse(hx+dx,hy+dy,rr,rr,CORAL[-1] if d<.6 else VIOLET[0])
        if d<.6:r.ellipse(hx+dx-.5,hy+dy+1,.7,.7,WHITE)
    for side in (-1,1):
        r.taper([(hx+side*5,hy-4),(hx+side*(8+3*w),hy-10-5*s),(hx+side*2+12*s,hy-15-3*s)],BONE,3,1)
    return a


def sovereign(setup,clip,n):
    a,r,w,s,d,ph,b=setup('pavilion_sovereign',clip,n,(0,8),-.22)
    sway=math.sin(ph)*2.8 if clip=='walk' else 0
    cy=27+b-13*d;hx=-2+7*s-5*w+sway*.25;hy=51+b-27*d
    r.ball(0,3,17+7*d,3,CRIMSON)
    r.poly([(-17-6*d,3),(-13,cy+16),(12,cy+16),(18+8*d,3)],CRIMSON[1],OUTLINE)
    r.ball(0,cy+3,14,19*(1-.4*d),CRIMSON)
    for xx in (-10,0,10):r.taper([(xx*.6,cy+12),(xx+5*d+sway,5+abs(sway)*.3)],GOLD,2,1)
    # Paper sleeve wings are rigid pleats that unfold downward as their joints fail.
    for side in (-1,1):
        for i in range(3):
            xx=side*(14+i*4)+10*s+sway
            r.poly([(side*10,cy+14),(xx,cy+4+8*w),(xx+side*5,cy-13-3*i+8*d),(side*8,cy-1)],PEARL[2+i%3],OUTLINE)
    r.ball(hx,hy,11,11,PEARL)
    # A long black stage mask: gold diagonal brow, one red pupil and a jagged mouth.
    r.poly([(hx-7,hy+8),(hx+6,hy+7),(hx+8,hy-7),(hx+1,hy-13),(hx-7,hy-6)],VIOLET[0],OUTLINE)
    r.line([(hx-5,hy+5),(hx+5,hy+2)],GOLD[3],2)
    if d<.7:r.ellipse(hx+3,hy,1,2,CORAL[-1]);r.ellipse(hx+3,hy+1,.7,.7,WHITE)
    r.line([(hx-3,hy-5),(hx,hy-7),(hx+2,hy-5),(hx+5,hy-8)],PEARL[2],1)
    # Tall folded crown fans apart into a creased white heap; it does not squash.
    for side in (-1,1):
        tipx=hx+side*(6+15*d);tipy=hy+34-27*d
        r.poly([(hx,hy+9),(hx+side*10,hy+11),(tipx,tipy),(hx+side*2,hy+29-20*d)],PEARL[3],OUTLINE)
        r.line([(hx+side*4,hy+11),(tipx,tipy)],PEARL[0],1)
    r.poly([(hx-3,hy+11),(hx,hy+39-34*d),(hx+4,hy+12)],GOLD[3],OUTLINE)
    handx=23+24*s-11*w+sway;handy=cy+10+16*w-8*s+abs(sway)*.4
    r.limb([(-11,cy+13),(-19,cy+3),(-21+9*s,cy-1)],CRIMSON,4)
    r.limb([(11,cy+13),(17+9*s,cy+4),(handx,handy)],CRIMSON,4)
    # An attached folding war fan swings over the shoulder and sweeps forward.
    fan=r.__class__(a,handx,handy,-.55*w-.85*s-.85*d)
    for i in range(6):
        angle=-.85+i*.31
        tip=(handx+math.sin(angle)*22,handy+math.cos(angle)*22)
        nxt=(handx+math.sin(angle+.28)*22,handy+math.cos(angle+.28)*22)
        fan.poly([(handx,handy),tip,nxt],CORAL[2+i%2],OUTLINE)
        fan.line([(handx,handy),tip],GOLD[2],1)
    fan.ball(handx,handy,3,3,GOLD)
    return a
