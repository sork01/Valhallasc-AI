"""Six Elder Hollow models. All coordinates attach parts to their joints; y points up."""
import math
from astral_slime_redraw import OUTLINE, WHITE, CRIMSON, BONE, PEARL, GOLD, GREEN, BROWN, PINK, CORAL, AMBER, PURPLE, VIOLET, SLATE


def thornling(setup, clip, n):
    a,r,w,s,d,ph,b=setup('elder_thornling',clip,n,(0,12),-.36)
    cy=17+b-4*w-5*d;lean=12*s-4*w
    # Diagonal walk pairs, distinct planted paws even beneath the low bramble body.
    for i,x in enumerate((-23,-13,12,22)):
        step=math.sin(ph+(i%3)*math.pi)*3 if clip=='walk' else 0
        lift=max(0,math.sin(ph+(i%3)*math.pi))*4 if clip=='walk' else 0
        r.limb([(x+lean,cy),(x+step+lean+7*d,7+lift),(x+step+lean+9*d,2+lift)],BROWN,4)
        r.ball(x+step+lean+9*d,2+lift,4,2,BROWN)
    r.taper([(-20+lean,cy),(-31+lean,cy+4),(-35+lean,cy+9+math.sin(ph)*(1-d))],BROWN,5,1)
    r.ball(lean,cy,25,12,BROWN)
    r.ball(lean-2,cy+5,22,8,GREEN)
    for i in range(6):
        x=-23+i*8+lean;top=cy+12+(i%2)*3
        r.poly([(x-3,top-6),(x-2-7*d,top+9-12*d),(x+5,top-5)],BONE[2],OUTLINE)
        if d>.35:r.line([(x-2,top-3),(x+1,top-7),(x+4,top-4)],BROWN[0],1)
    hx=27+18*s-7*w;hy=cy+5+3*w-6*d
    r.limb([(15+lean,cy+1),(hx-5,hy)],BROWN,9)
    r.ball(hx,hy,12,10,BROWN)
    # Asymmetric acorn socket, hooked brow and pointed wooden teeth.
    r.ball(hx+2,hy+3,6,4,AMBER)
    if d<.55:
        r.poly([(hx-3,hy+7),(hx+8,hy+3),(hx+8,hy+7)],BROWN[0])
        r.ellipse(hx+4,hy+3,1.3,2,OUTLINE);r.ellipse(hx+3,hy+4,1,1,WHITE)
    else:r.line([(hx-2,hy+3),(hx+7,hy+1)],BROWN[0],2)
    jaw=3+9*s+3*w+4*d
    r.poly([(hx+3,hy-3),(hx+15,hy-3),(hx+12,hy-jaw),(hx+2,hy-jaw-1)],OUTLINE)
    r.limb([(hx+1,hy-4),(hx+7,hy-jaw-2),(hx+13,hy-jaw)],BROWN,3)
    for xx in (hx+5,hx+10):r.poly([(xx,hy-3),(xx+2,hy-3),(xx+1,hy-7)],BONE[-1])
    r.taper([(hx-6,hy+7),(hx-14,hy+18-11*d)],GREEN,5,1)
    return a


