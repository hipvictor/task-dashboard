"""Pre-build analysis report for one Sunday.

Reads the AUMC Worship Service Schedule (CSV export of the Google Sheet), pulls the row for
a target date, picks the template (Standard/Communion), maps each swap slot to its source
column, runs the library matcher, and prints a human-review report BEFORE any playlist is
built. Per the user: analyze + flag gaps first, then build on direction.

Usage:  python3 analyze_week.py <schedule.csv> "<Date>"   e.g.  ... schedule.csv "June 14"

Get the CSV with the Drive connector:  download_file_content(fileId=<sheet>, exportMimeType=
text/csv).  Do NOT use the markdown render — it drops trailing columns.
"""
import csv, sys, os, json, importlib.util, calendar, re

_HERE=os.path.dirname(__file__)
def _load(name):
    s=importlib.util.spec_from_file_location(name, os.path.join(_HERE, name+".py"))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
ml=_load("match_library")
INV=json.load(open(os.path.join(_HERE,"data","library_inventory.json")))
HYMNS, L3S = INV["hymns"], INV["l3s"]

# slot -> (label, column index, kind)   kind: 'hymn' | 'person' | 'ctw' | 'card'
SLOTS=[
    ("A","Welcome person",      8,  "person"),
    ("B","Accompanist (prelude)",10, "person"),
    ("C","Call to Worship",     13, "ctw"),
    ("D","Opening hymn",        15, "hymn"),
    ("T","Special music (card)",19, "card"),
    ("E","Invitation person",   28, "person"),
    ("F","Closing hymn",        30, "hymn"),
]
COMMUNION_COLS=(26,27,33)   # Communion Servers / Communion / Communion Music

MONTHS={m.lower():i for i,m in enumerate(calendar.month_name) if m}
def is_first_sunday(date_cell):
    m=re.match(r'([A-Za-z]+)\s+(\d+)', date_cell.strip())
    if not m: return None
    mo=MONTHS.get(m.group(1).lower()); day=int(m.group(2))
    return mo is not None and 1<=day<=7   # a Sunday in days 1..7 is the month's 1st Sunday

def pick_template(row, date_cell):
    communion = any(len(row)>c and row[c].strip() for c in COMMUNION_COLS)
    first = is_first_sunday(date_cell)
    if communion or first:
        why="communion columns populated" if communion else "1st Sunday of month"
        return "Communion", why
    return "Standard", "not 1st Sunday, no communion entry"

def analyze(csv_path, date):
    rows=list(csv.reader(open(csv_path, newline='')))
    hdr=rows[0]
    row=next((r for r in rows[1:] if len(r)>1 and r[1].strip().lower()==date.strip().lower()), None)
    if row is None:
        print(f"!! no row for date {date!r}"); return
    tpl, why = pick_template(row, date)
    print(f"=== Build plan — {date} ===")
    print(f"Template : {tpl}  ({why})")
    print(f"Preacher : {row[22] if len(row)>22 else ''}  |  sermon left to user (not generated)\n")
    flags=[]
    for sid,label,idx,kind in SLOTS:
        val=(row[idx].strip() if len(row)>idx else "")
        if kind=="ctw":
            note=f"regenerate from CTW doc (cell: {val or 'MISSING'})"
            mark="~";
            if not val: flags.append(f"[{sid}] CTW reference cell empty")
        elif not val:
            note="EMPTY → keep template default"; mark="!"; flags.append(f"[{sid}] {label}: source cell empty")
        elif kind=="hymn":
            f=ml.match_hymn(val, HYMNS);
            if f: note=f"→ {f}"; mark="OK"
            else: note=f"NO MATCH → placeholder slide"; mark="X"; flags.append(f"[{sid}] hymn no match: {val!r}")
        elif kind=="person":
            f=ml.match_person(val, L3S)
            if f: note=f"→ {f}"; mark="OK"
            else: note="NO MATCH → placeholder L3"; mark="X"; flags.append(f"[{sid}] person no match: {val!r}")
        elif kind=="card":
            note=f"title card text = {val!r}"; mark="OK"
        print(f"  {mark:>2} [{sid}] {label:<22} src={val[:40]!r:42} {note}")
    print()
    if flags:
        print("NEEDS REVIEW before build:")
        for f in flags: print("   -", f)
    else:
        print("All slots resolved — ready to build.")

if __name__=="__main__":
    analyze(sys.argv[1], sys.argv[2])
