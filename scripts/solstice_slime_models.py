"""Silent Solstice: articulated snow, feathers, armour, ice, spirit and crystal."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, PEARL, GOLD, AZURE, SLATE, PURPLE, TEAL, BROWN


def crescent(r, x, y, size, bg=SLATE[0]):
    r.ball(x, y, size, size, PEARL)
    r.ellipse(x + size * .42, y + size * .15, size * .77, size * .8, bg)


def flurry(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solstice_flurry', clip, n, (0, 30))
    x, y = 17*s-8*w, 52+b+8*w-4*s
    # Snow vortices lose their spiral and disperse into a low settled drift.
    for j in range(6):
        xx=x+math.sin(ph+j*.9)*(9+j*1.3)*(1-d)+(-1 if j%2 else 1)*j*4*d
        yy=(y-j*5)*(1-d)+(7+j%2*2)*d
        r.ball(xx, yy, (17-j*1.5)*(1-.25*d), (9-j*.6)*(1-.65*d), PEARL)
    if d < .8:
        r.ball(x, y+8, 20*(1-.7*d), 17*(1-.7*d), AZURE)
        for side in (-1,1):
            r.poly([(x+side*3,y+15),(x+side*15,y+20),(x+side*13,y+8)], OUTLINE)
            r.ellipse(x+side*9,y+12,2,3,WHITE)
        r.poly([(x-8,y+2),(x,y-3),(x+9,y+2),(x+3,y-7)], SLATE[0])
    # A continuous attached snow-whip winds back, lashes and returns.
    if d < .9:
        r.taper([(x+9,y),(x+22-10*w,y+16*w),(x+25+40*s-12*w,y-8-7*s)], PEARL, 7*(1-d), 1)
    return a


def owl(setup, clip, n):
    a,r,w,s,d,ph,b=setup('solstice_owl',clip,n,(0,6),-1.25)
    x,y=16*s-8*w,31+b+5*w-12*d
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*3 if clip=='walk' else 0
        foot=(x+side*9+step,4+8*s)
        r.limb([(x+side*7,y-10),foot], BROWN, 3)
        for toe in (-1,0,1):r.line([foot,(foot[0]+5+toe*3,foot[1]-3)], GOLD[2],2)
    r.ball(x,y,19,23,SLATE)
    r.ball(x+2,y-4,12,16,PEARL)
    # Folded feather wings flare during the wind-up, then beat into a talon strike.
    wing=10*w+15*s
    for side in (-1,1):
        r.poly([(x+side*14,y+16),(x+side*(22+wing),y+4+17*w-18*s),
                (x+side*(19+wing),y-14-6*s),(x+side*12,y-18)],SLATE[1],OUTLINE)
        for j in range(3):
            r.line([(x+side*(17+j*2+wing*.5),y+3-j*5),(x+side*(20+wing),y-9-j*2)],AZURE[2],2)
    hx,hy=x+4+5*s,y+21
    r.ball(hx,hy,19,15,SLATE)
    for side in (-1,1):
        r.poly([(hx+side*10,hy+8),(hx+side*17,hy+24),(hx+side*3,hy+13)],SLATE[1],OUTLINE)
        r.ball(hx+side*8,hy,8,10,PEARL)
        r.poly([(hx+side*2,hy+5),(hx+side*15,hy+8),(hx+side*12,hy-4)],OUTLINE)
        if d<.75:r.ellipse(hx+side*8,hy+1,3,4,GOLD[3]);r.ellipse(hx+side*8+1,hy+1,1,3,OUTLINE)
    r.poly([(hx,hy-3),(hx+6,hy-8),(hx+1,hy-13)],GOLD[2],OUTLINE)
    crescent(r,x+3,y-7,6,PEARL[2])
    return a


def guard(setup, clip, n):
    a,r,w,s,d,ph,b=setup('solstice_guard',clip,n,(0,5),-1.18)
    x,y=12*s-7*w,32+b+4*w-16*d
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        foot=(x+side*11+step+side*5*d,4)
        r.limb([(x+side*8,y-10),(foot[0],14-7*d),foot],SLATE,6)
        r.ball(*foot,9,4,AZURE)
    r.ball(x,y+6,18,23,AZURE)
    r.poly([(x-15,y+21),(x,y+27),(x+15,y+21),(x+12,y-9),(x,y-14),(x-12,y-9)],AZURE[2],OUTLINE)
    r.line([(x,y+19),(x,y-7)],PEARL[3],2)
    r.ball(x,y+35,14,16,AZURE)
    for side in (-1,1):r.ball(x+side*12,y+38,6,7,PEARL)
    r.poly([(x-11,y+40),(x+11,y+40),(x+8,y+29),(x-8,y+29)],SLATE[0],OUTLINE)
    if d<.75:r.line([(x-8,y+35),(x+8,y+35)],TEAL[3],2)
    shield=(x-25-5*w,y+3-5*d)
    r.limb([(x-15,y+17),shield],AZURE,5)
    r.poly([(shield[0]-12,shield[1]+18),(shield[0]+10,shield[1]+18),(shield[0]+12,shield[1]-5),(shield[0],shield[1]-18),(shield[0]-12,shield[1]-5)],AZURE[2],OUTLINE)
    r.line([(shield[0],shield[1]+13),(shield[0],shield[1]-9)],PEARL[3],2)
    hand=(x+22+24*s-7*w,y+4+15*w-5*d)
    r.limb([(x+15,y+17),(x+21,y+8),hand],AZURE,5)
    r.ball(*hand,5,5,SLATE)
    # Spear rotates from raised preparation into a near-horizontal thrust.
    dx,dy=7+24*s,33-27*s
    tip=(hand[0]+dx,hand[1]+dy)
    r.line([(hand[0]-dx*.7,hand[1]-dy*.7),tip],BROWN[2],3)
    r.poly([(tip[0]-5,tip[1]-4),(tip[0]+5+7*s,tip[1]+12-8*s),(tip[0]+5,tip[1]-6)],PEARL[3],OUTLINE)
    return a


def watcher(setup, clip, n):
    a,r,w,s,d,ph,b=setup('solstice_watcher',clip,n,(0,5))
    x,y=11*s-6*w,48+b+7*w-29*d
    # Each hard ice component falls independently; none scales into a soft puddle.
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        r.limb([(x+side*(9+9*d),y-9),(x+side*(12+13*d)+step,5)],AZURE,5)
        r.ball(x+side*(13+17*d)+step,4,9,4,PEARL)
    for side in (-1,1):
        cx,cy=x+side*(10+21*d),y-8*d
        r.poly([(cx-side*10,cy+21),(cx+side*12,cy+14),(cx+side*15,cy-9),(cx-side*9,cy-16)],AZURE[2],OUTLINE)
        r.poly([(cx,cy+17),(cx+side*8,cy+9),(cx+side*6,cy-10)],PEARL[3])
        for j in range(2):
            bx=x+side*(8+j*10+16*d)
            r.poly([(bx-5,y+13-10*d),(bx,y+32-j*5-26*d),(bx+6,y+13-10*d)],AZURE[3],OUTLINE)
    if d<.85:
        r.ball(x,y+3,16*(1-.7*d),15*(1-.5*d),PEARL)
        r.ball(x+3+3*s,y+4,8*(1-.6*d),10*(1-.6*d),PURPLE)
        r.ellipse(x+5+3*s,y+5,2,7*(1-.6*d),OUTLINE)
        r.ellipse(x,y+9,2,2,WHITE)
        r.line([(x-16,y+16),(x+14,y+11)],SLATE[0],4)
    for side in (-1,1):
        hand=(x+side*(27+18*d)+(26*s if side==1 else 0),y-6+20*w-17*s-7*d)
        r.limb([(x+side*17,y+4),hand],AZURE,4)
        r.ball(*hand,7,7,PEARL)
    return a


def harbinger(setup, clip, n):
    a,r,w,s,d,ph,b=setup('solstice_harbinger',clip,n,(0,25))
    x,y=14*s-7*w,59+b+6*w-4*s
    fade=max(0,1-d)
    # Spectral feathers withdraw and the body dissipates upward into wisps.
    if d<.92:
        for side in (-1,1):
            for j in range(4):
                tip=(x+side*(36-j*5)*fade,y+18-j*10+9*w-12*s+25*d)
                r.poly([(x+side*9,y+14),(tip[0],tip[1]),(tip[0]-side*5,tip[1]-14*fade),(x+side*8,y-8)],SLATE[1+j%2],OUTLINE)
        # Rounded shoulders, ribcage and pinched waist give the cloak a body underneath.
        # Every volume uses the five-tone purple ramp, lit from the upper left.
        by=y+24*d
        for side in (-1,1):
            r.ball(x+side*13*fade,by+10*fade,7.5*fade,9*fade,PURPLE,side*.22)
        r.ball(x-fade,by+4*fade,15*fade,17*fade,PURPLE,-.10)
        r.ball(x,by-10*fade,10*fade,10*fade,PURPLE)
        # Overlapping hanging cloth folds form a rounded, split hem instead of a triangle.
        r.ball(x,by-22*fade,16*fade,12*fade,PURPLE)
        for j,(dx,drop) in enumerate(((-10,31),(-3,35),(5,33),(12,29))):
            flow=math.sin(ph+j*.7)*1.3 if clip in ('idle','walk') else -3*w+4*s
            r.taper([(x+dx*.55*fade,by-12*fade),
                     (x+(dx+flow)*fade,by-24*fade),
                     (x+(dx+flow*.5)*fade,by-drop*fade)],PURPLE,6*fade,1.2*fade)
        # Narrow crease shadows sit beside lit fabric ridges; these follow the belly.
        for dx in (-7,3,10):
            r.line([(x+dx*.5*fade,by-15*fade),(x+dx*fade,by-26*fade)],PURPLE[0],1)
            r.line([(x+(dx-1)*fade,by-16*fade),(x+(dx-2)*fade,by-25*fade)],PURPLE[3],1)
        r.line([(x-10*fade,by-10*fade),(x,by-13*fade),(x+9*fade,by-10*fade)],PURPLE[0],3)
        # Two fitted lapels and a small moon clasp describe the chest's curve.
        r.poly([(x-11*fade,by+16*fade),(x-4*fade,by+11*fade),(x,by+2*fade),
                (x-8*fade,by+7*fade)],SLATE[1],OUTLINE)
        r.poly([(x+10*fade,by+16*fade),(x+3*fade,by+10*fade),(x,by+2*fade),
                (x+8*fade,by+6*fade)],SLATE[0],OUTLINE)
        r.line([(x-10*fade,by+15*fade),(x-3*fade,by+9*fade)],PEARL[1],1)
        r.ball(x,by+2*fade,3*fade,3*fade,GOLD)
        # Hood is BEHIND the face; the old triangle hid the brow and eyes.
        fy=y+24+24*d
        r.poly([(x-15*fade,fy-7*fade),(x-14*fade,fy+10*fade),(x,fy+27*fade),
                (x+15*fade,fy+8*fade),(x+14*fade,fy-9*fade)],SLATE[0],OUTLINE)
        r.ball(x,fy,10.5*fade,13*fade,PEARL)
        # A distinct severe face: dark angular sockets, bright irises, nose and frown.
        for side in (-1,1):
            ex=x+side*5*fade
            r.poly([(ex-4*fade,fy+5*fade),(ex+4*fade,fy+5*fade),
                    (ex+3*fade,fy-1*fade),(ex-3*fade,fy-1*fade)],OUTLINE)
            r.ball(ex,fy+2*fade,3*fade,3.6*fade,TEAL)
            r.ellipse(ex+1.3*fade,fy+2*fade,.8*fade,2.5*fade,OUTLINE)
            r.ellipse(ex,fy+3*fade,.8*fade,.8*fade,WHITE)
            r.line([(ex-side*4*fade,fy+6*fade),(ex+side*4*fade,fy+9*fade)],SLATE[0],2)
        r.poly([(x+fade,fy+fade),(x+4*fade,fy-5*fade),(x,fy-6*fade)],PEARL[0])
        r.line([(x-4*fade,fy-9*fade),(x,fy-7*fade),(x+5*fade,fy-8*fade)],OUTLINE,2)
        # Sleeves end at two visible articulated hands, rather than a bare staff and wing.
        far=(x-22-5*w+8*s,y+3+9*w-6*s)
        r.limb([(x-10*fade,y+12),(x-17,y+6),far],PURPLE,5*fade)
        r.ball(*far,5.5*fade,5*fade,BONE)
        for j in range(3):
            r.limb([(far[0]+(j-1)*3*fade,far[1]),
                    (far[0]+(j-1)*4*fade,far[1]-6*fade),
                    (far[0]+(j-1)*4*fade+2*fade,far[1]-9*fade)],BONE,1.5*fade)
        hand=(x+23+28*s-7*w,y+4+18*w)
        r.limb([(x+10,y+12),(hand[0]-8*fade,hand[1]+2*fade),hand],PURPLE,5*fade)
        r.line([(hand[0]-2,hand[1]-7*fade),(hand[0]+2,hand[1]+20*fade)],PEARL[2],3)
        crescent(r,hand[0]+2,hand[1]+25*fade,7*fade)
        r.ball(*hand,5.5*fade,6*fade,BONE)
        # Fingers wrap across the shaft, thumb hooks over its near edge.
        for j in range(3):
            r.line([(hand[0]-3*fade,hand[1]+(3-j*2.5)*fade),
                    (hand[0]+3*fade,hand[1]+(2-j*2.5)*fade)],BROWN[0],1)
        r.limb([(hand[0]+3*fade,hand[1]+4*fade),
                (hand[0]+6*fade,hand[1]+fade),(hand[0]+3*fade,hand[1]-fade)],BONE,2*fade)
    if d>0:
        for j in range(5):
            if j < round(5*(1-d)):
                r.ball(x-14+j*7,y+20+30*d+j*3,3*(1-d)+.5,5*(1-d)+.5,PURPLE)
    # The crescent relic alone falls; spirit colours vanish entirely at the end.
    crescent(r,x-17-12*d,69-61*d**.18,7,SLATE[0])
    return a


def heart(setup, clip, n):
    a,r,w,s,d,ph,b=setup('solstice_heart',clip,n,(0,25))
    x,y=9*s-5*w,52+b+6*w-3*s
    spread=1+.18*w+.35*s
    # Six faceted rigid crystal petals orbit the core, then break and land individually.
    for j in range(6):
        ang=j*math.pi/3+(.08*math.sin(ph) if clip in ('idle','walk') else 0)
        radius=(23*spread)*(1-d)+(30+j%2*10)*d
        cx=x+math.cos(ang)*radius
        cy=(y+math.sin(ang)*radius)*(1-d)+(8+j%2*4)*d
        angle=ang+1.3*d
        pts=[]
        for dx,dy in [(0,15),(8,0),(0,-12),(-7,0)]:
            pts.append((cx+dx*math.cos(angle)-dy*math.sin(angle),cy+dx*math.sin(angle)+dy*math.cos(angle)))
        r.poly(pts,AZURE[2+j%2],OUTLINE)
        r.line([pts[0],(cx,cy),pts[2]],PEARL[3],2)
    if d<.9:
        r.ball(x,y,18*(1-.55*d),21*(1-.55*d),SLATE)
        r.poly([(x-12,y+13),(x,y+23),(x+13,y+13),(x+9,y-12),(x,y-20),(x-10,y-12)],AZURE[2],OUTLINE)
        # Star-shaped aperture rather than another round cyclops face.
        radius=9+5*w+7*s
        pts=[(x+math.cos(j*math.pi/4)*radius*(1 if j%2==0 else .4),y+math.sin(j*math.pi/4)*radius*(1 if j%2==0 else .4)) for j in range(8)]
        r.poly(pts,SLATE[0],OUTLINE)
        r.ellipse(x,y,3+2*s,6+3*w,TEAL[3])
        r.ellipse(x-1,y+3,1,2,WHITE)
    return a
