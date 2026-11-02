from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
OUT=Path('/mnt/data/Assignment2_Training_Audit_Feature/evidence/component_diagram.png')
W,H=1700,650
im=Image.new('RGB',(W,H),'#ffffff');d=ImageDraw.Draw(im)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
f=ImageFont.truetype(font,24);s=ImageFont.truetype(font,23);head=ImageFont.truetype(bold,31);small=ImageFont.truetype(font,21)

def box(x,y,w,h,title,lines,color='#f1f6f9',border='#8eacbf'):
 d.rounded_rectangle((x,y,x+w,y+h),radius=15,fill=color,outline=border,width=3)
 d.rounded_rectangle((x,y,x+w,y+67),radius=15,fill=color,outline=border,width=3)
 d.line((x,y+67,x+w,y+67),fill=border,width=3)
 d.text((x+22,y+17),title,font=head,fill='#1c3348')
 for j,t in enumerate(lines):d.text((x+20,y+86+35*j),t,font=s,fill='#263849')

def arrow(x1,y1,x2,y2,label='',pos=None):
 d.line((x1,y1,x2,y2),fill='#337d90',width=5)
 import math
 a=math.atan2(y2-y1,x2-x1);r=15
 d.polygon([(x2,y2),(x2-r*math.cos(a-.55),y2-r*math.sin(a-.55)),(x2-r*math.cos(a+.55),y2-r*math.sin(a+.55))],fill='#337d90')
 if label:d.text(pos or ((x1+x2)//2-60,(y1+y2)//2-35),label,font=small,fill='#315c72')

box(25,40,355,220,'Browser UI',['HTML / CSS / JS','submit event listener','showErrors()','renderRecent()'],color='#e5f4f1',border='#61aaa3')
box(445,40,335,220,'HTTP Handler',['GET /api/audits','POST /api/audits','returns JSON'])
box(842,40,345,220,'AuditService',['record(payload)','recent()','uses validation'])
box(1248,40,425,220,'AuditRepository',['create(values)','latest(limit)','parameterized SQL'])
arrow(380,145,440,145,'JSON',(381,104))
arrow(780,145,837,145,'call',(780,104))
arrow(1187,145,1243,145,'call',(1186,104))
box(850,375,337,208,'validate_audit()',['Required values','Valid dates / choices','Note: 10–500 chars'],color='#f0ecfc',border='#a5a0cf')
box(1248,375,425,208,'SQLite audits table',['id INTEGER PRIMARY KEY','date · area · result','note · timestamp'],color='#fff5df',border='#d1b16d')
arrow(1020,260,1020,370,'checks',(1036,303))
arrow(1455,260,1455,370,'SQL',(1470,305))
im.save(OUT)
print(OUT,im.size)
