# Minimal faithful protobuf wire-format codec.
# Goal: decode -> (optionally mutate leaf strings) -> encode, byte-exact for anything untouched.

def read_varint(b, i):
    shift = 0; val = 0
    while True:
        c = b[i]; i += 1
        val |= (c & 0x7f) << shift
        if not (c & 0x80): break
        shift += 7
    return val, i

def write_varint(v):
    out = bytearray()
    while True:
        c = v & 0x7f; v >>= 7
        if v: out.append(c | 0x80)
        else: out.append(c); break
    return bytes(out)

class Field:
    __slots__=('fn','wt','raw_full','value','msg','dirty')
    def __init__(s, fn, wt, raw_full, value):
        s.fn=fn; s.wt=wt; s.raw_full=raw_full; s.value=value
        s.msg=None      # parsed sub-message (list[Field]) if wt==2 and parses cleanly
        s.dirty=False

def try_parse(buf):
    try:
        fields = parse(buf)
        # re-encode must match to be considered a faithful message
        if encode(fields) == buf:
            return fields
    except Exception:
        pass
    return None

def parse(buf):
    fields=[]; i=0; n=len(buf)
    while i<n:
        start=i
        tag,i = read_varint(buf,i)
        fn = tag>>3; wt = tag&7
        if wt==0:
            v,i = read_varint(buf,i); val=v
        elif wt==1:
            val=buf[i:i+8]; i+=8
        elif wt==2:
            ln,i = read_varint(buf,i); val=buf[i:i+ln]; i+=ln
        elif wt==5:
            val=buf[i:i+4]; i+=4
        else:
            raise ValueError(f"bad wire type {wt} at {start}")
        f=Field(fn,wt,buf[start:i],val)
        if wt==2:
            f.msg=try_parse(val)
        fields.append(f)
    return fields

def encode(fields):
    out=bytearray()
    for f in fields:
        if not f.dirty:
            out += f.raw_full; continue
        tag = (f.fn<<3)|f.wt
        out += write_varint(tag)
        if f.wt==0: out += write_varint(f.value)
        elif f.wt==1: out += f.value
        elif f.wt==2:
            val = encode(f.msg) if f.msg is not None else f.value
            out += write_varint(len(val)) + val
        elif f.wt==5: out += f.value
    return bytes(out)
