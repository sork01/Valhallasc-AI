"""Six articulated Rain Crown creatures in y-up coordinates; props follow their grips."""
import math
from astral_slime_redraw import OUTLINE, WHITE, PEARL, GOLD, GREEN, TEAL, AZURE, SLATE, PURPLE, VIOLET, CRIMSON, BROWN


def crown(r,x,y,width=12,height=13,tilt=0):
    r.poly([(x-width,y),(x+width,y),(x+width,y+4),(x-width,y+4)],GOLD[2],OUTLINE)
    for i in range(5):
        xx=x-width+i*width/2
        r.poly([(xx-3,y+3),(xx+tilt,y+height+(3 if i==2 else 0)),(xx+3,y+3)],GOLD[3],OUTLINE)
    r.ball(x,y+3,3,3,CRIMSON)


def droplet(setup,clip,n):
    a,r,w,s,d,ph,b=setup('rain_crown_droplet',clip,n,(0,18))
    drift=math.sin(ph)*2.5 if clip=='walk' else 0
    x=22*s-9*w+drift;y=46+b+8*w-12*s-15*d+(math.cos(ph)*2 if clip=='walk' else 0)
    # Water alone changes volume: pointed crest melts into the connected splash.
    rx=15+18*d+5*s;ry=17*(1-.84*d)
    r.ball(x,y,rx,ry,AZURE)
    r.poly([(x-12*(1-d),y+8*(1-d)),(x-2,y+31*(1-d)),(x+12*(1-d),y+6*(1-d))],AZURE[2],OUTLINE)
    r.poly([(x-6,y+10*(1-d)),(x-2,y+25*(1-d)),(x+2,y+9*(1-d))],AZURE[-1])
    for side in (-1,1):
        r.taper([(x+side*11,y-6),(x+side*(21+14*s+8*d),y+3+5*w),(x+side*(20+16*d),y-8)],AZURE,4*(1-.5*d),1)
    if d<.8:
        for side in (-1,1):
            ex=x+side*6
            r.poly([(ex-5,y+6),(ex+4,y+4),(ex+3,y),(ex-3,y-1)],PEARL[-1],OUTLINE)
            r.line([(ex,y+4),(ex,y+1)],VIOLET[0],2)
        r.poly([(x-9,y-5),(x-4,y-3),(x,y-6),(x+5,y-3),(x+10,y-5),(x+5,y-10),(x-5,y-10)],VIOLET[0])
        for dx in (-5,3):r.poly([(x+dx,y-4),(x+dx+3,y-4),(x+dx+1,y-8)],WHITE)
    # Intact crown descends with the draining water; never softens or squashes.
    crown(r,x-1+9*d,y+25*(1-d)+1,10,10,3*d)
    return a


def oracle(setup,clip,n):
    a,r,w,s,d,ph,b=setup('rain_crown_oracle',clip,n,(0,9),-.45)
    cy=26+b-12*d;hx=3+7*s-5*w;hy=50+b-21*d
    hem=math.sin(ph)*3 if clip=='walk' else b*.4
    if clip=='walk':hy+=math.cos(ph)*1.2
    r.poly([(-16-5*d,2),(-10,cy+13),(11,cy+12),(18+5*d,2),(hem,5)],TEAL[1],OUTLINE)
    r.ball(0,cy+1,12,17*(1-.35*d),GREEN)
    for j,x in enumerate((-10,-3,5,12)):
        r.taper([(x*.5,cy+10),(x+hem,6+j%2)],GREEN,3,1)
    # Cowl, jade skin and a gold circlet framing a single vertical third eye.
    r.ball(hx-3,hy+2,14,17,TEAL)
    r.ball(hx+2,hy,10,12,GREEN)
    r.limb([(hx-11,hy+11),(hx+12,hy+11)],GOLD,2)
    r.poly([(hx-1,hy+13),(hx+3,hy+17),(hx+7,hy+13),(hx+3,hy+10)],GOLD[3],OUTLINE)
    r.line([(hx+3,hy+14),(hx+3,hy+12)],CRIMSON[2],1)
    for xx in (-3,7):
        r.line([(hx+xx-3,hy+3),(hx+xx+2,hy+5)],OUTLINE,2)
        if d<.5:r.ellipse(hx+xx,hy+3,1,1,GOLD[-1])
    r.line([(hx,hy-6),(hx+4,hy-7)],TEAL[0],1)
    hand=(20+22*s-9*w,cy+12+13*w-5*s)
    r.limb([(-10,cy+11),(-18,cy+2),(-16+hem,cy-7)],GREEN,4)
    r.limb([(10,cy+11),(15+10*s,cy+4),hand],GREEN,4)
    r.ball(*hand,4,4,GREEN)
    orb=(hand[0]+3,hand[1]+9)
    r.ball(*orb,6+4*w+2*s,7+3*w,GOLD)
    r.taper([(orb[0]-3,orb[1]),(orb[0]+5+8*s,orb[1]+8),(orb[0]+12+13*s,orb[1]+2)],TEAL,3,1)
    return a


