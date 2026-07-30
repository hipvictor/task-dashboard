"""Format provided hymn lyrics into a ProPresenter hymn deck (for hymns not in the library).

FORMATTER, not author: verses are provided (a hymnal's published text). Rather than synthesize
slides (risky uuid surgery), this takes a donor library hymn deck and re-texts it: fill the
title slide + one slide per verse from existing slide-groups, then DROP the unused verse groups
(and their cues). No uuid regeneration — every kept slide keeps its own canonical uuid, so the
group->cue links and arrangement stay intact. Requires: #verses <= donor's verse-slide count.

CANONICAL HYMN SPEC — see `.claude/skills/worship-playlist/CONVENTIONS.md` ("Hymn slide spec"):
  · 4 lyric lines per slide (split longer stanzas into 4+4 half-stanzas).
  · Verse layout (lower third): Helvetica Bold 55pt (\\fs110); black bar h370 @ 75% opacity;
    text box 1620x325 at x150,y732.7, centered. (Geometry inherited from donor; font forced 55pt.)
  · 3-line title slide: Title / hymnal+number / hymnal color (UMH=Blue, TFWS=Black, W&S=Green).
  · Rename presentation field-3 to the hymn title so no donor metadata leaks in.
When #slides exceeds the donor's group count (e.g. a 4-verse hymn split 4+4 = 8+title), clone a
donor (group,cue) pair per slide with all uuids regenerated (keeping each group->cue ref linked),
as in the "Called as Partners in Christ's Service" build.

Hymn-deck model (reverse-engineered): display order = the sequence of top-level fn=12 groups;
each group has a header (fn=1, name at /1/2) + an fn=2 ref carrying its cue's uuid; the cues are
top-level fn=13. The arrangement (fn=17/18) does not reference cue/group uuids.

Input file: title block, blank line, then verses separated by blank lines. Example:
    Where Charity and Love Prevail
    United Methodist Hymnal #549

    Where charity and love prevail,
    there God is ever found; ...

Usage: gen_hymn.py <lyrics.txt> --out "<549 - ....pro>" [--template <donor hymn .pro>]
"""
import sys, os, re, argparse, importlib.util

_HERE=os.path.dirname(__file__)
def _load(n):
    s=importlib.util.spec_from_file_location(n, os.path.join(_HERE,n+".py"))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pb=_load("pb"); gc=_load("gen_ctw")
DEFAULT_TPL=os.path.join(_HERE,"templates","communion","3179 - The Risen Christ.pro")
_UUID=re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

def parse_lyrics(text):
    blocks=[b.strip("\n") for b in re.split(r'\n[ \t]*\n', text.replace('\r','')) if b.strip()]
    if len(blocks)<2: raise ValueError("need a title block, a blank line, then >=1 verse block")
    return blocks[0].strip(), blocks[1:]

def _gname(g):
    h=gc._get(g.msg,1)
    if h and h.msg:
        n=gc._get(h.msg,2)
        if n and n.value: return n.value.decode('latin1')
    return ""
def _gref(g):                       # cue uuid this group points at (its fn=2 ref)
    r=gc._get(g.msg,2)
    m=_UUID.search(r.raw_full) if r else None
    return m.group(0).decode() if m else None

def generate(title, verses, template=DEFAULT_TPL, out=None):
    root=pb.parse(open(template,'rb').read())
    groups=[f for f in root if f.fn==12]
    cues  ={gc._cue_uuid(c): c for c in root if c.fn==13}
    title_group=groups[0]
    verse_groups=[g for g in groups[1:] if _gname(g).lower().startswith("verse")]
    other_groups=[g for g in groups[1:] if not _gname(g).lower().startswith("verse")]
    if len(verses)>len(verse_groups):
        raise ValueError(f"donor has {len(verse_groups)} verse slides, need {len(verses)} — "
                         f"pick a donor with more verses")

    gc._fill_cue(cues[_gref(title_group)], [(True, title)])   # title slide
    used=[title_group]
    for i,v in enumerate(verses):
        g=verse_groups[i]; gc._fill_cue(cues[_gref(g)], [(True, v)]); used.append(g)
    used+=other_groups                                        # keep Blank etc.
    drop_groups=[g for g in verse_groups[len(verses):]]
    keep_refs={_gref(g) for g in groups if g not in drop_groups}
    # preserve original top-level order, minus dropped groups and their cues
    keep_groups=[g for g in groups if g not in drop_groups]
    keep_cues=[c for u,c in cues.items() if u in keep_refs]
    kc_by_u={gc._cue_uuid(c):c for c in keep_cues}
    ordered_cues=[kc_by_u[_gref(g)] for g in keep_groups if _gref(g) in kc_by_u]

    newroot=[]; gput=cput=False
    for f in root:
        if f.fn==12:
            if not gput: newroot.extend(keep_groups); gput=True
        elif f.fn==13:
            if not cput: newroot.extend(ordered_cues); cput=True
        else:
            newroot.append(f)
    data=pb.encode(newroot)
    _validate(data)
    if out: open(out,'wb').write(data)
    return data, len(verses)

def _validate(data):
    assert pb.encode(pb.parse(data))==data, "hymn deck not round-trip stable"
    root=pb.parse(data)
    groups=[f for f in root if f.fn==12]; cues=[f for f in root if f.fn==13]
    cu=[gc._cue_uuid(c) for c in cues]
    assert len(cu)==len(set(cu)), "duplicate cue uuid"
    cueset=set(cu)
    for g in groups:
        assert _gref(g) in cueset, f"group {_gname(g)!r} refs missing cue {_gref(g)}"
    assert len(groups)==len(cues), f"{len(groups)} groups vs {len(cues)} cues"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("lyrics"); ap.add_argument("--template", default=DEFAULT_TPL)
    ap.add_argument("--out", required=True)
    a=ap.parse_args()
    title, verses = parse_lyrics(open(a.lyrics, encoding='utf-8').read())
    _, n = generate(title, verses, a.template, a.out)
    print(f"wrote {a.out}: title + {n} verse slide(s)  (title={title!r})")