def moth(setup,clip,n):
    a,r,w,s,d,ph,b=setup('elder_moth',clip,n,(0,38),1.10)
    x=18*s-6*w;y=58+b+5*w-5*s-30*d
    flap=(.50+.17*math.sin(ph*1.7)) if clip in ('idle','walk') else .50+.48*w-.22*s
    span=max(.15,flap*(1-.80*d))
    # Layered rigid wing blades fold at the thorax; do not shrink the whole creature.
    for side in (-1,1):
        root=(x+side*4,y)
        xx=x+side*(10+36*span);yy=y+12-11*d
        r.poly([root,(x+side*9,y+18),(xx,yy+14),(xx+side*8,yy-11),(x+side*13,y-22)],GREEN[1],OUTLINE)
        r.poly([root,(xx-side*4,yy+12),(xx+side*4,yy-8),(x+side*12,y-18)],GREEN[2])
        r.line([root,(xx,yy+5),(xx+side*4,yy-8)],AMBER[2],2)
        r.ball(xx-side*4,yy+1,5*max(.4,span),7,AMBER)
        r.ellipse(xx-side*4,yy+1,2*max(.4,span),3,OUTLINE)
        r.ellipse(xx-side*4-1,yy+3,1,1,WHITE)
        r.taper([(x+side*4,y+18),(x+side*9,y+30-12*d),(x+side*13,y+32-15*d)],BROWN,2,1)
    r.ball(x,y-7,7,16,BROWN)
    for i in range(4):
        yy=y-16+i*6;r.line([(x-4,yy),(x+4,yy)],GOLD[2],2)
    r.ball(x,y+8,8,9,AMBER)
    r.ball(x,y+16,7,7,BROWN)
    # Wide-set black compound eyes and a curled, attached feeding tube.
    for side in (-1,1):
        r.ball(x+side*6,y+16,3,5,SLATE)
        if d<.7:r.ellipse(x+side*6-1,y+18,1,1,WHITE)
        for j in range(3):
            r.limb([(x+side*4,y+5-j*5),(x+side*(9+3*(1-d)),y+1-j*6),(x+side*(12-7*d),y-2-j*7+9*d)],BROWN,1)
    r.taper([(x+2,y+10),(x+8+14*s,y+2+5*w),(x+11+24*s,y+5-3*s)],GOLD,2,1)
    return a


def barkguard(setup,clip,n):
    a,r,w,s,d,ph,b=setup('elder_barkguard',clip,n,(0,12),-.14)
    cy=28+b-15*d;hx=1+5*s-4*w;hy=54+b-25*d
    for i,x in enumerate((-10,11)):
        step=math.sin(ph+i*math.pi)*4 if clip=='walk' else 0
        r.limb([(x,cy),(x+7*d,12-3*d),(x+step+10*d,3)],BROWN,6)
        r.ball(x+step+10*d,3,7,3,BROWN)
    r.ball(0,cy+4,16,18*(1-.30*d),BROWN)
    # Overlapping bark plates fall away on different sides of the stump.
    for side in (-1,1):
        xx=side*(10+7*d);yy=cy+6-6*d
        r.ball(xx,yy,8,15,BROWN,side*.20*d)
        r.line([(xx-3,yy+11),(xx+1,yy+4),(xx-2,yy-8)],BROWN[0],1)
        r.ball(side*17,cy+15-4*d,9,7,BROWN)
        r.ball(side*18,cy+17-4*d,6,3,GREEN)
    r.ball(hx,hy,13,11,BROWN)
    # Two uneven hollow knots; no shared round eyeball face.
    for dx,sz in ((-5,4),(5,3)):
        r.ellipse(hx+dx,hy+2,sz,sz-1,OUTLINE)
        if d<.6:r.ellipse(hx+dx+1,hy+2,1,1,GOLD[-1])
    r.line([(hx-10,hy+6),(hx-2,hy+4),(hx+10,hy+7)],BROWN[0],2)
    r.poly([(hx-4,hy-5),(hx+5,hy-4),(hx+2,hy-8)],OUTLINE)
    for i,xx in enumerate((-7,0,7)):
        r.taper([(hx+xx,hy+8),(hx+xx-3+4*d,hy+18-12*d)],GREEN,4,1)
    sx=-29+12*s+3*w;sy=cy+1-3*d
    r.limb([(-14,cy+9),(sx,sy)],BROWN,5)
    r.ball(sx,sy,12,16*(1-.66*d),BROWN,.35*d)
    r.ball(sx,sy,8,11*(1-.66*d),AMBER,.35*d)
    for xx in (-5,0,5):r.line([(sx+xx,sy+10*(1-d)),(sx+xx,sy-11*(1-d))],BROWN[0],1)
    handx=25+23*s-7*w;handy=cy+6+17*w-9*s
    r.limb([(14,cy+11),(18+8*s,cy),(handx,handy)],BROWN,5)
    r.taper([(handx-2,handy-11+6*d),(handx+4,handy+19-6*d)],BROWN,3,5)
    r.ball(handx+4,handy+18-6*d,7,5,BROWN)
    r.ball(handx+2,handy+20-6*d,4,2,GREEN)
    if d>.2:r.line([(-8,cy+16),(1,cy+9),(-2,cy+1),(5,cy-6)],OUTLINE,2)
    return a