def guard(setup,clip,n):
    a,r,w,s,d,ph,b=setup('rain_crown_guard',clip,n,(0,9),.51)
    cy=28+b-13*d;hx=3+7*s-5*w;hy=53+b-23*d
    for i,x in enumerate((-10,10)):
        step=math.sin(ph+i*math.pi)*4 if clip=='walk' else 0
        lift=max(0,math.sin(ph+i*math.pi))*5 if clip=='walk' else 0
        r.limb([(x,cy-7),(x+step/2,13+lift),(x+step+6*d,3+lift)],AZURE,5)
        r.ball(x+step+6*d,3+lift,7,3,SLATE)
    r.ball(0,cy+5,16,17,AZURE)
    for y in (-5,3,11):r.limb([(-13,cy+y),(13,cy+y)],SLATE,3)
    r.ball(hx,hy,11,11,SLATE)
    r.poly([(hx-13,hy+7),(hx+13,hy+7),(hx+12,hy+14),(hx-12,hy+14)],AZURE[2],OUTLINE)
    # One hard diagonal visor, no skin-coloured shared circular face.
    r.poly([(hx-9,hy+3),(hx+10,hy+5),(hx+8,hy-1),(hx-7,hy-3)],VIOLET[0],OUTLINE)
    if d<.6:r.line([(hx-5,hy+1),(hx+7,hy+2)],CRIMSON[-1],1)
    r.poly([(hx-8,hy-5),(hx,hy-11),(hx+8,hy-5)],SLATE[3],OUTLINE)
    shieldx=-29-4*w+4*s;shieldy=cy+9+6*w-4*d
    r.limb([(-12,cy+12),(-22,cy+4),(shieldx,shieldy)],AZURE,4)
    # Turquoise umbrella is rigid; its ribs meet the same central grip.
    r.limb([(shieldx,shieldy-10),(shieldx,shieldy+6)],BROWN,2)
    r.poly([(shieldx-21,shieldy+3),(shieldx-14,shieldy+14),(shieldx,shieldy+20),(shieldx+16,shieldy+13),(shieldx+22,shieldy+3)],TEAL[2],OUTLINE)
    for dx in (-14,0,16):r.line([(shieldx,shieldy+18),(shieldx+dx,shieldy+4)],TEAL[-1],1)
    hand=(20+25*s-12*w,cy+8+13*w-5*s)
    r.limb([(12,cy+13),(19+10*s,cy+4),hand],AZURE,4)
    angle=.03-.5*w+1.30*s+.9*d
    vx,vy=math.sin(angle),math.cos(angle)
    tip=(hand[0]+vx*31,hand[1]+vy*31)
    r.limb([(hand[0]-vx*21,hand[1]-vy*21),tip],BROWN,2)
    r.poly([tip,(tip[0]-vx*10-vy*4,tip[1]-vy*10+vx*4),(tip[0]-vx*10+vy*4,tip[1]-vy*10-vx*4)],PEARL[-1],OUTLINE)
    r.ball(*hand,4,4,SLATE)
    return a


