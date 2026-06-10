import sys; sys.path.insert(0,'/root/ppgen'); import importlib, pb; importlib.reload(pb)

SRC="/root/.claude/uploads/e1f65a43-907e-5465-98e0-2ff8fdb0909d/ex/CALL TO WORSHIP-2.pro"
OUT="/root/ppgen/CALL TO WORSHIP-2.pro"

# ---- content: list of (bold, text) segments per slide; '\n' = 1 char line break ----
slides = {
 0: [(True, "Call To Worship\nJuneteenth")],   # title: default font is Helvetica-Bold (whole bold)
 4: [(False,"Leader: We gather as people still learning — unlearning what the world taught us, and leaning toward the truth.\n\n"),
     (True, "People: Teach us to listen, and to stay at the table when listening is hard.")],
 7: [(False,"Leader: Long before the news ever reached Galveston, freedom was already true. God’s “yes” had already been spoken.\n\n"),
     (True, "People: We come believing that liberation delayed is still liberation promised — and ours to carry.")],
 10:[(False,"Leader: God is already moving toward the margins, calling every beloved and colorfully made child by name.\n\n"),
     (True, "People: May we go where God goes, and tell the ones still waiting that they are free.")],
 13:[(True, "All: We are God’s learning, loving, justice-seeking people. Let us worship — and then let us go and do better.")],
}

def esc(t):
    cp={0x2019:"\\'92",0x2018:"\\'91",0x201c:"\\'93",0x201d:"\\'94",0x2014:"\\'97",
        0x2013:"\\'96",0x00a0:"\\'a0",0x2026:"\\'85"}
    o=[]
    for ch in t:
        c=ord(ch)
        if ch=='\\':o.append('\\\\')
        elif ch=='{':o.append('\\{')
        elif ch=='}':o.append('\\}')
        elif ch=='\n':o.append('\\\n')          # RTF hard return (counts as 1 char)
        elif c<128:o.append(ch)
        else:o.append(cp.get(c,"\\u%d?"%c))
    return ''.join(o)

def build_rtf(segs, fs, title=False):
    if title:
        ft="{\\fonttbl\\f0\\fswiss\\fcharset0 Helvetica-Bold;}"
    else:
        ft="{\\fonttbl\\f0\\fnil\\fcharset0 HelveticaNeue-Bold;\\f1\\fnil\\fcharset0 HelveticaNeue;}"
    pre=("{\\rtf1\\ansi\\ansicpg1252\\cocoartf2870\n\\cocoatextscaling0\\cocoaplatform0"+ft+"\n"
         "{\\colortbl;\\red255\\green255\\blue255;\\red255\\green255\\blue255;}\n"
         "{\\*\\expandedcolortbl;;\\cssrgb\\c100000\\c100000\\c100000;}\n"
         "\\deftab1680\n\\pard\\pardeftab1680\\pardirnatural\\qc\\partightenfactor0\n\n")
    body=""
    for bold,text in segs:
        if title:
            body+="\\f0\\b\\fs%d \\cf2 "%fs+esc(text)
        else:
            body+=("\\f0\\b" if bold else "\\f1\\b0")+"\\fs%d \\cf2 "%fs+esc(text)
    return pre+body+"}"

raw=open(SRC,'rb').read()
root=pb.parse(raw)

# collect text containers in document order (each has fn=5 rtf + fn=3 attr)
conts=[]
def collect(fields):
    for f in fields:
        if f.wt==2 and f.msg is not None:
            rtf=[c for c in f.msg if c.fn==5 and c.wt==2 and c.msg is None and b'rtf1' in c.value]
            attr=[c for c in f.msg if c.fn==3 and c.msg is not None]
            if rtf and attr: conts.append((f,rtf[0],attr[0]))
            collect(f.msg)
collect(root)

def mark(chain):
    for a in chain: a.dirty=True

# need ancestor chains to mark dirty; rebuild with chains
chains={}
def collect2(fields, chain):
    for f in fields:
        if f.wt==2 and f.msg is not None:
            rtf=[c for c in f.msg if c.fn==5 and c.wt==2 and c.msg is None and b'rtf1' in c.value]
            attr=[c for c in f.msg if c.fn==3 and c.msg is not None]
            if rtf and attr: chains[id(f)]=chain+[f]
            collect2(f.msg, chain+[f])
collect2(root,[])

for idx,segs in slides.items():
    cont,rtf,attr=conts[idx]
    # default size from attr.fn=1 -> fn=2
    deff=[c for c in attr.msg if c.fn==1 and c.msg is not None]
    size=65.0
    if deff:
        sz=[c for c in deff[0].msg if c.fn==2]
        if sz: import struct; size=struct.unpack('<d',sz[0].value)[0]
    fs=int(round(size*2))
    title=(idx==0)
    # 1) RTF text
    rtf.value=build_rtf(segs,fs,title=title).encode('utf-8'); rtf.dirty=True
    # 2) regenerate runs (skip for title: whole-bold via default font)
    attr.msg=[c for c in attr.msg if c.fn!=13]   # drop old runs
    if not title:
        pos=0
        newruns=[]
        for bold,text in segs:
            end=pos+len(text)
            if bold:
                newruns.append(pb.make_run(pos,end,'HelveticaNeue-Bold',size,bold=True))
            pos=end
        # insert runs before trailing fn=15 if present, else append
        attr.msg += newruns
    attr.dirty=True
    mark(chains[id(cont)])

out=pb.encode(root)
open(OUT,'wb').write(out)
print('wrote',len(out),'bytes (orig',len(raw),')')

# ---- validate: re-parse, dump runs + plain text per slide ----
r2=pb.parse(open(OUT,'rb').read())
c2=[]
def col(fields):
    for f in fields:
        if f.wt==2 and f.msg is not None:
            rtf=[c for c in f.msg if c.fn==5 and c.wt==2 and c.msg is None and b'rtf1' in c.value]
            attr=[c for c in f.msg if c.fn==3 and c.msg is not None]
            if rtf and attr: c2.append((rtf[0],attr[0]))
            col(f.msg)
col(r2)
import re
def vis(rtf):
    s=re.sub(r'\{\\fonttbl.*?\}','',rtf,flags=re.S)
    s=re.sub(r'\{\\colortbl.*?\}','',s,flags=re.S)
    s=re.sub(r'\{\\\*\\expandedcolortbl.*?\}','',s,flags=re.S)
    s=s.replace('\\\n','\n')
    s=re.sub(r"\\'([0-9a-fA-F]{2})",lambda m:bytes([int(m.group(1),16)]).decode('cp1252'),s)
    s=re.sub(r'\\[a-zA-Z]+-?[0-9]*','',s).replace('{','').replace('}','').replace('\\','')
    return s.strip()
for idx in (0,4,7,10,13):
    rtf,attr=c2[idx]
    runs=[]
    for f in attr.msg:
        if f.fn==13:
            rng=[c for c in f.msg if c.fn==1][0]; st=0;en=None
            for c in rng.msg:
                if c.fn==1:st=c.value
                if c.fn==2:en=c.value
            fm=[c for c in f.msg if c.fn==12][0]
            nm=[c for c in fm.msg if c.fn==1][0].value.decode()
            runs.append((st,en,'B' if any(c.fn==8 for c in fm.msg) else '.'))
    p=vis(rtf.value.decode('latin-1'))
    print(f'\n[slide {idx}] len={len(p)} runs={runs}')
    print('  ',repr(p[:120]))