def gatekeeper(setup,clip,n):
    a,r,w,s,d,ph,b=setup('elder_gatekeeper',clip,n,(0,12),-.35)
    cy=28+b-12*d;hx=-5+8*s-4*w;hy=53+b-23*d
    for i,xx in enumerate((-12,12)):
        step=math.sin(ph+i*math.pi)*3 if clip=='walk' else 0
        r.limb([(xx,cy),(xx+8*d,12),(xx+step+13*d,3)],BROWN,8)
        r.ball(xx+step+13*d,3,8,3,BROWN)
    r.ball(-3,cy+5,21,23*(1-.28*d),BROWN)
    r.ball(-5,cy+6,7,11,AMBER)
    r.line([(-5,cy+13),(-10,cy+7),(-6,cy+1)],BROWN[0],2)
    # Long forked branch antlers and a knotted face, with one vertical amber slit.
    for side in (-1,1):
        r.taper([(hx+side*8,hy+8),(hx+side*(13+4*d),hy+20-9*d),(hx+side*(9+11*d),hy+31-22*d)],BROWN,4,1)
        r.taper([(hx+side*12,hy+18),(hx+side*(22+8*d),hy+25-17*d)],BROWN,2,1)
        r.taper([(hx+side*18,hy+23),(hx+side*23,hy+28-19*d)],GREEN,4,1)
    r.ball(hx,hy,15,13,BROWN)
    r.line([(hx-13,hy+5),(hx-3,hy+2),(hx+10,hy+7)],BROWN[0],3)
    r.poly([(hx+2,hy+7),(hx+6,hy+6),(hx+5,hy-1),(hx+2,hy-2)],OUTLINE)
    if d<.65:r.line([(hx+4,hy+5),(hx+4,hy)],GOLD[-1],1)
    r.ball(hx+11,hy-1,5,4,BROWN)
    r.line([(hx-4,hy-6),(hx+3,hy-9),(hx+11,hy-6)],OUTLINE,2)
    # Both hands hold an actual gate slab; the rigid boards tip as the joints break.
    gx=29+25*s-10*w;gy=cy+5+10*w-7*s-10*d
    for side in (-1,1):r.limb([(side*17-3,cy+14),(side*19+10*s,cy+4),(gx+side*5,gy+side*5)],BROWN,6)
    gate=r.__class__(a,gx,gy,(-.72*d),0)
    gate.poly([(gx-11,gy-20),(gx+12,gy-20),(gx+12,gy+22),(gx-11,gy+22)],BROWN[2],OUTLINE)
    for xx in (-6,0,6):gate.line([(gx+xx,gy-18),(gx+xx,gy+20)],BROWN[0],2)
    for yy in (-12,12):gate.limb([(gx-10,gy+yy),(gx+11,gy+yy)],SLATE,3)
    gate.ball(gx+4,gy+1,3,4,SLATE)
    if d>.2:
        gate.line([(gx-8,gy+6),(gx+1,gy+3),(gx-3,gy-5),(gx+7,gy-11)],OUTLINE,2)
        r.line([(-10,cy+18),(-3,cy+8),(-8,cy-4)],BROWN[0],2)
    return a