def gatekeeper(setup,clip,n):
    a,r,w,s,d,ph,b=setup('rain_crown_gatekeeper',clip,n,(0,9),-.6)
    cy=27+b-19*d;hy=51+b-27*d
    # Iron wheel is behind the shoulders and stops rotating during death.
    wx=-18;wy=cy+16-7*d;turn=(ph*.13 if clip=='walk' else b*.1) if not d else 0
    r.ball(wx,wy,17,17,SLATE);r.ball(wx,wy,11,11,VIOLET)
    for j in range(6):
        ang=j*math.tau/6+turn
        r.limb([(wx,wy),(wx+math.cos(ang)*14,wy+math.sin(ang)*14)],SLATE,2)
    for i,x in enumerate((-11,13)):
        step=math.sin(ph+i*math.pi)*4 if clip=='walk' else 0
        lift=max(0,math.sin(ph+i*math.pi))*4 if clip=='walk' else 0
        r.limb([(x,cy),(x+step/2-7*d,13+lift),(x+step-12*d,3+lift)],SLATE,6)
        r.ball(x+step-12*d,3+lift,8,3,SLATE)
    r.poly([(-20,cy-10),(-23,cy+14),(-7,cy+23),(19,cy+14),(20,cy-10)],SLATE[2],OUTLINE)
    for y in (-3,7,17):r.line([(-17,cy+y),(16,cy+y-1)],SLATE[0],2)
    r.poly([(-13,hy-8),(-17,hy+4),(-9,hy+13),(10,hy+12),(15,hy+2),(10,hy-8)],SLATE[3],OUTLINE)
    for xx in (-7,5):
        r.poly([(xx-4,hy+3),(xx+4,hy+1),(xx+3,hy-2),(xx-2,hy-1)],VIOLET[0])
        if d<.6:r.line([(xx,hy+1),(xx+1,hy-1)],GOLD[-1],1)
    r.line([(-7,hy-5),(0,hy-3),(7,hy-5)],SLATE[0],2)
    for xx,yy in ((-16,cy+17),(8,hy+13),(-8,hy+12)):r.ball(xx,yy,4,2,GREEN)
    r.limb([(-18,cy+13),(-29,cy+2),(-23-9*s,cy-5+8*w)],SLATE,6)
    hand=(25+19*s-7*w,cy+6+20*w-10*s)
    r.limb([(17,cy+14),(22+9*s,cy+4),hand],SLATE,6)
    r.poly([(hand[0]-11,hand[1]-13),(hand[0]+13,hand[1]-13),(hand[0]+13,hand[1]+17),(hand[0]-11,hand[1]+17)],SLATE[2],OUTLINE)
    for j in range(3):r.limb([(hand[0]-8,hand[1]-8+j*8),(hand[0]+10,hand[1]-8+j*8)],PEARL,2)
    if d<.9:
        for dx in (-6,7):
            r.taper([(hand[0]+dx,hand[1]-12),(hand[0]+dx,hand[1]-12-(10-3*math.sin(ph+dx))*(1-d))],AZURE,2,1)
    if d>.15:
        for dx in (-8,5):r.line([(dx,cy+15),(dx-3,cy+5),(dx+2,cy-3)],VIOLET[0],1)
    return a


