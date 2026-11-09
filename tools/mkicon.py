import math, sys
from PIL import Image, ImageDraw
S=2048
def icon(size, pad):  # pad: fraction kept clear for maskable safe zone
    im=Image.new('RGB',(S,S),'#0A6B7C'); d=ImageDraw.Draw(im)
    # water band
    wy=S*0.60
    d.rectangle([0,wy,S,S],fill='#08566A')
    w=S*(1-2*pad)*0.92; cx=S/2
    N=400; top=[]; bot=[]
    for i in range(N+1):
        t=-1+2*i/N; x=cx+t*w/2; at=abs(t)
        sheer=wy-S*0.10 - S*0.12*at**5
        keel=wy+S*0.075*(1-at**2.5)**0.6
        if at>0.72:
            f=(at-0.72)/0.28; keel=keel+(sheer-keel)*(1-math.sqrt(max(0,1-f*f)))
        top.append((x,sheer)); bot.append((x,keel))
    d.polygon(top+bot[::-1],fill='#E9F1F5')
    g=S*0.028; band=[(x,y-g*0.4) for x,y in top]+[(x,y+g*0.6) for x,y in top[::-1]]
    d.polygon(band,fill='#C8692A')
    # water drawn over the lower hull, slightly translucent look
    ov=Image.new('RGBA',(S,S),(0,0,0,0)); od=ImageDraw.Draw(ov)
    od.rectangle([0,wy,S,S],fill=(8,86,106,150)); im.paste(ov,(0,0),ov); d=ImageDraw.Draw(im)
    d.line([(0,wy),(S,wy)],fill='#4CC3D8',width=int(S*0.012))
    return im.resize((size,size),Image.LANCZOS)
out=sys.argv[1]
icon(180,0.06).save(out+'/apple-touch-icon.png')
icon(192,0.06).save(out+'/icon-192.png')
icon(512,0.06).save(out+'/icon-512.png')
icon(512,0.16).save(out+'/icon-maskable-512.png')
icon(32,0.04).save(out+'/favicon-32.png')
