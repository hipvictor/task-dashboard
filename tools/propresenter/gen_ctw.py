"""Format an already-written Call to Worship doc into the CTW ProPresenter deck.

This is a FORMATTER, not an author: the CTW text is written by humans before the skill runs.
It reads the week's CTW doc text, pulls the Leader:/People: responsive exchanges and the
closing All:, and lays them into `CALL TO WORSHIP-2.pro` (title slide = "Call To Worship" +
the liturgist from col 12; scripture/theme/rubric stay doc-only).

Deck capacity: the template CTW has a title slide + 4 content slots (visible text containers
0,4,7,10,13). Content units (each Leader/People pair, plus the All line) fill 4,7,10,13 in
order; unused slots are blanked. If a doc needs MORE than 4 content slides this raises — that
overflow week is flagged for review (dynamic slide add/remove is the planned next step).

Usage: gen_ctw.py <ctw_doc.txt> --liturgist "<name>" --out <CALL TO WORSHIP-2.pro>
                   [--template <CALL TO WORSHIP-2.pro>]
Get the doc text with the Drive connector's read_file_content; save it to a .txt first.
"""
import sys, os, re, struct, argparse, importlib.util

_HERE=os.path.dirname(__file__)
def _load(n):
    s=importlib.util.spec_from_file_location(n, os.path.join(_HERE,n+".py"))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pb=_load("pb")
DEFAULT_TPL=os.path.join(_HERE,"templates","standard","CALL TO WORSHIP-2.pro")
SLOTS=[4,7,10,13]                      # content-slide container indices (title is 0)

def parse_ctw(text):
    """-> list of content units, each a list of (bold, text) segments, in order."""
    strip=lambda s: s.strip().lstrip('*').rstrip('*').strip()
    units=[]; leader=None
    for raw in text.replace('\r','').split('\n'):
        s=strip(raw)
        if not s: continue
        low=s.lower()
        if low.startswith('leader'):          # "Leader:" / "Leaders:"
            leader=s
        elif low.startswith('people'):
            seg=[(False, leader+"\n\n"),(True, s)] if leader else [(True, s)]
            units.append(seg); leader=None
        elif low.startswith('all:'):
            units.append([(True, s)])
    return units

# ---- RTF builders (verbatim from the proven June-14 POC) ----
def esc(t):
    cp={0x2019:"\\'92",0x2018:"\\'91",0x201c:"\\'93",0x201d:"\\'94",0x2014:"\\'97",
        0x2013:"\\'96",0x00a0:"\\'a0",0x2026:"\\'85"}
    o=[]
    for ch in t:
        c=ord(ch)
        if ch=='\\':o.append('\\\\')
        elif ch=='{':o.append('\\{')
        elif ch=='}':o.append('\\}')
        elif ch=='\n':o.append('\\\n')
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
        if title: body+="\\f0\\b\\fs%d \\cf2 "%fs+esc(text)
        else:     body+=("\\f0\\b" if bold else "\\f1\\b0")+"\\fs%d \\cf2 "%fs+esc(text)
    return pre+body+"}"

def generate(doc_text, liturgist, template=DEFAULT_TPL, out=None):
    units=parse_ctw(doc_text)
    if not units:
        raise ValueError("CTW doc has no Leader/People/All exchanges — check the doc / format")
    if len(units) > len(SLOTS):
        raise ValueError(f"CTW doc needs {len(units)} content slides but the deck holds "
                         f"{len(SLOTS)} — FLAG: dynamic slide add not yet built")
    title_txt="Call To Worship"+(f"\n{liturgist}" if liturgist else "")
    slides={0:[(True, title_txt)]}
    for i,u in enumerate(units): slides[SLOTS[i]]=u
    for j in range(len(units), len(SLOTS)): slides[SLOTS[j]]=[(False,"")]   # blank unused

    root=pb.parse(open(template,'rb').read())
    conts=[]; chains={}
    def collect(fields, chain):
        for f in fields:
            if f.wt==2 and f.msg is not None:
                rtf=[c for c in f.msg if c.fn==5 and c.wt==2 and c.msg is None and b'rtf1' in (c.value or b'')]
                attr=[c for c in f.msg if c.fn==3 and c.msg is not None]
                if rtf and attr: conts.append((f,rtf[0],attr[0])); chains[id(f)]=chain+[f]
                collect(f.msg, chain+[f])
    collect(root, [])
    for idx,segs in slides.items():
        cont,rtf,attr=conts[idx]
        deff=[c for c in attr.msg if c.fn==1 and c.msg is not None]
        size=65.0
        if deff:
            sz=[c for c in deff[0].msg if c.fn==2]
            if sz: size=struct.unpack('<d',sz[0].value)[0]
        fs=int(round(size*2)); title=(idx==0)
        rtf.value=build_rtf(segs,fs,title=title).encode('utf-8'); rtf.msg=None; rtf.dirty=True
        attr.msg=[c for c in attr.msg if c.fn!=13]            # drop old bold runs
        if not title:
            pos=0
            for bold,text in segs:
                end=pos+len(text)
                if bold: attr.msg.append(pb.make_run(pos,end,'HelveticaNeue-Bold',size,bold=True))
                pos=end
        attr.dirty=True
        for a in chains[id(cont)]: a.dirty=True
    data=pb.encode(root)
    if out: open(out,'wb').write(data)
    return data, len(units)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("doc"); ap.add_argument("--liturgist", default="")
    ap.add_argument("--template", default=DEFAULT_TPL); ap.add_argument("--out", required=True)
    a=ap.parse_args()
    _, n = generate(open(a.doc, encoding='utf-8').read(), a.liturgist, a.template, a.out)
    print(f"wrote {a.out}: {n} content slide(s) + title (liturgist={a.liturgist!r})")
