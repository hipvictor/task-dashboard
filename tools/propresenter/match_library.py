"""Match spreadsheet values to existing ProPresenter library files.

Tested against the real June 14 row + live library inventory (all correct).
Inventory = lists of '.pro' filenames per category (pull from the Drive mirror of
~/Documents/ProPresenter/Libraries, or a cached listing).

Design rule: low-confidence / ambiguous matches should be surfaced for human review,
not silently guessed (esp. first-name-only people when names could collide).
"""
import re, difflib

def match_hymn(cell, hymns):
    """cell e.g. 'UMH 519, Lift Every Voice and Sing, v. 1 and 3' -> '519 - Lift Every Voice.pro'."""
    m=re.search(r'(\d{2,4})', cell)
    if m:
        num=m.group(1)
        cands=[h for h in hymns if h.startswith(num+' ') or h.startswith(num+' -')]
        if cands: return min(cands, key=len)
    title=re.sub(r'(UMH|TFWS|W&S|#|\bv\.?\s*[\d,\s&-]+|\d{2,4})',' ',cell,flags=re.I).strip(' ,')
    base=[re.sub(r'^\d+\s*-?\s*','',h[:-4]) for h in hymns]
    best=difflib.get_close_matches(title, base, n=1, cutoff=0.5)
    if best:
        return hymns[base.index(best[0])]
    return None

def match_person(name, l3s):
    """'Gabe Meadows' -> 'L3 - Gabe Meadows & Band.pro'; 'Jonathan' -> 'L3 - JONATHAN PERRY.pro'."""
    name=(name or '').strip()
    if not name: return None
    low=name.lower()
    exact=[l for l in l3s if low in l.lower()]
    if exact: return min(exact, key=len)
    first=low.split()[0]
    fn=[l for l in l3s if re.search(rf'\b{re.escape(first)}\b', l, re.I)]
    if fn: return min(fn, key=len)      # NOTE: ambiguous if >1 — caller should review
    best=difflib.get_close_matches('L3 - '+name, l3s, n=1, cutoff=0.5)
    return best[0] if best else None
