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
# donor's title slide placeholders (3152 - Welcome), replaced with this hymn's three lines
_PH_TITLE=b"Welcome"; _PH_HYMNAL=b"Worship & Song #3152"; _PH_COLOR=b"Green Hymnal"
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

def _clone_pair(group,cue,name):
    """Deep-copy a (group,cue) pair with every uuid regenerated consistently (ref stays linked)."""
    seen={}
    def repl(m):
        k=m.group(0)
        if k not in seen: seen[k]=str(_uuid.uuid4()).upper().encode()
        return seen[k]
    c2=pb.parse(_UUIDB.sub(repl,cue.raw_full))[0]
    g2=pb.parse(_UUIDB.sub(repl,group.raw_full))[0]
    _set_gname(g2,name)
    return g2,c2

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

def _sub_title(cue, title, hymnal_line, color):
    """Replace the donor title's 3 placeholder lines in place (preserves the title's format)."""
    hit=[False]
    def walk(fs,anc):
        for f in fs:
            v=f.value if isinstance(f.value,(bytes,bytearray)) else None
            if v and _PH_COLOR in v:              # the title RTF may be misparsed -> collapse+replace
                nv=v.replace(_PH_HYMNAL, hymnal_line.encode()).replace(_PH_COLOR, color.encode())
                nv=nv.replace(_PH_TITLE, title.encode())
                f.value=nv; f.msg=None; f.dirty=True
                for a in anc: a.dirty=True;
                hit[0]=True
            elif f.msg is not None: walk(f.msg,anc+[f])
    walk(cue.msg,[cue])
    if not hit[0]: raise RuntimeError("title placeholder not found — donor changed?")

def generate(title, code, num, verses, out=None):
    hymnal_name,color=HYMNALS[code]; hymnal_line=f"{hymnal_name} #{num}"
    slides=split_slides(verses)
    if not slides: raise ValueError("no verses")
    root=pb.parse(open(DONOR,'rb').read())
    groups=[x for x in root if x.fn==12]; cues=[x for x in root if x.fn==13]
    cby={_UUIDB.search(c.raw_full).group(0).decode():c for c in cues}
    title_g=next(g for g in groups if _gname(g)=="Intro"); title_c=cby[_gref(title_g)]
    verse_g=next(g for g in groups if _gname(g)=="Verse 2"); verse_c=cby[_gref(verse_g)]

    _sub_title(title_c, title, hymnal_line, color); _set_gname(title_g,"Title")
    new_groups=[title_g]; new_cues=[title_c]
    for name,text in slides:
        g2,c2=_clone_pair(verse_g,verse_c,name); _fill_verse(c2,text)
        new_groups.append(g2); new_cues.append(c2)

    newroot=[]; gput=cput=False
    for f in root:
        if f.fn==12:
            if not gput: newroot+=new_groups; gput=True
        elif f.fn==13:
            if not cput: newroot+=new_cues; cput=True
        else: newroot.append(f)
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
    for g in groups:
        assert _gref(g) in set(cu), f"group {_gname(g)!r} refs missing cue"
    assert len(groups)==len(cues), f"{len(groups)} groups vs {len(cues)} cues"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("lyrics"); ap.add_argument("--out", required=True)
    a=ap.parse_args()
    title, code, num, verses = parse_input(open(a.lyrics, encoding='utf-8').read())
    _, n, name = generate(title, code, num, verses, a.out)
    print(f"wrote {a.out}: title + {n} lyric slide(s)  ({name!r})")