def matron(setup,clip,n):
    a,r,w,s,d,ph,b=setup('elder_matron',clip,n,(0,10),-.18)
    cy=26+b-12*d;hx=-1+6*s-5*w;hy=51+b-23*d
    r.ball(0,3,16+6*d,3,PURPLE)
    r.poly([(-15-5*d,3),(-11,cy+14),(11,cy+14),(17+6*d,3)],PURPLE[1],OUTLINE)
    r.ball(0,cy,12,18*(1-.4*d),PURPLE)
    for xx in (-10,-3,5,12):r.taper([(xx*.6,cy+10),(xx+math.sin(ph)*2,4)],PURPLE,3,1)
    # Each attached petal has its own hinge; wilted collar droops down around the face.
    for i in range(9):
        ang=i*math.tau/9
        xx=hx+math.cos(ang)*14;yy=hy+math.sin(ang)*12
        tx=xx+math.cos(ang)*7*(1-.7*d);ty=yy+math.sin(ang)*9*(1-d)-17*d
        r.taper([(hx,hy),(xx,yy),(tx,ty)],PINK,6,2)
        r.line([(xx,yy),(tx,ty)],CORAL[2],1)
    r.ball(hx,hy,9,10,PEARL)
    # Hollow seed-shaped sockets on a pale mask, and a toothed vertical flower mouth.
    for dx in (-4,4):
        r.poly([(hx+dx-2,hy+4),(hx+dx+2,hy+6),(hx+dx+3,hy),(hx+dx,hy-1)],PURPLE[0])
        if d<.7:r.ellipse(hx+dx+1,hy+2,1,1,VIOLET[-1])
    gap=4+3*s
    r.poly([(hx-2,hy-3),(hx+3,hy-2),(hx+2,hy-gap-3),(hx-1,hy-gap-4)],OUTLINE)
    r.poly([(hx,hy-3),(hx+2,hy-3),(hx+1,hy-7)],BONE[-1])
    handx=23+25*s-10*w;handy=cy+6+13*w-8*s
    r.limb([(-10,cy+10),(-18,cy+6),(-22+8*s,cy-2+9*w)],PURPLE,4)
    r.limb([(10,cy+10),(16+6*s,cy+2),(handx,handy)],PURPLE,4)
    # Pod opens in the strike and withers around the attached palm on death.
    r.ball(handx,handy,7,8*(1-.3*d),GREEN)
    opening=2+6*s+3*d
    r.poly([(handx-4,handy+4),(handx+4,handy+5),(handx+opening,handy-2),(handx,handy-5)],GOLD[1],OUTLINE)
    r.ellipse(handx+1,handy+1,2,2,GOLD[-1] if d<.5 else BROWN[1])
    if d>.25:r.line([(-8,cy+12),(0,cy+5),(-3,cy-5)],PURPLE[0],2)
    return a


def heart(setup,clip,n):
    a,r,w,s,d,ph,b=setup('elder_heart',clip,n,(0,15),-.10)
    x=11*s-4*w;y=42+b+5*w-8*s-18*d
    # Anchored root buttresses, progressively bending and splitting into a stump.
    for i in range(6):
        xx=-24+i*9
        bend=math.sin(ph+i)*1.5 if clip in ('idle','walk') else 0
        r.taper([(x+xx*.6,y-12),(xx+6*s+6*d,14-6*d),(xx+bend+9*d,2)],CRIMSON,6,2)
        r.ball(xx+bend+9*d,2,4,2,CRIMSON)
    for side in (-1,1):
        r.taper([(x+side*15,y),(x+side*(25+9*d),y+14-16*d),(x+side*(22+16*d),y+29-37*d)],CRIMSON,7,2)
        r.taper([(x+side*25,y+13-16*d),(x+side*37,y+20-25*d)],CRIMSON,3,1)
        r.taper([(x+side*22,y+27-34*d),(x+side*25,y+38-45*d)],GREEN,5,1)
    for side in (-1,1):
        r.ball(x+side*(10+8*d),y+3-6*d,16,23*(1-.5*d),CRIMSON,side*.3*d)
        r.line([(x+side*(12+8*d),y+22-12*d),(x+side*(18+9*d),y+4-5*d),(x+side*(10+7*d),y-13)],CRIMSON[0],2)
    # A pulsing sap furnace under the split trunk. No cartoon eyes: a ribbed knot-mouth.
    pulse=1+.05*math.sin(ph) if clip in ('idle','walk') else 1+.20*w-.15*s
    r.ball(x,y,12*pulse,17*(1-.6*d),AMBER if d<.6 else CRIMSON[:2])
    r.ball(x,y+2,8*pulse,12*(1-.6*d),GOLD if d<.7 else CRIMSON[:2])
    r.poly([(x-4,y+10-5*d),(x+5,y+7),(x+3,y-8+5*d),(x-3,y-10+6*d)],OUTLINE)
    for j in range(3):
        yy=y-5+j*5
        r.poly([(x-4,yy+1),(x+2,yy),(x-3,yy-2)],BONE[2])
    # The two whiplash roots stay attached, gathering inward before the forward lash.
    for i,side in enumerate((-1,1)):
        tx=x+side*(26+7*w)+29*s;ty=y-9+12*w-15*s-8*d
        r.taper([(x+side*18,y-7),(tx,ty),(tx+side*10+13*s,ty+7-12*d)],CRIMSON,5,1)
    if d>.2:r.line([(x,y+22-14*d),(x-5,y+11-4*d),(x+2,y-2),(x-3,y-14+7*d)],OUTLINE,2)
    return a
