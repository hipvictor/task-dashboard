"""Build one Sunday's importable .proplaylist by swapping a template.

Strategy (template-swap): start from the chosen template's extracted files (which already
bundle every FIXED .pro + media), then for the target date:
  - swap the matched .pro into each variable slot (opening/closing hymn, the 3 person L3s),
  - overwrite the Call to Worship .pro with the regenerated one,
  - retitle the playlist to the service date,
  - re-zip as a stored .proplaylist.
Only path-based refs are rewritten per item: display name (/2), absolute file:// URL
(/4/1/1), relative library path (/4/1/4/2). Unchanged protobuf round-trips from raw bytes.

Slots are assigned positionally among the template's swap items (verified A,B,E person order
+ opening,closing song order). A slot whose matched file == the template's current file, or
whose value has no confident match, is left as the template default (and reported).

Library .pro files for swapped-in items must be present in <swapcache> (fetch from the Drive
mirror of ~/Documents/ProPresenter/Libraries).  CTW .pro path passed via --ctw.
"""
import csv, sys, os, re as _re, uuid as _uuid, importlib.util, argparse

_HERE=os.path.dirname(__file__)
def _load(n):
    s=importlib.util.spec_from_file_location(n, os.path.join(_HERE,n+".py"))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pb=_load("pb"); ml=_load("match_library"); sm=_load("slot_map"); ppzip=_load("ppzip")
INV=__import__("json").load(open(os.path.join(_HERE,"data","library_inventory.json")))
HYMNS,L3S=INV["hymns"],INV["l3s"]

ABS_PREFIX="file:///Users/avmac/Documents/ProPresenter/"
def abs_url(rel):  return ABS_PREFIX+rel.replace(" ","%20")   # only spaces are %-encoded

def _get(fs,fn):
    for x in fs:
        if x.fn==fn: return x
def _getm(fs,fn):
    x=_get(fs,fn); return x.msg if x else None
# NOTE: never mark-all-dirty + re-encode — some UUID strings are binary that coincidentally
# parses as protobuf, and rebuilding them corrupts the bytes. Mark ONLY edited fields + the
# ancestor chain dirty; everything else emits its original raw bytes (byte-faithful).
def _setf(field,s):
    field.value=s.encode("utf-8"); field.msg=None; field.dirty=True

def rewrite_item(child, new_basename):
    """Point an item (Field) at a new .pro filename, keeping its library folder. Returns old basename."""
    cm=child.msg
    f4=_get(cm,4); f41=_get(f4.msg,1); f414=_get(f41.msg,4)
    rel_f=_get(f414.msg,2); rel=rel_f.value.decode()
    folder="/".join(rel.split("/")[:-1])           # Libraries/<cat>
    old_base=rel.split("/")[-1]
    new_rel=folder+"/"+new_basename
    _setf(rel_f, new_rel)                # relative path  /4/1/4/2
    _setf(_get(f41.msg,1), abs_url(new_rel))   # absolute url   /4/1/1
    _setf(_get(cm,2), new_basename[:-4])       # display name   /2
    for fld in (child,f4,f41,f414):     # dirty the container chain so encode recurses
        fld.dirty=True
    return old_base

# ---- item cloning / insertion (for the Community Prayer sequence) ----
def _ref_is(c, suffix):
    r=sm._ref(c.msg); return bool(r) and r.endswith(suffix)
def _clone(field):
    return pb.parse(field.raw_full)[0]            # independent deep copy via re-parse
def _fresh_uuid(item):
    """Give a cloned item a brand-new cue UUID. The real structure is item/1/1 = a 36-char
    UUID string; a lenient parse can mis-split that string into phantom sub-fields, so set
    the string value directly (msg=None) rather than editing inside the misparse."""
    A=_get(item.msg,1)          # uuid wrapper message  (/1)
    U=_get(A.msg,1)             # uuid string field      (/1/1)
    U.value=str(_uuid.uuid4()).upper().encode(); U.msg=None; U.dirty=True
    A.dirty=True; item.dirty=True
