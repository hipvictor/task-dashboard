"""Format provided hymn lyrics into a ProPresenter hymn deck, built to the church spec.

FORMATTER, not author: verses are provided (a hymnal's published text). This clones a real
library hymn deck (`templates/hymn-donor.pro` = the church's 3152 - Welcome deck) so slide
geometry matches the church's actual slides, then re-texts it — one cloned (group, cue) pair
per slide with all uuids regenerated (each group->cue ref stays linked; the fn=17/18 arrangement
does not reference cue/group uuids, so it stays valid). Handles any slide count.

CANONICAL HYMN SPEC (also in .claude/skills/worship-playlist/CONVENTIONS.md):
  · 4 lyric lines per slide — a full 4-line stanza, or a longer stanza split into 4+4 halves.
  · Verse layout (inherited from the donor's lower-third slide): black bar h370 @ 75% opacity,
    text box 1620x325 @ x150/y732.7 centered; font FORCED to Helvetica Bold 55pt (\\fs110).
  · 3-line title slide: Title / hymnal+number / hymnal color.
  · Presentation name (field 3) set to "<number> - <Title>" so no donor metadata leaks in.

Input file: line 1 = hymn title; line 2 = "<HYMNAL> <number>" (UMH | TFWS | W&S); blank line;
then verses separated by blank lines. Example:
    Called as Partners in Christ's Service
    UMH 453

    Called as partners in Christ's service
    Called to ministries of grace
    ... (8 lines)

    Christ's example, Christ's inspiring
    ... (next verse)

Usage: gen_hymn.py <lyrics.txt> --out "<453 - Title.pro>"
"""
import sys, os, re, argparse, importlib.util, uuid as _uuid

_HERE=os.path.dirname(__file__)
def _load(n):
    s=importlib.util.spec_from_file_location(n, os.path.join(_HERE,n+".py"))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pb=_load("pb"); gc=_load("gen_ctw")
DONOR=os.path.join(_HERE,"templates","hymn-donor.pro")
_UUIDB=re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')
HYMNALS={  # code -> (line-2 hymnal name, line-3 color)
    "UMH":  ("The United Methodist Hymnal", "Blue Hymnal"),
    "TFWS": ("The Faith We Sing",           "Black Hymnal"),
    "W&S":  ("Worship & Song",              "Green Hymnal"),
}

def parse_input(text):
    blocks=[b.strip("\n") for b in re.split(r'\n[ \t]*\n', text.replace('\r','')) if b.strip()]
    if len(blocks)<2: raise ValueError("need: title line, hymnal line, blank line, then verses")
    head=[l.strip() for l in blocks[0].splitlines() if l.strip()]
    if len(head)<2: raise ValueError("first block must be: line1=title, line2='<HYMNAL> <number>'")
    title=head[0]
    m=re.match(r'(UMH|TFWS|W&S)\s+#?(\w+)', head[1], re.I)
    if not m: raise ValueError(f"hymnal line {head[1]!r} must be 'UMH 453' / 'TFWS 2130' / 'W&S 3152'")
    code=m.group(1).upper(); num=m.group(2)
    verses=[[l for l in blk.splitlines() if l.strip()] for blk in blocks[1:]]
    return title, code, num, verses

def split_slides(verses):
    """4 lines per slide; longer stanzas split into 4+4… half-stanzas."""
    out=[]
    for i,lines in enumerate(verses,1):
        chunks=[lines[j:j+4] for j in range(0,len(lines),4)]
        for k,ch in enumerate(chunks):
            label=f"Verse {i}" if k==0 else f"Verse {i} (cont.)"
            out.append((label,"\n".join(ch)))
    return out

def _gget(m,f):
    for c in m:
        if c.fn==f: return c
def _gname(g):
    h=_gget(g.msg,1); n=_gget(h.msg,2) if h and h.msg else None
    return n.value.decode('latin1') if n and n.value else ""
def _gref(g):
    r=_gget(g.msg,2); m=_UUIDB.search(r.raw_full) if r else None
    return m.group(0).decode() if m else None
def _set_gname(g,name):
    h=_gget(g.msg,1); n=_gget(h.msg,2); n.value=name.encode(); n.msg=None
    n.dirty=True; h.dirty=True; g.dirty=True

def _new_pres_uuid(root):
    """Give the presentation a fresh uuid (field 2) so it doesn't collide with the donor deck
    already in the library — a duplicate presentation uuid makes ProPresenter ignore the import."""
    f2=_gget(root,2)
    if f2 is None: return
    u=_gget(f2.msg,1)
    if u is not None:
        u.value=str(_uuid.uuid4()).upper().encode(); u.msg=None; u.dirty=True; f2.dirty=True

