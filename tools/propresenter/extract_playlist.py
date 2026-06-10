"""Extract a ProPresenter .proplaylist (non-standard ZIP64, method=store).

Stock unzip/zipfile choke on these ("overlapped components"). We scan local file
headers (PK\\x03\\x04) and read true sizes from the ZIP64 extra field (id 0x0001).
"""
import struct, os, sys

def extract(src, out):
    os.makedirs(out, exist_ok=True)
    d=open(src,'rb').read(); i=0; n=0
    while True:
        j=d.find(b'PK\x03\x04', i)
        if j<0: break
        nlen,elen=struct.unpack_from('<HH', d, j+26)
        csize,usize=struct.unpack_from('<II', d, j+18)
        name=d[j+30:j+30+nlen].decode('utf-8','replace')
        extra=d[j+30+nlen:j+30+nlen+elen]; k=0; z64=[]
        while k+4<=len(extra):
            hid,hsz=struct.unpack_from('<HH', extra, k)
            if hid==0x0001: z64=list(struct.unpack_from('<%dQ'%(hsz//8), extra, k+4))
            k+=4+hsz
        real_u=z64[0] if (usize==0xFFFFFFFF and z64) else usize
        real_c=(z64[1] if len(z64)>1 else real_u) if csize==0xFFFFFFFF else csize
        start=j+30+nlen+elen
        blob=d[start:start+(real_c or real_u)]
        if not name.endswith('/'):
            p=os.path.join(out,name); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p,'wb').write(blob); n+=1
        i=start+1
    return n

if __name__=='__main__':
    print('extracted', extract(sys.argv[1], sys.argv[2]), 'entries')
