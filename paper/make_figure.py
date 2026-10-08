from pathlib import Path
from html import escape
D=Path(__file__).parent
s=[]
s.append('''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="990" viewBox="0 0 1600 990"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="none" stroke="#586777" stroke-width="1.2"/></marker></defs><rect width="1600" height="990" fill="white"/>''')
def text(x,y,t,size=27,bold=False,color='#1c2734',anchor='start'):
 s.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Noto Sans, DejaVu Sans, Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(t)}</text>')
def rect(x,y,w,h,fill='#f6f8fa',stroke='#b8c3cf',r=10):
 s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
def line(x1,y1,x2,y2,dash=False,arrow=False,col='#586777'):
 s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="2.5"'+(' stroke-dasharray="9 7"' if dash else '')+(' marker-end="url(#arrow)"' if arrow else '')+'/>')
def box(x,y,w,h,lines,fill='#f6f8fa',size=26):
 rect(x,y,w,h,fill)
 for j,t in enumerate(lines):text(x+w/2,y+(h-(len(lines)-1)*36)/2+10+j*36,t,size,anchor='middle')
text(40,39,'PROPOSED EXPERIMENT',23,True,'#526478')
text(1555,39,'Schematic only • no model results',23,False,'#526478','end')
text(45,97,'1  A shared workflow',30,True)
text(470,97,'2  Change advice lifetime',30,True)
text(1150,97,'3  Score later states',30,True)
line(438,116,438,877,col='#d9e0e7')
line(1124,116,1124,877,dash=True,col='#667b91')
# Left
text(47,151,'After progress, work remains',25,True)
box(47,174,362,124,['G1 achieved; still required','G2 not yet achieved'],'#eef5ef',25)
text(47,327,'Illustrative evaluator labels',22,False,'#687684')
box(47,373,362,99,['Public history and tools','Pending actor action a0'])
line(228,474,228,516,arrow=True)
box(47,526,362,104,['Reviewer draws q = (a1, m)','One draw, then frozen'],'#edf2fa',25)
line(228,632,228,674,arrow=True)
box(47,684,362,101,['Execute selected action a1','Record the actual result'],size=25)
text(48,835,'Dispatch uses public evidence only',21,True)
# Middle
text(470,151,'Same action and factual receipt',26,True)
text(470,192,'Native history stays available in every arm',23,False,'#586777')
text(710,256,'First request',24,True,anchor='middle')
text(981,256,'Later requests',24,True,anchor='middle')
# exposure table
rows=[('A','No packet','No packet','#f6f8fa'),('R','m + neutral','No packet','#f3f5f7'),('P','m + neutral','m + neutral','#edf2fa'),('C','m + neutral','m + status*','#edf4f3')]
for i,(label,c1,c2,fill) in enumerate(rows):
 y=285+i*105
 text(477,y+47,label,33,True)
 box(550,y,305,80,[c1],fill,size=29)
 box(890,y,203,80,[c2],fill,size=26)
 line(857,y+40,878,y+40,arrow=True)
text(470,737,'P, R and C share the first exposure segment.',23)
text(470,774,'Fork before the next actor request;',23)
text(470,811,'sample independent suffixes after the split.',23)
text(470,853,'* C is the primary same-text status treatment.',21,False,'#586777')
# Right
text(1150,151,'EVALUATOR ONLY',24,True,'#526478')
text(1150,190,'Actual states → hidden predicates',23)
text(1150,239,'Illustrative V+ trajectories',22,False,'#586777')
for y,title,seq,col in [(300,'Retained','True → True → True','#3c7654'),(445,'Recovered','True → False → True','#916d25'),(590,'Unresolved at termination','True → False → False','#9d4c49')]:
 text(1150,y,title,25,True,col)
 box(1150,y+22,402,71,[seq],'#ffffff',25)
text(1150,758,'Terminal unresolved loss',24,True)
text(1150,799,'Official task completion',24,True)
text(1150,840,'Cost and latency',24,True)
# footer boundary /notes
line(43,889,1555,889,col='#d9e0e7')
text(46,928,'Private goal labels never enter actor, reviewer, or controller inputs.',25,True)
text(46,966,'C closes only publicly verified local scope. R removes the full packet, so useful information can also be lost.',23,False,'#586777')
s.append('</svg>')
(D/'reviewer_advice_overview.svg').write_text('\n'.join(s))
