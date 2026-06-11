"""Guard against silently-truncated Drive downloads.

A .pro truncated at a field boundary still parses and round-trips cleanly, so size is the
only reliable integrity signal. After fetching library files, call this with the sizes
reported by get_file_metadata; it fails loudly on any short/missing file so they can be
re-fetched BEFORE a build goes out (this is exactly the Lift Every Voice bug: 9773 of 21736
bytes downloaded, looked valid, imported with no slides).

Usage:
    python3 check_sizes.py <dir> sizes.json      # sizes.json = {"519 - ....pro": 21736, ...}
or import and call verify(dir, {name: drive_size}).
"""
import os, sys, json

def verify(directory, expected):
    bad=[]
    for name, dz in expected.items():
        p=os.path.join(directory, name)
        lz=os.path.getsize(p) if os.path.exists(p) else None
        if lz!=dz: bad.append((name, lz, dz))
    if bad:
        lines="\n".join(f"  {n}: local={l} drive={d}  ({'MISSING' if l is None else 'TRUNCATED'})"
                         for n,l,d in bad)
        raise AssertionError("re-fetch these files before building:\n"+lines)
    print(f"OK: {len(expected)} files match Drive sizes")

if __name__=="__main__":
    verify(sys.argv[1], json.load(open(sys.argv[2])))
