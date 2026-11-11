"""Black Hour clockwork rigs: articulated forged metal, no rubber deformation."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, GOLD

IRON = AMETHYST = CURRENT = None


def gear(r,x,y,radius,teeth=12,phase=0,ramp=None):
    ramp=ramp or IRON
    pts=[]
    for j in range(teeth*4):
        t=math.tau*j/(teeth*4)+phase
        rr=radius*(1 if j%4 in (1,2) else .84)
        pts.append((x+rr*math.cos(t),y+rr*math.sin(t)))
    r.poly(pts,ramp[1],OUTLINE)
    r.line(pts[:len(pts)//2],ramp[3],1)
    r.ball(x,y,radius*.73,radius*.73,ramp)
    r.ball(x,y,radius*.49,radius*.49,IRON)


def piston(r,start,joint,end,thick=4):
    r.limb([start,joint],IRON,thick)
    r.limb([joint,end],GOLD,max(1.8,thick*.45))
    r.ball(*joint,thick+1,thick+1,IRON)
    r.ball(*end,thick,thick,IRON)


def lights(r,x,y,d,shape='slit'):
    # Every machine uses its own cutout, rather than a round universal face.
    if shape=='grille':
        r.poly([(x-11,y+6),(x+11,y+4),(x+9,y-7),(x-10,y-5)],OUTLINE)
        if d<.65:
            r.line([(x-9,y+4),(x-2,y+1)],CURRENT[3],2)
            r.line([(x+2,y+1),(x+9,y+3)],CURRENT[2],2)
        for j in range(4):r.line([(x-7+j*4,y-1),(x-7+j*4,y-5)],GOLD[2],1)
    elif shape=='visor':
        r.poly([(x-12,y+4),(x+12,y+7),(x+9,y-3),(x-10,y-5)],OUTLINE)
        if d<.68:
            r.poly([(x-8,y+1),(x+8,y+3),(x+3,y-1)],CURRENT[3])
        r.line([(x-12,y+6),(x,y+3),(x+11,y+9)],AMETHYST[0],3)
        r.poly([(x-6,y-8),(x+6,y-8),(x+4,y-12),(x-3,y-12)],IRON[0],OUTLINE)
    elif shape=='lens':
        r.ball(x,y,11,15,AMETHYST)
        r.poly([(x-5,y+9),(x+5,y+5),(x+3,y-8),(x-3,y-10)],OUTLINE)
        if d<.72:
            r.line([(x,y+5),(x-1,y-6)],CURRENT[3],3)
            r.ellipse(x-1,y+4,1,2,WHITE)
    elif shape=='bell':
        for side in (-1,1):
            ex=x+side*8
            r.poly([(ex+side*6,y+5),(ex-side*5,y+1),(ex-side*4,y-6),(ex+side*3,y-3)],OUTLINE)
            if d<.6:r.line([(ex+side*2,y),(ex-side*2,y-2)],CURRENT[3],2)
        r.line([(x-13,y-12),(x-5,y-9),(x,y-12),(x+11,y-10)],IRON[0],2)
    elif shape=='mask':
        r.poly([(x-10,y+12),(x+8,y+13),(x+12,y+2),(x+5,y-14),(x-5,y-14),(x-12,y+1)],IRON[3],OUTLINE)
        r.poly([(x+1,y+11),(x+8,y+10),(x+9,y+1),(x+3,y-11),(x,y-6)],IRON[1])
        for side in (-1,1):
            ex=x+side*5
            r.poly([(ex+side*4,y+6),(ex-side*3,y+2),(ex,y-3)],OUTLINE)
            if d<.65:r.line([(ex+side*2,y+3),(ex-side,y+1)],CURRENT[3],1)
        r.poly([(x-3,y-8),(x+3,y-7),(x+1,y-11),(x-2,y-11)],OUTLINE)


def hauler(setup,clip,n):
    a,r,w,s,d,ph,b=setup('null_hauler',clip,n,(0,15),-1.30)
    x,y=15*s-8*w,34+b+5*w-11*d
    # Four articulated load-bearing legs, brass piston rods and dark pads.
    for side in (-1,1):
        for j in range(2):
            xx=x-18+j*32
            step=math.sin(ph+j*math.pi+side)*5 if clip=='walk' else 0
            piston(r,(xx,y-7),(xx+side*9,y-18+step),(xx+side*(13-5*d)+step,5+11*d),4)
            r.ball(xx+side*(14-5*d)+step,4+11*d,9,4,IRON)
    r.ball(x,y,31,21,IRON)
    r.ball(x-4,y+8,27,22,AMETHYST)
    # Curved kiln ribs and a recessed furnace door give the hopper depth.
    for xx in (-19,-6,7,20):
        r.limb([(x+xx,y-8),(x+xx-2,y+18),(x+xx+3,y+25)],IRON,2.5)
    r.ball(x-8,y+2,15,12,IRON)
    r.ball(x-8,y+2,11,8,[IRON[0]]*5)
    for j in range(5):
        xx=x-16+j*4
        r.line([(xx,y-4),(xx,y+8)],CURRENT[2] if d<.65 else IRON[1],2)
    # Three bolted exhaust stacks, closed mouths rather than floating smoke.
    for j in range(3):
        xx=x-19+j*13;yy=y+25-j%2*3
        r.limb([(xx,yy-6),(xx-3,yy+12+j*3)],IRON,3)
        r.ball(xx-3,yy+12+j*3,5,3,IRON)
        r.ellipse(xx-3,yy+13+j*3,3,1,CURRENT[3] if d<.65 else IRON[0])
    # Long forward neck drives a crushing jaw slam.
    neck=(x+29+15*s-7*w,y-5+13*w-11*s)
    piston(r,(x+18,y+2),(x+26,y+4),neck,5)
    r.ball(*neck,14,12,IRON)
    lights(r,neck[0]+2,neck[1]+1,d,'grille')
    r.poly([(neck[0]-9,neck[1]-7),(neck[0]+13,neck[1]-7),(neck[0]+9,neck[1]-13),(neck[0]-6,neck[1]-12)],AMETHYST[2],OUTLINE)
    return a


def breaker(setup,clip,n):
    a,r,w,s,d,ph,b=setup('null_breaker',clip,n,(0,9),-1.52)
    x,y=12*s-6*w,34+b+4*w-9*d
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*5 if clip=='walk' else 0
        foot=(x+side*(11+6*d)+step,4+11*d)
        piston(r,(x+side*9,y-9),(x+side*13+step,18+8*d),foot,5)
        r.ball(foot[0]+2,foot[1],10,5,IRON)
    r.ball(x,y+8,19,26,IRON)
    r.ball(x-1,y+17,14,18,AMETHYST)
    r.line([(x-7,y+30),(x,y-9),(x+8,y+29)],GOLD[2],2)
    for side in (-1,1):
        gear(r,x+side*21,y+22,11,8,ramp=AMETHYST)
        r.poly([(x+side*17,y+30),(x+side*29,y+40),(x+side*30,y+18)],AMETHYST[2],OUTLINE)
    hx,hy=x,y+42
    r.ball(hx,hy,15,16,IRON)
    lights(r,hx,hy,d,'visor')
    # A separate suspended chest weight swings with the gait, never a free glyph.
    px=x+math.sin(ph)*3*(1-d);py=y-7
    r.limb([(x,y+12),(px,py)],GOLD,1.5)
    r.ball(px,py,7,9,AMETHYST)
    hand=(x+22-12*w+21*s,y+8+29*w-18*s)
    piston(r,(x+15,y+22),(x+25-9*w,y+16+11*w),hand,5)
    angle=-.2-1.1*w+1.25*s
    dx,dy=math.sin(angle),math.cos(angle)
    tip=(hand[0]+dx*29,hand[1]+dy*29)
    r.limb([(hand[0]-dx*17,hand[1]-dy*17),tip],GOLD,2.5)
    # Broad rigid pendulum blade with a bevel and a central clockwork bolt.
    ux,uy=dy,-dx
    def p(u,v):return tip[0]+ux*u+dx*v,tip[1]+uy*u+dy*v
    r.poly([p(-16,5),p(8,10),p(18,3),p(12,-12),p(-14,-9)],IRON[2],OUTLINE)
    r.poly([p(-14,-6),p(12,-10),p(17,1),p(9,-4)],AMETHYST[3],OUTLINE)
    r.ball(*tip,5,5,GOLD)
    # Counterbalancing fist folds into the corpse.
    piston(r,(x-16,y+20),(x-25,y+8),(x-20+5*d,y-8+12*d),5)
    return a


def coil(setup,clip,n):
    a,r,w,s,d,ph,b=setup('null_coil',clip,n,(0,42),-1.43)
    x,y=13*s-7*w,50+b+5*w
    for side in (-1,1):
        for j in range(3):
            xx=x+side*(17+j*9);yy=y+23-j*9
            piston(r,(x+side*9,y-7),(xx,y-17),(xx,yy),2.5)
            # Stacked ribbed solenoids and heavy spherical terminal caps.
            r.limb([(xx,y-14),(xx,yy)],AMETHYST,3.5)
            for k in range(4):r.line([(xx-4,y-9+k*5),(xx+4,y-9+k*5)],IRON[3],1)
            r.ball(xx,yy,5,4,IRON)
            r.ellipse(xx,yy+1,3,2,CURRENT[3] if d<.7 else IRON[0])
    gear(r,x,y,20,12,math.sin(ph)*.025,ramp=AMETHYST)
    lights(r,x,y,d,'lens')
    r.poly([(x-11,y-18),(x-6,y-30),(x,y-24),(x+7,y-32),(x+13,y-17)],IRON[2],OUTLINE)
    # Bolts emerge continuously from the right-hand terminals during the strike.
    if s>0 and d==0:
        for j in range(3):
            xx=x+17+j*9;yy=y+23-j*9
            pts=[(xx,yy),(xx+8*s,yy+8*s),(xx+17*s,yy-5*s),(xx+29*s,yy+4*s)]
            r.line(pts,CURRENT[2],4)
            r.line(pts,CURRENT[4],1)
    return a


def bell(setup,clip,n):
    a,r,w,s,d,ph,b=setup('null_bell',clip,n,(0,10),-1.50)
    x,y=11*s-6*w,35+b+8*w-10*s-8*d
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        foot=(x+side*(15+5*d)+step,4+10*d)
        piston(r,(x+side*12,y-8),(x+side*17,15+9*d),foot,6)
        r.ball(*foot,11,5,IRON)
    # Bell crown and skirt preserve a cast-metal silhouette throughout the fall.
    r.ball(x,y+16,25,32,AMETHYST)
    r.poly([(x-20,y+27),(x-25,y+2),(x-33,y-7),(x+33,y-7),(x+25,y+2),(x+20,y+27)],AMETHYST[2],OUTLINE)
    r.poly([(x+12,y+39),(x+21,y+27),(x+26,y+1),(x+32,y-6),(x+19,y-6)],AMETHYST[0])
    r.line([(x-18,y+27),(x-22,y+1),(x-28,y-5)],AMETHYST[4],2)
    r.ball(x,y-7,33,6,IRON)
    r.ball(x,y-8,24,3,[IRON[0]]*5)
    clx=x+7*math.sin(ph)*(1-d)+11*s
    r.limb([(x,y+8),(clx,y-17)],GOLD,3)
    r.ball(clx,y-18,7,7,IRON)
    if d<.65:r.ellipse(clx-1,y-16,3,3,CURRENT[3])
    # Crown yoke attached directly to the bell cap.
    r.limb([(x-9,y+42),(x-9,y+54),(x+9,y+54),(x+9,y+42)],IRON,3)
    lights(r,x,y+22,d,'bell')
    for side in (-1,1):
        hand=(x+side*(34+6*s-5*w-8*d),y-1+26*w-14*s+12*d)
        piston(r,(x+side*21,y+25),(x+side*31,y+12+16*w),hand,6)
        r.ball(*hand,10,12,IRON)
        r.poly([(hand[0]-8,hand[1]+5),(hand[0]+8,hand[1]+5),(hand[0]+8,hand[1]-9),(hand[0]-8,hand[1]-9)],AMETHYST[2],OUTLINE)
        for j in range(3):r.line([(hand[0]-5+j*5,hand[1]+4),(hand[0]-5+j*5,hand[1]-7)],IRON[0],1)
    return a


def conductor(setup,clip,n):
    a,r,w,s,d,ph,b=setup('null_conductor',clip,n,(0,47),1.52)
    x,y=10*s-5*w,54+b+4*w
    # Six hinged current arms are mechanical appendages, not loose orbiting marks.
    for side in (-1,1):
        for j in range(3):
            end=(x+side*(30+j*3-13*d)+17*s,y+22-j*21+10*w-9*s)
            knee=(x+side*(24-9*d),y+20-j*14)
            piston(r,(x+side*9,y+5),knee,end,2)
            r.line([(x+side*9,y+5),knee,end],CURRENT[2] if d<.65 else IRON[1],1)
            r.ball(*end,5,8,IRON)
            r.ellipse(end[0],end[1]+1,2,5,CURRENT[3] if d<.65 else IRON[0])
            if s>0 and d==0 and side==1:
                r.line([end,(end[0]+12*s,end[1]+5*s),(end[0]+23*s,end[1]-3*s)],CURRENT[3],2)
    r.ball(x,y,15,24,IRON)
    r.ball(x-2,y+3,11,18,AMETHYST)
    for j in range(4):r.line([(x-7,y+10-j*6),(x+7,y+10-j*6)],CURRENT[2] if d<.65 else IRON[0],2)
    # Split rigid skirt plates and the spindle keel.
    for side in (-1,1):
        r.poly([(x+side*7,y-9),(x+side*15,y-10),(x+side*(21-9*d),y-34),(x+side*5,y-23)],AMETHYST[2],OUTLINE)
        r.line([(x+side*13,y-12),(x+side*14,y-27)],IRON[3],1)
    r.limb([(x,y-15),(x,y-34)],IRON,3)
    # Gear halo is solid iron behind Iona's distinctive severe mask.
    gear(r,x,y+30,22,13,ramp=AMETHYST)
    lights(r,x,y+31,d,'mask')
    r.poly([(x-9,y+49),(x-14,y+57),(x-3,y+52),(x+4,y+58),(x+9,y+49)],GOLD[2],OUTLINE)
    return a


def hour(setup,clip,n):
    a,r,w,s,d,ph,b=setup('null_hour',clip,n,(0,11),-1.42)
    x,y=14*s-7*w,43+b+5*w-9*d
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        foot=(x+side*(21+5*d)+step,4+12*d)
        piston(r,(x+side*16,y-17),(x+side*20,18+10*d),foot,5)
        r.ball(*foot,11,4,IRON)
    gear(r,x,y,35,13,ramp=AMETHYST)
    r.ball(x,y,27,27,IRON)
    r.ball(x,y,23,23,[IRON[0],IRON[0],IRON[1],IRON[1],IRON[2]])
    for j in range(12):
        t=math.tau*j/12
        r.line([(x+math.sin(t)*20,y+math.cos(t)*20),(x+math.sin(t)*24,y+math.cos(t)*24)],GOLD[3],2)
    # Hour hands emerge from the central bearing; the eye is a cruel horizontal aperture.
    theta=-.55-.9*w+1.5*s if d==0 else -.55
    for length,angle in ((18,theta),(13,theta+2.1)):
        r.limb([(x,y),(x+math.sin(angle)*length,y+math.cos(angle)*length)],CURRENT if d<.6 else IRON,2)
    r.ball(x,y,9,7,AMETHYST)
    r.poly([(x-8,y+3),(x+8,y+4),(x+5,y-3),(x-6,y-3)],OUTLINE)
    if d<.6:
        r.line([(x-5,y+1),(x+5,y+1)],CURRENT[3],2)
        r.line([(x,y+3),(x,y-2)],IRON[0],1)
    r.poly([(x-11,y-10),(x+11,y-10),(x+8,y-16),(x-8,y-16)],OUTLINE)
    for j in range(5):r.poly([(x-9+j*4,y-10),(x-6+j*4,y-10),(x-7+j*4,y-14)],GOLD[3])
    # Thirteen-tooth crown is part of the clock, not hovering magic.
    r.poly([(x-16,y+28),(x-18,y+44),(x-8,y+36),(x,y+47),(x+8,y+36),(x+18,y+44),(x+16,y+28)],IRON[2],OUTLINE)
    r.poly([(x-15,y+30),(x-16,y+40),(x-8,y+33),(x,y+43),(x,y+30)],IRON[3])
    r.poly([(x+8,y+34),(x+16,y+40),(x+14,y+29),(x+1,y+29)],IRON[1])
    r.line([(x-14,y+29),(x+14,y+29)],GOLD[2],2)
    for side in (-1,1):
        hand=(x+side*(39+8*s-8*w-26*d)+10*s,y-12+31*w-12*s+15*d)
        piston(r,(x+side*27,y+12),(x+side*38,y+1+17*w),hand,5)
        gear(r,*hand,10,8,ramp=IRON)
        # Clock-hand blades are attached to the fist bearing and sweep with the arm.
        angle=side*(.25-1.1*w+1.3*s)*(1-d)+.15*d
        dx,dy=math.sin(angle),math.cos(angle);ux,uy=dy,-dx
        def p(u,v):return hand[0]+ux*u+dx*v,hand[1]+uy*u+dy*v
        r.poly([p(-4,-8),p(-4,15),p(-9,15),p(0,30),p(9,15),p(4,15),p(4,-8)],IRON[2],OUTLINE)
        r.line([p(0,-3),p(0,24)],CURRENT[3] if d<.6 else GOLD[1],2)
    return a
