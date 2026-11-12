"""Chained Forge native rigs: connected anatomy, attached tools and rigid material deaths."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, GOLD, BROWN, VIOLET, PEARL
IRON = FIRE = GLASS = CLOTH = SKIN = None


def plate(r, pts, ramp):
    r.poly(pts,ramp[1],OUTLINE)
    cx=sum(x for x,y in pts)/len(pts);cy=sum(y for x,y in pts)/len(pts)
    r.poly([pts[0],pts[1],(cx,cy)],ramp[3])
    r.poly([pts[-1],pts[0],(cx,cy)],ramp[2])


def cool(d,ramp=None):return (ramp or FIRE) if d<.65 else IRON


def chain(r,pts,ramp=None):
    ramp=ramp or GOLD
    for (x,y),(xx,yy) in zip(pts,pts[1:]):
        count=max(1,round(math.hypot(xx-x,yy-y)/5))
        for j in range(count+1):
            t=j/count;px=x+(xx-x)*t;py=y+(yy-y)*t
            r.ball(px,py,3.1 if j%2 else 2.4,2.4 if j%2 else 3.1,ramp)
            r.ellipse(px,py,1.1,1.1,IRON[0])


def joint(r,pts,ramp=None,width=4):
    ramp=ramp or IRON
    r.limb(pts,ramp,width)
    for x,y in pts[1:-1]:r.ball(x,y,width+1,width+1,GOLD)


def stack(r,x,y,height,d,tilt=0):
    joint(r,[(x,y),(x+tilt,y+height)],IRON,3)
    r.ball(x+tilt,y+height,5,2.8,IRON)
    r.ellipse(x+tilt,y+height+.5,3.3,1.3,cool(d)[3])


def face(r,x,y,d,style):
    """Individually drawn brows, sockets and mouths; sockets stay with the rigid skull."""
    if style=='brute':
        for side in (-1,1):
            ex=x+side*7
            r.poly([(ex-side*5,y+4),(ex+side*6,y+8),(ex+side*5,y-1),(ex-side*4,y-2)],OUTLINE)
            if d<.6:r.line([(ex-side*2,y+1),(ex+side*2,y+3)],FIRE[4],2)
        r.poly([(x-9,y-7),(x+8,y-7),(x+6,y-12),(x-7,y-12)],OUTLINE)
        for j in range(4):r.line([(x-6+j*4,y-8),(x-6+j*4,y-11)],GOLD[2],1)
    elif style=='sentry':
        plate(r,[(x-14,y+7),(x,y+15),(x+14,y+7),(x+10,y-11),(x,y-17),(x-10,y-11)],IRON)
        r.poly([(x-11,y+5),(x+10,y+7),(x+6,y-1),(x-7,y-3)],OUTLINE)
        if d<.6:r.line([(x-6,y+2),(x+6,y+3)],GLASS[4],2)
        r.line([(x,y+13),(x,y-13)],GOLD[2],2)
    elif style=='kettil':
        r.ball(x-6,y+1,5.5,5.5,SKIN);r.ball(x+7,y+2,5,4.5,SKIN)
        if d<.6:
            for ex in (x-6,x+7):
                r.ellipse(ex,y+2,3.7,3.8,WHITE);r.ellipse(ex+1,y+1,1.6,2.6,OUTLINE)
        r.line([(x-13,y+9),(x-2,y+4)],BROWN[0],3);r.line([(x+3,y+5),(x+13,y+9)],BROWN[0],3)
        r.line([(x-10,y-7),(x+9,y-7)],IRON[0],3)
        for j in range(4):r.line([(x-7+j*4,y-8),(x-7+j*4,y-12)],GOLD[2],1)
        r.line([(x-13,y+2),(x-10,y-10)],SKIN[0],1)
    elif style=='ysolt':
        for side in (-1,1):
            ex=x+side*6
            r.poly([(ex-side*4,y+4),(ex+side*4,y+6),(ex+side*3,y-1),(ex-side*3,y-2)],OUTLINE)
            if d<.65:r.line([(ex-side,y+1),(ex+side*2,y+2)],GLASS[4],2)
            r.line([(x+side*2,y+6),(x+side*12,y+10)],BROWN[0],3)
        plate(r,[(x-10,y-4),(x+10,y-4),(x+8,y-13),(x-8,y-13)],GOLD)
        for dx in (-5,0,5):r.line([(x+dx,y-6),(x+dx,y-11)],IRON[0],1)
    elif style=='hallgrim':
        for side in (-1,1):
            ex=x+side*6
            r.ball(ex,y+3,6,5,GOLD);r.ellipse(ex,y+3,4,3,IRON[0])
            if d<.6:r.line([(ex-2,y+4),(ex+2,y+4)],GLASS[3],2)
        r.line([(x-13,y+9),(x-1,y+6),(x+11,y+10)],IRON[0],3)
        r.poly([(x-10,y-6),(x+10,y-6),(x+7,y-16),(x,y-23),(x-7,y-15)],BROWN[1],OUTLINE)
        for dx in (-4,0,4):r.line([(x+dx,y-10),(x+dx*.5,y-19)],GOLD[2],1)
    elif style=='sigrun':
        for side in (-1,1):
            ex=x+side*6
            r.ellipse(ex,y+2,4.2,4,OUTLINE)
            if d<.6:r.ellipse(ex,y+2,2.2,2.8,FIRE[3]);r.ellipse(ex-1,y+3,1,1,WHITE)
            r.line([(ex+side*5,y+8),(ex-side*4,y+4)],BROWN[0],3)
        r.poly([(x-8,y-6),(x+8,y-5),(x+5,y-11),(x-6,y-11)],OUTLINE)
        r.line([(x-6,y-7),(x+5,y-7)],BONE[3],2)
    elif style=='dagfinn':
        for side in (-1,1):
            ex=x+side*7
            r.poly([(ex-side*4,y+4),(ex+side*4,y+6),(ex+side*3,y-2),(ex-side*3,y-2)],OUTLINE)
            if d<.65:r.ellipse(ex,y+1,2,2,WHITE)
        r.line([(x-13,y+9),(x-1,y+4)],BROWN[0],3);r.line([(x+2,y+5),(x+12,y+10)],BROWN[0],3)
        r.poly([(x-11,y-5),(x+10,y-5),(x+9,y-17),(x,y-24),(x-10,y-15)],BROWN[1],OUTLINE)
        for dx in (-6,0,6):r.line([(x+dx,y-8),(x+dx*.6,y-20)],GOLD[2],1)
    elif style=='thorbjorg':
        r.poly([(x-13,y+13),(x-15,y-8),(x-7,y-18),(x-9,y+4),(x+8,y+9),(x+12,y-14),(x+15,y+12)],BROWN[1],OUTLINE)
        for side in (-1,1):
            ex=x+side*5
            r.line([(ex-side*3,y+4),(ex+side*3,y+6)],OUTLINE,3)
            if d<.65:r.line([(ex-side,y+2),(ex+side*2,y+3)],FIRE[4],2)
        r.line([(x-5,y-7),(x+5,y-5)],IRON[0],2)
    elif style=='ragnhild':
        plate(r,[(x-14,y+6),(x-9,y+13),(x+10,y+16),(x+14,y+4),(x+9,y-7),(x-10,y-4)],IRON)
        r.line([(x-10,y+7),(x-1,y+3),(x+10,y+9)],IRON[0],3)
        if d<.65:
            r.line([(x-8,y+4),(x-3,y+2)],VIOLET[4],2);r.line([(x+3,y+2),(x+9,y+6)],VIOLET[3],2)
        r.line([(x-7,y-5),(x+7,y-4)],IRON[0],2)
    elif style=='orm':
        r.ball(x,y,16,15,GOLD);r.ball(x,y+1,12,11,IRON)
        for side in (-1,1):
            ex=x+side*6
            r.ball(ex,y+4,5,6,IRON);r.ellipse(ex,y+4,3.6,4.4,cool(d,GLASS)[2])
            if d<.65:r.line([(ex-1,y+6),(ex+1,y+3)],WHITE,1)
        joint(r,[(x,y-2),(x+2,y-15),(x+10,y-21)],IRON,3)
        r.line([(x-11,y+11),(x-1,y+8),(x+10,y+12)],GOLD[1],3)
    elif style=='hildr':
        plate(r,[(x-13,y+9),(x-9,y+19),(x+9,y+19),(x+13,y+8),(x+6,y+3),(x-6,y+3)],GLASS)
        for side in (-1,1):
            ex=x+side*5
            r.poly([(ex+side*4,y+6),(ex-side*3,y+2),(ex-side,y-3),(ex+side*3,y-1)],OUTLINE)
            if d<.65:r.line([(ex+side*2,y+3),(ex-side,y+1)],PEARL[4],1)
        r.line([(x-6,y+18),(x+7,y+5)],GOLD[2],1)
        r.poly([(x-4,y-9),(x+4,y-9),(x+2,y-13),(x-3,y-13)],OUTLINE)
    elif style=='eldmarr':
        for side in (-1,1):
            ex=x+side*7
            r.poly([(ex+side*6,y+7),(ex-side*5,y+3),(ex-side*4,y-4),(ex+side*4,y-2)],OUTLINE)
            if d<.65:r.line([(ex+side*3,y+2),(ex-side*2,y)],FIRE[4],2)
            r.line([(x+side*2,y+6),(x+side*14,y+11)],IRON[0],4)
        r.poly([(x-10,y-8),(x+10,y-8),(x+7,y-18),(x-7,y-18)],OUTLINE)
        for j in range(4):r.line([(x-7+j*4,y-10),(x-6+j*4,y-15)],cool(d)[3],2)
        r.line([(x-12,y+1),(x-8,y-5),(x-10,y-10)],cool(d)[3],1)


def humanoid(setup,kind,clip,n):
    styles={'cf_brute':(19,25,14,15,-1.12),'cf_sentry':(15,26,13,15,-1.58),
        'cf_kettil':(16,23,13,13,1.38),'cf_ysolt':(11,26,12,13,-1.43),
        'cf_hallgrim':(19,23,14,13,1.48),'cf_sigrun':(18,25,13,14,-1.46),
        'cf_dagfinn':(18,23,14,14,1.33),'cf_thorbjorg':(15,24,12,14,-1.39),
        'cf_ragnhild':(17,23,13,12,1.50),'cf_orm':(18,23,14,13,-1.37),
        'cf_hildr':(16,24,13,14,1.57),'cf_eldmarr':(21,25,15,14,-1.29)}
    width,th,hrx,hry,angle=styles[kind]
    a,r,w,s,d,ph,b=setup(kind,clip,n,(0,16),angle)
    x=11*s-6*w;y=31+b+4*w-8*d
    style=kind[3:]
    body=IRON if style in ('brute','sentry','eldmarr','orm','kettil') else GLASS if style=='hildr' else CLOTH
    skin=IRON if style in ('brute','sentry','eldmarr') else SKIN
    # Knees and elbows fold as the whole unscaled body tips over.
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        toe=(x+side*(11+3*d)+step,4+16*d)
        joint(r,[(x+side*8,y-8),(x+side*(14-5*d)+step,16+11*d),toe],IRON,4.3)
        r.ball(toe[0]+2,toe[1],8,4.2,IRON)
    # Distinct back regalia is connected to shoulder sockets.
    if style=='brute':
        stack(r,x-18,y+15,23,d,-3)
    if style=='kettil':
        for side in (-1,1):chain(r,[(x+side*16,y+22),(x+side*(27-9*d),y+8),(x+side*19,y-9+12*d)])
        for side in (-1,1):plate(r,[(x+side*10,y+26),(x+side*23,y+24),(x+side*25,y+13),(x+side*12,y+15)],IRON)
    if style=='ysolt':
        for side in (-1,1):
            bx=x+side*23;by=y+18
            height=24+11*w-8*s-5*d
            plate(r,[(bx-8,by-4),(bx+8,by-4),(bx+8,by+height),(bx-8,by+height)],IRON)
            for j in range(6):r.line([(bx-7,by+j*height/6),(bx+7,by+j*height/6+2)],CLOTH[2],2)
            joint(r,[(bx,by+height),(bx+side*4,by+height+10)],GOLD,3)
            r.ball(bx+side*4,by+height+11,5,3,GLASS)
            if s>0 and d==0:r.taper([(bx+side*4,by+height+12),(bx+side*(8+8*s),by+height+20*s),(bx+side*(12+20*s),by+height+26*s)],FIRE,5*s,1)
    if style=='hallgrim':
        plate(r,[(x-27,y+19),(x-30,y+29),(x-11,y+29),(x-9,y+22),(x+12,y+22),(x+26,y+32),(x+29,y+24),(x+14,y+17),(x-14,y+17)],IRON)
    if style=='sigrun':
        for side in (-1,1):
            plate(r,[(x+side*10,y+16),(x+side*28,y+20),(x+side*26,y+5),(x+side*15,y+5)],IRON)
            r.line([(x+side*17,y+17),(x+side*22,y+8)],cool(d)[2],2)
    if style=='dagfinn':
        for side in (-1,1):
            xx=x+side*23;yy=y+23
            r.ball(xx,yy,11,11,GOLD);r.ball(xx,yy,7,7,IRON)
            for j in range(6):
                t=j*math.tau/6+s*.6
                r.line([(xx,yy),(xx+9*math.cos(t),yy+9*math.sin(t))],GOLD[3],2)
    if style=='thorbjorg':
        for j,xx in enumerate((-22,0,22)):
            yy=y+34+(j%2)*8
            joint(r,[(x+xx*.5,y+20),(x+xx,yy)],BROWN,3)
            r.ball(x+xx,yy+5,6,9,GOLD);r.ball(x+xx,yy+5,3,6,cool(d))
            for dx in (-3,3):r.line([(x+xx+dx,yy-2),(x+xx+dx,yy+12)],IRON[1],1)
    if style=='ragnhild':
        for j,xx in enumerate((-25,-17,17,25)):stack(r,x+xx,y+12,25+(j%2)*10,d,-d*6)
    if style=='orm':
        r.ball(x,y+18,28,24,IRON);r.ball(x,y+21,23,20,GOLD)
        for side in (-1,1):
            r.ball(x+side*20,y+26,5,12,cool(d,GLASS))
            joint(r,[(x+side*25,y+10),(x+side*29,y-5+8*d)],IRON,3)
    if style=='hildr':
        for j in range(7):
            t=math.pi*j/6;xx=x+math.cos(t)*28;yy=y+18+math.sin(t)*33
            if d==0:
                joint(r,[(x+math.cos(t)*18,y+20),(xx,yy)],GOLD,1.3)
                plate(r,[(xx-5,yy),(xx,yy+11),(xx+5,yy),(xx,yy-7)],GLASS)
            else:
                # Mirror-halo plates break away, rotate rigidly and land beside the fallen body.
                from lapis_slime_redraw import Rig
                wx,wy=r.t(xx,yy);targetx=-34+j*12;targety=9+(j%2)*3
                cx=wx*(1-d)+targetx*d;cy=wy*(1-d)+targety*d
                q=Rig(a,cx,cy,(j%2*2-1)*1.25*d)
                plate(q,[(cx-5,cy),(cx,cy+11),(cx+5,cy),(cx,cy-7)],GLASS)
                q.line([(cx-3,cy+3),(cx+2,cy-2)],IRON[0],1)
        for side in (-1,1):chain(r,[(x+side*22,y+20),(x+side*25,y+4),(x+side*20,y-6+10*d)])
    if style=='eldmarr':
        for side in (-1,1):
            plate(r,[(x+side*12,y+20),(x+side*31,y+28),(x+side*34,y+13),(x+side*22,y+3)],IRON)
            chain(r,[(x+side*28,y+16),(x+side*30,y),(x+side*22,y-8+10*d)])
    r.ball(x,y+9,width,th,body)
    r.ball(x-2,y+16,width*.75,th*.72,body)
    if style in ('brute','eldmarr','sigrun'):
        plate(r,[(x-12,y+22),(x+12,y+22),(x+14,y-7),(x-14,y-7)],IRON)
        for j in range(3):r.line([(x-9,y+17-j*7),(x+9,y+17-j*7)],cool(d)[2],2)
    else:r.line([(x-10,y+21),(x,y-7),(x+10,y+21)],GOLD[2],2)
    hx=x;hy=y+th+18
    joint(r,[(x,y+th),(hx,hy-9)],skin,6)
    r.ball(hx,hy,hrx,hry,skin)
    if style in ('kettil','ysolt','hallgrim','sigrun','dagfinn','thorbjorg'):
        plate(r,[(hx-hrx,hy+7),(hx-hrx+3,hy+16),(hx+hrx-3,hy+16),(hx+hrx,hy+7)],BROWN if style=='thorbjorg' else IRON)
    if style in ('kettil','ysolt','sigrun','eldmarr'):
        # Crown band overlaps the skull; all teeth share the head's transform.
        plate(r,[(hx-hrx-1,hy+8),(hx+hrx+1,hy+8),(hx+hrx,hy+14),(hx-hrx,hy+14)],GOLD)
        teeth=9 if style=='eldmarr' else 6 if style=='sigrun' else 3
        for j in range(teeth):
            xx=hx-hrx+2+j*(2*hrx-4)/max(1,teeth-1)
            joint(r,[(xx,hy+13),(xx+(j-teeth/2)*.3,hy+22+(j%3)*2)],IRON,1.5)
            r.ball(xx+(j-teeth/2)*.3,hy+23+(j%3)*2,1.7,2.2,cool(d))
    face(r,hx,hy,d,style)
    # Back arm folds close; hand and every held object share exact attachment coordinates.
    left=(x-22+9*d,y+6+10*d)
    joint(r,[(x-width+2,y+21),(x-27+10*d,y+12),left],skin,4.4)
    r.ball(*left,5.6,5.6,skin)
    hand=(x+22-9*w+18*s-10*d,y+7+26*w-15*s+12*d)
    joint(r,[(x+width-2,y+21),(x+27-6*w-6*d,y+17+10*w),hand],skin,4.8)
    angle=-.12-1.1*w+1.28*s-1.0*d
    ux,uy=math.sin(angle),math.cos(angle)
    vx,vy=uy,-ux
    def p(u,v):return hand[0]+vx*u+ux*v,hand[1]+vy*u+uy*v
    def shaft(length=29,ramp=None):joint(r,[p(0,-13),p(0,length)],ramp or GOLD,2.4)
    if style in ('brute','hallgrim'):
        shaft();plate(r,[p(-13,20),p(13,20),p(13,35),p(-13,35)],IRON)
        r.line([p(-9,27),p(9,27)],cool(d)[2],2)
        for xx in (-9,9):r.ball(*p(xx,31),1.8,1.8,GOLD)
    elif style=='sentry':
        plate(r,[p(-15,19),p(14,19),p(18,-4),p(0,-21),p(-17,-4)],IRON)
        plate(r,[p(-10,14),p(9,14),p(12,-2),p(0,-15),p(-11,-2)],cool(d,GLASS))
        r.line([p(0,12),p(0,-11)],GOLD[2],2)
    elif style=='kettil':
        r.ball(*p(0,7),10,10,GOLD);r.ball(*p(0,7),5.2,5.2,IRON)
        chain(r,[p(0,13),p(6-8*w,25+8*w),p(16+15*s,18-18*s)])
        r.ball(*p(16+15*s,18-18*s),7,7,IRON)
    elif style=='ysolt':
        shaft();r.ball(*p(0,31),8,10,GLASS);r.ball(*p(0,31),3,4,IRON)
        if s>0 and d==0:r.taper([p(0,39),p(6*s,49),p(18*s,51)],GLASS,5*s,1)
    elif style=='sigrun':
        shaft();r.ball(*p(0,33),12,7,IRON);r.ball(*p(0,35),9,3,cool(d))
        if s>0 and d==0:r.taper([p(8,33),p(8+6*s,33-20*s),p(8+10*s,33-40*s)],FIRE,4,1)
    elif style=='dagfinn':
        for side in (-1,1):
            joint(r,[p(side*3,-12),p(side*(8+7*w-5*s),23),p(side*(4+3*w-2*s),34)],IRON,2.5)
        r.ball(*hand,3,3,GOLD)
    elif style=='thorbjorg':
        shaft(26,BROWN);r.ball(*p(0,31),9,12,GOLD);r.ball(*p(0,32),5,8,cool(d))
        for dx in (-5,0,5):r.line([p(dx,22),p(dx,42)],IRON[1],1)
        if s>0 and d==0:r.taper([p(0,40),p(6*s,46+4*s),p(13*s,47+5*s)],FIRE,7*s,1)
    elif style=='ragnhild':
        shaft();r.ball(*p(0,31),10,6,IRON);r.line([p(-7,32),p(7,32)],cool(d,VIOLET)[3],2)
        if s>0 and d==0:
            for j in range(3):
                vv=34+j*5*s
                r.line([p(-5-j*3*s,vv),p(0,vv+4*s),p(5+j*3*s,vv)],VIOLET[3],2)
    elif style=='orm':
        plate(r,[p(-8,-7),p(8,-7),p(9,19),p(0,28),p(-9,19)],IRON)
        r.ball(*p(0,13),5,9,cool(d,GLASS))
        if s>0 and d==0:r.taper([p(0,28),p(9*s,40),p(24*s,32)],GLASS,5*s,1)
    elif style=='hildr':
        plate(r,[p(-13,-5),p(-13,20),p(0,33),p(13,20),p(13,-5),p(0,-12)],GOLD)
        plate(r,[p(-9,-2),p(-9,18),p(0,27),p(9,18),p(9,-2),p(0,-7)],GLASS)
        r.line([p(-6,20),p(7,1)],IRON[0],1)
    elif style=='eldmarr':
        shaft(30);plate(r,[p(-10,9),p(14,12),p(17,34),p(3,43),p(-12,35)],IRON)
        plate(r,[p(10,15),p(13,18),p(13,32),p(2,38),p(-7,33)],cool(d))
        for j in range(4):r.line([(hx-8+j*5,hy-15),(hx-6+j*4,hy-27)],cool(d)[2],2)
    r.ball(*hand,5.5,5.5,skin)
    if d>.25 and style in ('brute','sentry','eldmarr','hildr'):
        r.line([(x-7,y+20),(x+2,y+12),(x-2,y+5),(x+8,y-4)],IRON[0],2)
    return a


def crawler(setup,clip,n):
    a,r,w,s,d,ph,b=setup('cf_crawler',clip,n,(0,18),1.55)
    x=12*s-6*w;y=27+b+7*w-5*d
    for side in (-1,1):
        for j in range(3):
            xx=x-17+j*16;step=math.sin(ph+j*2+side)*5 if clip=='walk' else 0
            joint(r,[(xx,y),(xx+side*(20-10*d),y-10+step),(xx+side*(24-19*d)+step,4+18*d)],IRON,2.8)
    r.ball(x,y+3,25,19,IRON)
    for j in range(3):stack(r,x-16+j*15,y+18,18+(j%2)*10,d,4*d)
    for j in range(4):r.line([(x-20+j*11,y-3),(x-17+j*11,y+15)],cool(d)[2],2)
    hx=x+19+9*s;hy=y+2
    r.ball(hx,hy,12,10,IRON)
    for j in range(6):
        ex=hx-7+(j%3)*6;ey=hy+5-(j//3)*6
        r.ellipse(ex,ey,2.5,2.5,OUTLINE)
        if d<.65:r.ellipse(ex,ey,1.3,1.3,FIRE[3])
    for side in (-1,1):
        joint(r,[(hx+side*6,hy-4),(hx+side*(10+8*w-4*s),hy-11),(hx+side*5,hy-15+6*s)],GOLD,2)
    if s>0 and d==0:
        for j in range(3):r.taper([(x-16+j*15,y+38),(x-9+j*15+8*s,y+42+10*s),(x-4+j*15+18*s,y+35+12*s)],FIRE,4*s,1)
    return a


def caster(setup,clip,n):
    a,r,w,s,d,ph,b=setup('cf_caster',clip,n,(0,45),-1.5)
    x=10*s-5*w;y=48+b+5*w
    for side in (-1,1):
        joint(r,[(x+side*17,y),(x+side*(29-9*d),y+17),(x+side*(21-6*d),y+37)],IRON,3)
        r.ball(x+side*(21-6*d),y+37,5,3,IRON)
    plate(r,[(x-25,y+5),(x+25,y+5),(x+18,y-20),(x-18,y-20)],IRON)
    r.ball(x,y+5,25,7,GOLD);r.ball(x,y+6,19,4,cool(d))
    for j in range(6):r.line([(x-19+j*7,y+1),(x-13+j*5,y-15)],GLASS[2],1)
    if d<.92:
        r.ball(x,y+22,13*(1-.82*d),17*(1-.82*d),FIRE)
        r.poly([(x-10,y+29),(x-2,y+24),(x-3,y+18),(x-9,y+20)],OUTLINE)
        r.poly([(x+2,y+24),(x+10,y+30),(x+9,y+19),(x+3,y+18)],OUTLINE)
        if d<.65:
            r.line([(x-8,y+24),(x-4,y+22)],WHITE,2);r.line([(x+4,y+22),(x+8,y+25)],WHITE,2)
        r.poly([(x-5,y+15),(x,y+11),(x+6,y+16),(x,y+18)],OUTLINE)
    # Flame jets change shape and gutter into the crucible; iron stays unscaled.
    for j in range(3):
        xx=x-10+j*10
        if d<.92:r.taper([(xx,y+32),(xx+math.sin(ph+j)*4,y+43+9*w),(xx+4+13*s,y+51+12*w-24*d)],cool(d),5*(1-.8*d),.8)
    if s>0 and d==0:r.taper([(x+13,y+26),(x+24+12*s,y+22),(x+32+20*s,y+13)],FIRE,8*s,1)
    if d>.25:r.line([(x-17,y),(x-9,y-7),(x+2,y-4),(x+12,y-17)],IRON[0],2)
    return a


def ingot(setup,clip,n):
    from lapis_slime_redraw import Rig
    a,r,w,s,d,ph,b=setup('cf_ingot',clip,n,(0,10),0)
    x=4*s-2*w+((-3,-1,2,0)[n] if clip=='hurt' else 0);y=13+b*.35+4*w
    # It cannot attack: this clip is a shield-warning pulse, never a damage swing.
    for side in (-1,1):
        cx=x+side*(12+9*d);cy=y+3*d
        q=Rig(a,cx,cy,-side*1.57*d)
        def p(u,v):return cx+side*u,cy+v
        plate(q,[p(-11,-12),p(12,-12),p(7,9),p(-11,9)],IRON)
        plate(q,[p(-11,9),p(7,9),p(1,17),p(-11,17)],GOLD)
        plate(q,[p(-8,-8),p(6,-8),p(2,5),p(-8,5)],cool(d))
        for u in (-6,-1,4):q.line([p(u,-6),p(u-1,3)],IRON[0],1)
        q.line([p(-8,14),p(-5,4),p(-10,-3),p(-8,-11)],IRON[0],2)
    if w>.08 and d==0:
        for side in (-1,1):
            # The shield charges along its own sides before the warning pulse.
            r.line([(x+side*24,y-10),(x+side*(25+8*w),y+2),(x+side*(22+8*w),y+19)],FIRE[2],3)
    if s>.08 and d==0:
        for side in (-1,1):r.line([(x+side*25,y),(x+side*(25+18*s),y+6*s),(x+side*(25+24*s),y+18*s)],FIRE[3],2)
    if d>.2:
        for j in range(3):
            xx=x-12+j*13+(j-1)*8*d;yy=5+(j%2)*2
            plate(r,[(xx-4,yy),(xx+5,yy),(xx+2,yy+5)],IRON)
    return a


# Explicit entry points keep the kind-to-anatomy mapping reviewable.
def brute(setup,c,n):return humanoid(setup,'cf_brute',c,n)
def sentry(setup,c,n):return humanoid(setup,'cf_sentry',c,n)
def kettil(setup,c,n):return humanoid(setup,'cf_kettil',c,n)
def ysolt(setup,c,n):return humanoid(setup,'cf_ysolt',c,n)
def hallgrim(setup,c,n):return humanoid(setup,'cf_hallgrim',c,n)
def sigrun(setup,c,n):return humanoid(setup,'cf_sigrun',c,n)
def dagfinn(setup,c,n):return humanoid(setup,'cf_dagfinn',c,n)
def thorbjorg(setup,c,n):return humanoid(setup,'cf_thorbjorg',c,n)
def ragnhild(setup,c,n):return humanoid(setup,'cf_ragnhild',c,n)
def orm(setup,c,n):return humanoid(setup,'cf_orm',c,n)
def hildr(setup,c,n):return humanoid(setup,'cf_hildr',c,n)
def eldmarr(setup,c,n):return humanoid(setup,'cf_eldmarr',c,n)
