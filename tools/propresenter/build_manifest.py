"""Build a ProPresenter playlist `data` manifest from a service spec.

Validated structurally (parses, unique UUIDs, correct library paths). Clones item
templates from a real manifest, so the exact binary structure matches what ProPresenter
writes. See docs/propresenter-playlist-workflow.md sections 7-9.

Spec format: list of ("GROUP", name, None) | ("PRES", name, "Libraries/.../x.pro").
Still TODO: fetch the matched .pro files into the zip; hook/sermon placeholders;
spreadsheet -> spec mapping + library fuzzy-match.
"""
import uuid, re
import pb  # local codec

HOME_PREFIX = "file:///Users/jonathan/Documents/ProPresenter/"

def _uuid_leaf(item):
    out=[]
    def w(fs):
        for c in fs:
            if c.wt==2 and c.msg is not None: w(c.msg)
            elif c.wt==2 and c.msg is None and len(c.value)==36 and c.value.count(b'-')==4:
                out.append(c)
    node = pb.get(item.msg,1)
    w(node.msg if node else item.msg)
    return out[0] if out else None

def _new_uuid(): return str(uuid.uuid4()).upper()

def make_group(tmpl_group, name):
    g=pb.clone(tmpl_group)
    pb.set_str_leaf(_uuid_leaf(g), _new_uuid())
    pb.set_str_leaf(pb.get(g.msg,2), name)
    pb.mark_all_dirty(g); return g

def make_pres(tmpl_pres, name, relpath):
    g=pb.clone(tmpl_pres)
    pb.set_str_leaf(_uuid_leaf(g), _new_uuid())
    pb.set_str_leaf(pb.get(g.msg,2), name)
    def fix(fs):
        for c in fs:
            if c.wt==2 and c.msg is not None: fix(c.msg)
            elif c.wt==2 and c.msg is None:
                if c.value.startswith(b'Libraries/'): pb.set_str_leaf(c, relpath)
                elif c.value.startswith(b'file://'):  pb.set_str_leaf(c, HOME_PREFIX+relpath)
    fix(pb.get(g.msg,4).msg)
    pb.mark_all_dirty(g); return g

def build(template_data: bytes, playlist_name: str, spec) -> bytes:
    """spec: list of ('GROUP', name, None) | ('PRES', name, relpath)."""
    root=pb.parse(template_data)
    fn3=pb.get(root,3); fn12=pb.get(fn3.msg,12); pl=pb.get(fn12.msg,1); fn13=pb.get(pl.msg,13)
    items=[c for c in fn13.msg if c.fn==1]; meta=[c for c in fn13.msg if c.fn!=1]
    tmpl_group=[it for it in items if not any(c.fn in (4,5) for c in it.msg)
                and pb.get(it.msg,2) and pb.get(it.msg,2).msg is None][0]
    tmpl_pres =[it for it in items if any(c.fn==4 for c in it.msg)][0]
    newitems=[]
    for kind,name,path in spec:
        newitems.append(make_group(tmpl_group,name) if kind=='GROUP' else make_pres(tmpl_pres,name,path))
    fn13.msg=[pb.clone(m) for m in meta]+newitems
    for x in (fn13,pl,fn12,fn3): x.dirty=True
    pb.set_str_leaf(pb.get(pl.msg,2), playlist_name)
    return pb.encode(root)