def insert_community_prayer(a13, children, leader_basename, report):
    """Replace the Baptismal Liturgy item with: blank · leader L3 · Lord's Prayer · blank."""
    bap=next((c for c in children if _ref_is(c,"Baptismal Liturgy.pro")), None)
    if bap is None:
        report.append("  · Community Prayer: no Baptismal Liturgy item, skipped"); return None
    wb=next(c for c in children if _ref_is(c,"Worship Blank.pro"))   # /4/1/2 ref shape
    jp=next(c for c in children if _ref_is(c,"L3 - JONATHAN PERRY.pro"))  # /4/1/1 ref shape
    b1=_clone(wb); _fresh_uuid(b1)
    l3=_clone(jp); rewrite_item(l3, leader_basename); _fresh_uuid(l3)
    lp=_clone(bap); rewrite_item(lp, "Lord's Prayer.pro"); _fresh_uuid(lp)
    b2=_clone(wb); _fresh_uuid(b2)
    i=a13.msg.index(bap); a13.msg[i:i+1]=[b1,l3,lp,b2]
    report.append(f"  ✓ Community Prayer: Baptismal Liturgy → blank · {leader_basename[:-4]} · Lord's Prayer · blank")
    return ("Baptismal Liturgy.pro", [leader_basename, "Lord's Prayer.pro"])

_UUIDRE=_re.compile(rb'^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$')

def _rtf_esc(t):
    cp={0x2019:"\\'92",0x2018:"\\'91",0x201c:"\\'93",0x201d:"\\'94",0x2014:"\\'97",
        0x2013:"\\'96",0x2026:"\\'85"}
    o=[]
    for ch in t:
        c=ord(ch)
        if ch=='\\': o.append('\\\\')
        elif ch in '{}': o.append('\\'+ch)
        elif c<128: o.append(ch)
        else: o.append(cp.get(c,"\\u%d?"%c))
    return ''.join(o).encode()

def song_title_card(src_bytes, title):
    """Return L3 - Song Title .pro bytes with the quoted song title replaced. The card has no
    character-range runs (pure-RTF formatting), so a substring swap is safe."""
    root=pb.parse(src_bytes); target=None
    def walk(fs,chain):
        nonlocal target
        for f in fs:
            if f.wt==2 and f.msg is None and b'rtf1' in (f.value or b'') and b"\\'93" in f.value:
                target=chain+[f]
            elif f.wt==2 and f.msg is not None: walk(f.msg,chain+[f])
    walk(root,[])
    if not target: return src_bytes
    rtf=target[-1]; esc=_rtf_esc(title)
    rtf.value=_re.sub(rb"\\'93.*?\\'94", lambda m: b"\\'93"+esc+b"\\'94", rtf.value, count=1, flags=_re.S)
    rtf.msg=None
    for f in target: f.dirty=True
    return pb.encode(root)

def _validate(data_bytes, bundled):
    """Fail loudly if the manifest would not deserialize cleanly: every item must carry a
    canonical cue UUID (item/1/1 = 0a26 0a24 <36-char>) and every ref must be bundled.
    Guards against the lenient-parser misparse that corrupted cloned-item UUIDs."""
    root=pb.parse(data_bytes)
    a1=_get(_get(_get(root,3).msg,12).msg,1)
    items=[c for c in _get(a1.msg,13).msg if c.fn==1 and c.msg]
    for k,c in enumerate(items,1):
        raw=_get(c.msg,1).raw_full
        assert len(raw)==40 and raw[0]==0x0a and raw[2:4]==b'\x0a\x24' and _UUIDRE.match(raw[4:40]), \
            f"item {k}: non-canonical cue UUID ({raw[:8].hex()})"
        r=sm._ref(c.msg)
        assert (not r) or r.split('/')[-1] in bundled, f"item {k}: dangling ref {r}"
    return len(items)