def sibyl(setup,clip,n):
    a,r,w,s,d,ph,b=setup('rain_crown_sibyl',clip,n,(0,20),-.35)
    cy=38+b-25*d;hx=3+7*s-6*w;hy=60+b-28*d
    sw=math.sin(ph)*2 if clip=='walk' else b*.4
    r.taper([(hx-5,hy+9),(hx-18,hy-5),(hx-22+sw,cy-3)],PURPLE,7,2)
    r.poly([(-16,20-18*d),(-10,cy+12),(10,cy+12),(16,20-18*d),(sw,23-17*d)],PURPLE[2],OUTLINE)
    r.ball(0,cy+1,11,15*(1-.3*d),PURPLE)
    for dx in (-9,-2,6):r.taper([(dx*.5,cy+8),(dx+sw,23-18*d)],PURPLE,3,1)
    r.ball(hx,hy,9,11,PEARL)
    r.poly([(hx-11,hy+2),(hx-10,hy+13),(hx+3,hy+16),(hx+10,hy+6),(hx-1,hy+8)],PURPLE[2],OUTLINE)
    # A dark painted tear mask and an asymmetrical white pupil.
    r.poly([(hx-7,hy+3),(hx,hy+5),(hx+7,hy+2),(hx+1,hy-5),(hx-3,hy-2)],VIOLET[0])
    if d<.6:r.poly([(hx,hy+2),(hx+4,hy+3),(hx+2,hy)],WHITE)
    r.line([(hx-2,hy-7),(hx+3,hy-6)],CRIMSON[2],1)
    r.limb([(-10,cy+9),(-19+sw,cy+2),(-19+sw,cy-5)],PURPLE,4)
    hand=(19+23*s-11*w,cy+11+18*w-7*s)
    r.limb([(10,cy+11),(18+9*s,cy+4),hand],PURPLE,4)
    r.ball(*hand,3,3,PEARL)
    r.poly([(hand[0]-1,hand[1]+11),(hand[0]+10+14*s,hand[1]+5),(hand[0]+5+10*s,hand[1]),(hand[0]+16+18*s,hand[1]-11),(hand[0]+5,hand[1]-4),(hand[0]+8,hand[1]+1)],GOLD[3],OUTLINE)
    # Overhead cloud breaks into progressively smaller wisps; no floating corpse.
    for j,(dx,dy,rr) in enumerate(((-13,0,8),(0,4,10),(14,0,8))):
        radius=max(1,rr*(1-.9*d))
        r.ball(hx+dx*(1+d),hy+23+dy-12*d,radius,radius*.7,PEARL)
    if d<.8:
        for j in range(3):
            yy=hy+19-((n*3+j*7)%13)
            r.taper([(hx-15+j*15,yy),(hx-15+j*15,yy-4)],AZURE,2,1)
    return a


def sovereign(setup,clip,n):
    a,r,w,s,d,ph,b=setup('rain_crown_sovereign',clip,n,(0,18))
    x=12*s-7*w;y=49+b+7*w-6*s-30*d
    # Five streams stay attached to the water body and drain into the same pool.
    for j in range(5):
        dx=-22+j*11
        wave=math.sin(ph+j*.7)*(3 if clip=='walk' else 1)
        r.taper([(x+dx*.7,y-9),(x+dx+wave+8*s,y-17+11*w),(x+dx*(1+.7*d)+wave,18-14*d)],AZURE,4,2)
    r.ball(x,y,24+13*d,23*(1-.89*d),AZURE)
    r.ball(x-5,y+8*(1-d),14*(1-.5*d),10*(1-.7*d),AZURE)
    if d>.2:r.ball(x,y-7*(1-d),23+18*d,3,AZURE)
    if d<.9:
        # A broad hollow mouth and three unequal eyes, unlike the small droplet.
        for dx,dy,rr in ((-11,7,4),(5,9,5),(14,4,3)):
            r.ball(x+dx,y+dy,rr,rr+1,PEARL)
            r.line([(x+dx,y+dy+2),(x+dx,y+dy-1)],CRIMSON[1],2)
        r.poly([(x-12,y-6),(x-5,y-3),(x+2,y-5),(x+12,y-2),(x+15,y-12),(x+2,y-17),(x-10,y-13)],VIOLET[0])
        for dx in (-7,1,9):r.poly([(x+dx,y-5),(x+dx+4,y-5),(x+dx+1,y-10)],PEARL[-1])
    # Gold crown remains rigid and tips as water loses support.
    cr=type(r)(a,x,y+20*(1-d),.34*d)
    crown(cr,x,y+20*(1-d),23,20)
    return a
