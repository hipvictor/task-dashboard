"""Format an already-written Call to Worship doc into the CTW ProPresenter deck (flexible length).

FORMATTER, not author: the CTW text is written before the skill runs. This reads the doc,
pulls the Leader:/People: exchanges + closing All:, and rebuilds the deck to hold exactly the
needed number of slides — title + one slide per exchange — in correct DISPLAY order.

Deck model (reverse-engineered): a presentation's display order is the cue-group (top-level
fn=12): header fn=1 + repeated fn=2 ref entries, each fn=2 = {fn=1: <cue-uuid>}. The cues
themselves are top-level fn=13, each with uuid at /1/1 and 3 text boxes (box 0 = visible).
So we: keep the title cue, CLONE a content cue once per exchange (regenerating every uuid),
fill each, then rewrite both the fn=13 cue list and the fn=12 ref list. Any length works.

Usage: gen_ctw.py <ctw_doc.txt> --liturgist "<name>" --out <CALL TO WORSHIP-2.pro>
                   [--template <CALL TO WORSHIP-2.pro>]
"""
import sys, os, re, struct, argparse, importlib.util, uuid as _uuid

_HERE=os.path.dirname(__file__)
def _load(n):
    s=importlib.util.spec_from_file_location(n, os.path.join(_HERE,n+".py"))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pb=_load("pb")
DEFAULT_TPL=os.path.join(_HERE,"templates","standard","CALL TO WORSHIP-2.pro")
_UUIDB=re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

def _get(fs,fn):
    for x in fs:
        if x.fn==fn: return x

def parse_ctw(text):
    """-> list of content units, each a list of (bold,text) segments, in order."""
    strip=lambda s: s.strip().lstrip('*').rstrip('*').strip()
    units=[]; leader=None
    for raw in text.replace('\r','').split('\n'):
        s=strip(raw)
        if not s: continue
        low=s.lower()
        if low.startswith('leader'):
            leader=s
        elif low.startswith('people'):
            units.append([(False, leader+"\n\n"),(True, s)] if leader else [(True, s)]); leader=None
        elif low.startswith('all:'):
            units.append([(True, s)])
    return units

# ---- RTF builders (verbatim from the proven June-14 path) ----
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

def _cue_uuid(cue):                       # cue uuid = first uuid in the cue bytes (/1/1)
    return _UUIDB.search(cue.raw_full).group(0).decode()

def _clone_cue(cue):                      # deep copy with EVERY uuid regenerated (byte-level)
    seen={}
    def repl(mo):
        o=mo.group(0)
        if o not in seen: seen[o]=str(_uuid.uuid4()).upper().encode()
        return seen[o]
    return pb.parse(_UUIDB.sub(repl, cue.raw_full))[0]

def _fill_cue(cue, segs):                 # set the cue's first (visible) text box + bold runs
    hit=[]
    def w(fs, chain):
        if hit: return
        for f in fs:
            if f.wt==2 and f.msg is not None:
                rtf=[c for c in f.msg if c.fn==5 and c.wt==2 and c.msg is None and b'rtf1' in (c.value or b'')]
                attr=[c for c in f.msg if c.fn==3 and c.msg is not None]
                if rtf and attr: hit.append((rtf[0],attr[0],chain+[f])); return
                w(f.msg, chain+[f])
    w(cue.msg, [cue])
    rtf, attr, chain = hit[0]
    deff=[c for c in attr.msg if c.fn==1 and c.msg is not None]; size=65.0
    if deff:
        sz=[c for c in deff[0].msg if c.fn==2]
        if sz: size=struct.unpack('<d', sz[0].value)[0]
    fs=int(round(size*2)); title = segs[0][1].startswith("Call To Worship")
    rtf.value=build_rtf(segs, fs, title=title).encode('utf-8'); rtf.msg=None; rtf.dirty=True
    attr.msg=[c for c in attr.msg if c.fn!=13]
    if not title:
        pos=0
        for bold,text in segs:
            end=pos+len(text)
            if bold: attr.msg.append(pb.make_run(pos,end,'HelveticaNeue-Bold',size,bold=True))
            pos=end
    attr.dirty=True
    for a in chain: a.dirty=True

def generate(doc_text, liturgist, template=DEFAULT_TPL, out=None):
    units=parse_ctw(doc_text)
    if not units:
        raise ValueError("CTW doc has no Leader/People/All exchanges — check the doc / format")
    title_segs=[(True, "Call To Worship"+(f"\n{liturgist}" if liturgist else ""))]

    root=pb.parse(open(template,'rb').read())
    group=_get(root,12)
    order=[_get(r.msg,1).value.decode() for r in group.msg
           if r.fn==2 and _get(r.msg,1) and _get(r.msg,1).msg is None]
    cues={_cue_uuid(c): c for c in root if c.fn==13}
    ordered=[cues[u] for u in order if u in cues]
    title_cue=ordered[0]
    content_tpl=next(c for c in ordered[1:] if c is not title_cue)   # a content cue to clone

    _fill_cue(title_cue, title_segs)
    clones=[]
    for u in units:
        c=_clone_cue(content_tpl); _fill_cue(c, u); clones.append(c)

    new_cues=[title_cue]+clones
    new_order=[_cue_uuid(title_cue)]+[_cue_uuid(c) for c in clones]
    group.msg=[x for x in group.msg if x.fn==1] + \
              [pb.mfield(2,[pb.sfield(1,u)]) for u in new_order]
    group.dirty=True

    newroot=[]; placed=False
    for f in root:
        if f.fn==13:
            if not placed: newroot.extend(new_cues); placed=True
        else:
            newroot.append(f)
    data=pb.encode(newroot)
    _validate(data, len(units))
    if out: open(out,'wb').write(data)
    return data, len(units)

_UUIDS=re.compile(r'^[0-9A-Fa-f-]{36}$')
def _validate(data, n_units):
    """Fail the build if the CTW surgery left the deck inconsistent."""
    assert pb.encode(pb.parse(data))==data, "CTW not round-trip stable"
    root=pb.parse(data)
    uu=[_cue_uuid(c) for c in root if c.fn==13]
    assert all(_UUIDS.match(u) for u in uu), "non-canonical cue uuid"
    assert len(uu)==len(set(uu)), "duplicate cue uuid"
    cueset=set(uu)
    group=_get(root,12)
    refs=[_UUIDB.search(r.raw_full).group(0).decode() for r in group.msg if r.fn==2]
    dangling=[u for u in refs if u not in cueset]
    assert not dangling, f"cue-group refs with no cue: {dangling}"
    assert len(refs)==n_units+1, f"group has {len(refs)} refs, expected title+{n_units}"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("doc"); ap.add_argument("--liturgist", default="")
    ap.add_argument("--template", default=DEFAULT_TPL); ap.add_argument("--out", required=True)
    a=ap.parse_args()
    _, n = generate(open(a.doc, encoding='utf-8').read(), a.liturgist, a.template, a.out)
    print(f"wrote {a.out}: title + {n} content slide(s)  (liturgist={a.liturgist!r})")