def build(template_dir, csv_path, date, ctw_pro, swapcache, out_path, baptism=False):
    rows=list(csv.reader(open(csv_path,newline="")))
    row=next((r for r in rows[1:] if len(r)>1 and r[1].strip().lower()==date.strip().lower()),None)
    assert row, f"no row for {date!r}"
    g=lambda i: row[i].strip() if len(row)>i else ""
    # matched targets (None -> keep template default)
    open_h = ml.match_hymn(g(15),HYMNS) if g(15) else None
    close_h= ml.match_hymn(g(30),HYMNS) if g(30) else None
    pers   = [ml.match_person(g(8),L3S) if g(8) else None,    # A welcome
              ml.match_person(g(10),L3S) if g(10) else None,  # B accompanist
              ml.match_person(g(28),L3S) if g(28) else None]  # E invitation

    data_path=os.path.join(template_dir,"data")
    root=pb.parse(open(data_path,"rb").read())
    a3=_get(root,3); a12=_get(a3.msg,12); a1=_get(a12.msg,1); a13=_get(a1.msg,13)
    node=a1.msg
    children=[c for c in a13.msg if c.fn==1 and c.msg]

    # collect swap items in document order, bucketed
    songs=[]; persons=[]; ctw=None
    for c in children:
        nf=_get(c.msg,2); name=nf.value.decode() if nf else None
        ref=sm._ref(c.msg)
        if not ref: continue
        klass,_=sm.classify(name,ref)
        if klass!="swap": continue
        base=ref.split("/")[-1][:-4]
        if base=="CALL TO WORSHIP-2": ctw=c
        elif ref.split("/")[1]=="Hymns & Songs": songs.append(c)
        else: persons.append(c)

    removed=set(); added=[]; report=[]
    def do_swap(child, target_basename, label):
        if not target_basename:
            report.append(f"  · {label}: no match → kept template default"); return
        cur=sm._ref(child.msg).split("/")[-1]
        if cur==target_basename:
            report.append(f"  · {label}: unchanged ({cur})"); return
        old=rewrite_item(child, target_basename)
        removed.add(old); added.append(target_basename)
        report.append(f"  ✓ {label}: {old}  →  {target_basename}")

    if len(songs)>=1: do_swap(songs[0], open_h and open_h, "Opening hymn")
    if len(songs)>=2: do_swap(songs[-1], close_h and close_h, "Closing hymn")
    labels=["Welcome person","Accompanist","Invitation person"]
    for i,c in enumerate(persons[:3]):
        do_swap(c, pers[i], labels[i])
    # Community Prayer (typical Sunday): swap the special-case Baptismal Liturgy for the
    # standard blank · leader-L3 · Lord's Prayer · blank sequence (leader from col 24).
    if not baptism:
        cp=ml.match_person(g(24),L3S) if g(24) else None
        if cp:
            res=insert_community_prayer(a13, children, cp, report)
            if res: removed.add(res[0]); added.extend(res[1])
        else:
            report.append("  · Community Prayer: col-24 leader empty/no match, kept Baptismal Liturgy")

    # CTW: keep its path, just overwrite bundled .pro
    if ctw is not None:
        report.append("  ✓ Call to Worship: regenerated CALL TO WORSHIP-2.pro")

    # retitle playlist: /3/12/1/2
    _setf(_get(a1.msg,2), date)
    # dirty only the ancestor chain to title + edited children (children dirtied in rewrite_item)
    for fld in (a3,a12,a1,a13): fld.dirty=True
    new_data=pb.encode(root)

    # assemble bundle: flat .pro files + data (NO media tree), in ProPresenter's zip dialect
    present={fn:os.path.join(template_dir,fn) for fn in os.listdir(template_dir)
             if fn.endswith(".pro") and os.path.isfile(os.path.join(template_dir,fn))}
    for b in removed: present.pop(b, None)
    for b in added:
        src=os.path.join(swapcache,b); assert os.path.exists(src), f"missing swap file: {src}"
        present[b]=src
    present["CALL TO WORSHIP-2.pro"]=ctw_pro            # overwrite bundled CTW
    _validate(new_data, set(present))                  # schema guard before shipping
    # bytes for each entry (read files; CTW from its path)
    blobs={fn: open(p,"rb").read() for fn,p in present.items()}
    # special-music title card: set the quoted title from col 19 (Special Music/Anthem)
    if g(19) and "L3 - Song Title.pro" in blobs:
        title=g(19).split(" by ")[0].strip()           # title, drop "by <composer>"
        blobs["L3 - Song Title.pro"]=song_title_card(blobs["L3 - Song Title.pro"], title)
        report.append(f"  ✓ Special-music card: title → {title!r}")
    for fn,b in blobs.items():                          # truncation guard: a complete
        present_fns={f.fn for f in pb.parse(b)}          # presentation carries its arrangement
        assert 17 in present_fns and 18 in present_fns, \
            f"{fn} looks truncated/incomplete (missing arrangement fields 17/18) — re-download"
    entries=[(fn, blobs[fn]) for fn in sorted(blobs)]
    entries.append(("data", new_data))                 # data last, like real exports
    ppzip.write(out_path, entries)
    print(f"=== Built {out_path}  ({os.path.getsize(out_path)} bytes, {len(entries)} entries) ===")
    print("\n".join(report))
    return out_path

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--template",required=True); ap.add_argument("--csv",required=True)
    ap.add_argument("--date",required=True);     ap.add_argument("--ctw",required=True)
    ap.add_argument("--swapcache",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args()
    build(a.template,a.csv,a.date,a.ctw,a.swapcache,a.out)
