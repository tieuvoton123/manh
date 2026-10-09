#!/usr/bin/env python3
# Development helper only; the build artifact contains embedded glyph bitmaps,
# not a distributable font file. SVG/TTF/OTF not copied to ZIP.
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import unicodedata

BASE=Path(__file__).parent
FONT='/mnt/data/ChepGame_PS4_BGFT_ThemeProbe_v0.4.1_STB_FETCH_FIX/assets/noto_sans.ttf'
# Full precomposed Vietnamese combinations plus Latin, punctuation.
chars=set(range(32,127))
for base in 'AaEeIiOoUuYyĂăÂâÊêÔôƠơƯư':
    for tone in ('','\u0300','\u0301','\u0303','\u0309','\u0323'):
        n=unicodedata.normalize('NFC',base+tone)
        if len(n)==1:chars.add(ord(n))
for c in 'ĐđÁáÀàẠạÃãẢảÉéÈèẸẹẼẽẺẻÓóÒòỌọÕõỎỏÚúÙùỤụŨũỦủÝýỲỳỴỵỸỹỶỷ€£°•…–—():/\\[]_!?#%&+':
    chars.add(ord(c))
# Compose even older accents correctly, if support.
chars.update(ord(c) for c in 'ĂăÂâÊêÔôƠơƯưĐđ')
chars=sorted(chars)
records=[]
encoded=bytearray()
for size in (26,34,46):
    font=ImageFont.truetype(FONT,size)
    for cp in chars:
        ch=chr(cp)
        advance=round(font.getlength(ch))
        bbox=font.getbbox(ch,anchor='ls')
        if bbox is None:
            x0=y0=0;w=h=0;coverage=[]
        else:
            x0,y0,x1,y1=bbox
            w,h=max(0,x1-x0),max(0,y1-y0)
            coverage=[]
            if w and h:
                canvas=Image.new('L',(w,h),0)
                ImageDraw.Draw(canvas).text((-x0,-y0),ch,font=font,fill=255,anchor='ls')
                coverage=list(canvas.getdata())
        start=len(encoded)
        if coverage:
            count=1;value=coverage[0]
            for a in coverage[1:]:
                if a==value and count<255: count+=1
                else:
                    encoded.extend((count,value));count=1;value=a
            encoded.extend((count,value))
        records.append((cp,size,x0,y0,w,h,max(1,advance),start,len(encoded)-start))
out=BASE/'ChepGame-Installer/src/glyph_data.inc'
with out.open('w',encoding='utf-8') as f:
    f.write('// Antialiased glyph atlas, Noto Sans (SIL Open Font License 1.1).\n')
    f.write('// Generated from approved glyph outlines; original font files are not distributed.\n')
    f.write('static const uint8_t encoded[] = {\n')
    for i in range(0,len(encoded),30):
        f.write('  '+','.join(str(v) for v in encoded[i:i+30])+',\n')
    f.write('};\nstatic const GlyphRecord records[] = {\n')
    for cp,size,x0,y0,w,h,advance,start,n in records:
        f.write(f'  {{{cp},{size},{x0},{y0},{w},{h},{advance},{start},{n}}},\n')
    f.write('};\n')
print('glyphs:',len(records),'compressed data:',len(encoded),'bytes; file:',out.stat().st_size)
