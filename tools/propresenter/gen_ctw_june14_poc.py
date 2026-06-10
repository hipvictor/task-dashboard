import sys; sys.path.insert(0,'/root/ppgen')
import pb

SRC="/root/.claude/uploads/e1f65a43-907e-5465-98e0-2ff8fdb0909d/ex/CALL TO WORSHIP-2.pro"
OUT="/root/ppgen/CALL TO WORSHIP-2.pro"   # same filename so the playlist manifest resolves

# ---- RTF builder ----
def esc(t):
    out=[]
    for ch in t:
        o=ord(ch)
        if ch=='\\': out.append('\\\\')
        elif ch=='{': out.append('\\{')
        elif ch=='}': out.append('\\}')
        elif o<128: out.append(ch)
        else:
            cp1252={0x2019:"\\'92",0x2018:"\\'91",0x201c:"\\'93",0x201d:"\\'94",
                    0x2014:"\\'97",0x2013:"\\'96",0x00a0:"\\'a0",0x2026:"\\'85"}
            out.append(cp1252.get(o, "\\u%d?"%o))
    return ''.join(out)

def rtf(runs, fs):
    # runs: list of (bold, text). text may contain '\n' -> hard line break
    pre=("{\\rtf1\\ansi\\ansicpg1252\\cocoartf2870\n"
         "\\cocoatextscaling0\\cocoaplatform0{\\fonttbl\\f0\\fnil\\fcharset0 HelveticaNeue-Bold;\\f1\\fnil\\fcharset0 HelveticaNeue;}\n"
         "{\\colortbl;\\red255\\green255\\blue255;\\red255\\green255\\blue255;}\n"
         "{\\*\\expandedcolortbl;;\\cssrgb\\c100000\\c100000\\c100000;}\n"
         "\\deftab1680\n"
         "\\pard\\pardeftab1680\\pardirnatural\\qc\\partightenfactor0\n\n")
    body=""
    first=True
    for bold,text in runs:
        f="\\f0\\b" if bold else "\\f1\\b0"
        body+=f+"\\fs%d \\cf2 "%fs
        # hard line breaks: backslash + newline (RTF style used by the template)
        body+= esc(text).replace("\n","\\\n")
    return pre+body+"}"

# ---- Juneteenth June 14 liturgy ----
T="—"  # em dash
slots = {
 0: rtf([(True,"Call To Worship\nJuneteenth")], 110),
 4: rtf([(True,"Leader: "),(False,"We gather as people still learning %s unlearning what the world taught us, and leaning toward the truth.\n\n"%T),
         (True,"People: "),(False,"Teach us to listen, and to stay at the table when listening is hard.")],130),
 7: rtf([(True,"Leader: "),(False,"Long before the news ever reached Galveston, freedom was already true. God’s “yes” had already been spoken.\n\n"),
         (True,"People: "),(False,"We come believing that liberation delayed is still liberation promised %s and ours to carry."%T)],130),
 10:rtf([(True,"Leader: "),(False,"God is already moving toward the margins, calling every beloved and colorfully made child by name.\n\n"),
         (True,"People: "),(False,"May we go where God goes, and tell the ones still waiting that they are free.")],140),
 13:rtf([(True,"All: "),(False,"We are God’s learning, loving, justice-seeking people. Let us worship %s and then let us go and do better."%T)],130),
}

raw=open(SRC,'rb').read()
root=pb.parse(raw)

# collect rtf leaves with their ancestor chain
leaves=[]
def walk(fields, chain):
    for f in fields:
        if f.wt==2 and f.msg is not None: walk(f.msg, chain+[f])
        elif f.wt==2:
            try: s=f.value.decode('utf-8')
            except:
                try: s=f.value.decode('latin-1')
                except: s=None
            if s and 'rtf1' in s: leaves.append((f, chain))
walk(root, [])

for idx,new in slots.items():
    f,chain=leaves[idx]
    f.value=new.encode('utf-8'); f.dirty=True
    for anc in chain: anc.dirty=True

out=pb.encode(root)
open(OUT,'wb').write(out)
print("wrote", OUT, len(out), "bytes (orig", len(raw),")")

# validate: re-parse and re-extract text
import importlib
r2=pb.parse(open(OUT,'rb').read())
got=[]
def w2(fields):
    for f in fields:
        if f.wt==2 and f.msg is not None: w2(f.msg)
        elif f.wt==2:
            try: s=f.value.decode('utf-8')
            except: s=None
            if s and 'rtf1' in s: got.append(s)
w2(r2)
import re
def vis(rtf):
    b=re.sub(r'\{\\[^{}]*\}','',rtf)
    b=re.sub(r'\\[a-zA-Z]+-?\d* ?',' ',b).replace('\\\\','').replace('{','').replace('}','')
    return ' '.join(b.split())
print("\n--- regenerated slide texts ---")
for i in (0,4,7,10,13):
    print(f'[{i}]', vis(got[i])[:200])
