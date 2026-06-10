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
import csv, sys, os, shutil, zipfile, importlib.util, argparse

_HERE=os.path.dirname(__file__)
def _load(n):
    s=importlib.util.spec_from_file_location(n, os.path.join(_HERE,n+".py"))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pb=_load("pb"); ml=_load("match_library"); sm=_load("slot_map")
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

def build(template_dir, csv_path, date, ctw_pro, swapcache, out_path, communion=None):
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
    # CTW: keep its path, just overwrite bundled .pro
    if ctw is not None:
        report.append("  ✓ Call to Worship: regenerated CALL TO WORSHIP-2.pro")

    # retitle playlist: /3/12/1/2
    _setf(_get(a1.msg,2), date)
    # dirty only the ancestor chain to title + edited children (children dirtied in rewrite_item)
    for fld in (a3,a12,a1,a13): fld.dirty=True
    new_data=pb.encode(root)

    # assemble work dir
    work=out_path+".work"
    if os.path.exists(work): shutil.rmtree(work)
    shutil.copytree(template_dir, work, ignore=shutil.ignore_patterns("__MACOSX"))
    open(os.path.join(work,"data"),"wb").write(new_data)
    for b in removed:
        p=os.path.join(work,b)
        if os.path.exists(p): os.remove(p)
    for b in added:
        src=os.path.join(swapcache,b)
        assert os.path.exists(src), f"missing swap file: {src}"
        shutil.copy(src, os.path.join(work,b))
    shutil.copy(ctw_pro, os.path.join(work,"CALL TO WORSHIP-2.pro"))

    # zip (stored) -> .proplaylist
    if os.path.exists(out_path): os.remove(out_path)
    with zipfile.ZipFile(out_path,"w",zipfile.ZIP_STORED) as z:
        for dp,_,fns in os.walk(work):
            for fn in fns:
                full=os.path.join(dp,fn); arc=os.path.relpath(full,work)
                z.write(full,arc)
    shutil.rmtree(work)
    print(f"=== Built {out_path}  ({os.path.getsize(out_path)} bytes) ===")
    print("\n".join(report))
    return out_path

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--template",required=True); ap.add_argument("--csv",required=True)
    ap.add_argument("--date",required=True);     ap.add_argument("--ctw",required=True)
    ap.add_argument("--swapcache",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args()
    build(a.template,a.csv,a.date,a.ctw,a.swapcache,a.out)
