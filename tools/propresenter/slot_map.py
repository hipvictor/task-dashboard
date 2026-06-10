"""Classify each template item as a SWAP slot or FIXED, by library category + cue anchor.

Verified against both real templates (Standard + Communion). Swap slots:
  A person  (under 'In-Person Welcome')        - currently L3 - JONATHAN PERRY
  B person  (under 'Prelude & Call To Worship') - currently L3 - GUEST-PIANO / Ashton Landry
  C CTW     (CALL TO WORSHIP-2)                 - regenerate weekly from the CTW doc
  D song    (under 'Hymn #1')                   - opening hymn
  E person  (under 'Invitation')                - liturgist / invitation
  F song    (under 'Hymn #2')                   - closing hymn
Special music is an 'L3 - Song Title' title-card slot, not a hymn-file slot.
"""
import importlib.util, os
_spec=importlib.util.spec_from_file_location("pb", os.path.join(os.path.dirname(__file__),"pb.py"))
pb=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pb)

ROLE_FIXED={'L3 - WORSHIP GUIDE','L3 - WORSHIP APP CHECK IN','L3 - GO IN PEACE',
            "L3 - Children's Time",'L3 - Song Title'}

def _f(fs,fn):
    for x in fs:
        if x.fn==fn: return x
def _all(fs,fn): return [x for x in fs if x.fn==fn]
def _s(fld):
    try: return fld.value.decode('utf-8')
    except: return None
def _ref(fs):
    for x in fs:
        if x.wt==2 and x.msg:
            r=_ref(x.msg)
            if r: return r
        elif x.wt==2:
            v=_s(x)
            if v and v.startswith('Libraries/') and v.endswith('.pro'): return v

def items(path):
    """Ordered [(name, ref_or_None)] for every item/cue in the playlist."""
    root=pb.parse(open(path,'rb').read())
    node=_f(_f(_f(root,3).msg,12).msg,1)
    out=[]
    for c in _all(_f(node.msg,13).msg,1):
        if not c.msg: continue
        nf=_f(c.msg,2)
        out.append((_s(nf) if nf else None, _ref(c.msg)))
    return out

def classify(name, ref):
    """-> (klass, action). klass in {'cue','fixed','swap'}."""
    if not ref: return ('cue','production note, kept')
    base=ref.split('/')[-1][:-4]; cat=ref.split('/')[1]
    if base=='CALL TO WORSHIP-2': return ('swap','Call to Worship → regenerate')
    if cat=='Hymns & Songs':      return ('swap','Song → match hymn #/title')
    if cat=='Name Lower Thirds':
        if base in ROLE_FIXED:        return ('fixed','generic role label')
        if base.startswith('L3 - '): return ('swap','Person → match name→L3')
    return ('fixed','template owns')

if __name__=='__main__':
    import sys
    for i,(n,r) in enumerate(items(sys.argv[1]),1):
        k,a=classify(n,r)
        print(f"{'>' if k=='swap' else ' '}{i:>2} [{k:<5}] {(n or '(unnamed)')[:34]:<34} {a}")