def _fill_verse(cue,text):
    """Fill the visible text box with the (≤4-line) stanza and FORCE 55pt (\\fs110)."""
    gc._fill_cue(cue,[(True,text)])
    def walk(fs):
        for f in fs:
            if f.msg is not None: walk(f.msg)
            elif isinstance(f.value,(bytes,bytearray)) and b'rtf1' in f.value and b'\\cf2' in f.value:
                nv=re.sub(rb"\\fs\d+", b"\\\\fs110", f.value)
                if nv!=f.value: f.value=nv; f.msg=None; f.dirty=True
    walk(cue.msg)

def generate(title, code, num, verses, out=None):
    hymnal_name,color=HYMNALS[code]; hymnal_line=f"{hymnal_name} #{num}"
    slides=split_slides(verses)
    if not slides: raise ValueError("no verses")
    root=pb.parse(open(DONOR,'rb').read())
    groups=[x for x in root if x.fn==12]; cues=[x for x in root if x.fn==13]
    cby={_UUIDB.search(c.raw_full).group(0).decode():c for c in cues}
    # ONE cueGroup holds every slide (like gen_ctw). Cloning GROUPS re-parses the cue-ref uuids,
    # which mis-split and corrupt on re-encode (SwiftProtobuf rejects the file) — so instead we
    # clone only CUES and rebuild the group's cue-ref list FRESH from uuid strings.
    the_group=next(g for g in groups if _gname(g)=="Intro")
    title_c=cby[_gref(the_group)]
    verse_c=cby[_gref(next(g for g in groups if _gname(g)=="Verse 2"))]

    # Fill the title via the PROVEN _fill_cue path (rebuilds the text box with correct framing).
    # A naive byte-replace here corrupts the enclosing message's length prefixes -> ProPresenter's
    # strict decoder rejects the file (binaryDecoding error 3).
    gc._fill_cue(title_c, [(True, f"{title}\n{hymnal_line}\n{color}")])
    new_cues=[title_c]; order=[gc._cue_uuid(title_c)]
    for _name,text in slides:
        c=gc._clone_cue(verse_c); _fill_verse(c,text)
        new_cues.append(c); order.append(gc._cue_uuid(c))
    the_group.msg=[x for x in the_group.msg if x.fn==1] + \
                  [pb.mfield(2,[pb.sfield(1,u)]) for u in order]
    the_group.dirty=True
    _set_gname(the_group, title)

    newroot=[]; gput=cput=False
    for f in root:
        if f.fn==12:
            if not gput: newroot.append(the_group); gput=True
        elif f.fn==13:
            if not cput: newroot+=new_cues; cput=True
        else: newroot.append(f)
    _new_pres_uuid(newroot)
    presname=f"{num} - {title}".encode()
    for f in newroot:
        if f.fn==3 and isinstance(f.value,(bytes,bytearray)):
            f.value=presname; f.msg=None; f.dirty=True
    data=pb.encode(newroot)
    _validate(data)
    if out: open(out,'wb').write(data)
    return data, len(slides), f"{num} - {title}"

def _validate(data):
    assert pb.encode(pb.parse(data))==data, "hymn deck not round-trip stable"
    root=pb.parse(data)
    groups=[x for x in root if x.fn==12]; cues=[x for x in root if x.fn==13]
    fns={f.fn for f in root}
    assert 17 in fns, "missing arrangement (fn17)"
    cu=[_UUIDB.search(c.raw_full).group(0).decode() for c in cues]
    assert len(cu)==len(set(cu)), "duplicate cue uuid"
    cueset=set(cu); refs=[]
    for g in groups:
        for r in g.msg:
            if r.fn==2:
                m=_UUIDB.search(r.raw_full)
                if m: refs.append(m.group(0).decode())
    assert refs, "group has no cue refs"
    assert not [r for r in refs if r not in cueset], "cue-group ref with no matching cue"
    assert len(refs)==len(cues), f"{len(refs)} refs vs {len(cues)} cues"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("lyrics"); ap.add_argument("--out", required=True)
    a=ap.parse_args()
    title, code, num, verses = parse_input(open(a.lyrics, encoding='utf-8').read())
    _, n, name = generate(title, code, num, verses, a.out)
    print(f"wrote {a.out}: title + {n} lyric slide(s)  ({name!r})")
