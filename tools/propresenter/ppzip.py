"""Write archives in ProPresenter's exact .proplaylist zip dialect.

ProPresenter 7 writes a non-standard ZIP64 that its own importer relies on; a stock zip
(incl. Python zipfile) imports the playlist `data` but fails to index the bundled .pro
entries -> presentations import with "no slides". Replicated from a real church export:

  * stored only (method 0), version-needed 45, made-by 0x031e, flags 0, ext-attrs 0
  * EVERY entry forces csize=usize=0xFFFFFFFF and carries a 24-byte zip64 extra
    (id 0x0001, len 0x18) = <usize:u64><csize:u64><local_header_offset:u64>,
    in BOTH the local file header and the central directory header
  * central-dir 32-bit offset field holds the real offset too (redundant, but that's PP)
  * trailer: Zip64 EOCD (sizeofrec 44) + Zip64 locator + classic EOCD
Entries are stored flat (basename at archive root); the manifest's relative paths tell PP
where each lands in the library.
"""
import struct, zlib

_DOST, _DOSD = 0x622e, 0x5cbd   # arbitrary fixed DOS time/date; PP ignores it on import

def write(out_path, entries):
    """entries: list of (arcname:str, data:bytes), written in order."""
    out=bytearray()
    central=bytearray()
    for name, data in entries:
        nb=name.encode("utf-8")
        crc=zlib.crc32(data) & 0xffffffff
        off=len(out)
        z64=struct.pack("<QQQ", len(data), len(data), off)      # usize, csize, offset
        extra=struct.pack("<HH", 0x0001, len(z64))+z64          # id, size(0x18), payload
        # local file header
        out += b"PK\x03\x04"
        out += struct.pack("<HHHHH", 45, 0, 0, _DOST, _DOSD)    # ver, flags, method, time, date
        out += struct.pack("<III", crc, 0xFFFFFFFF, 0xFFFFFFFF) # crc, csize, usize (forced zip64)
        out += struct.pack("<HH", len(nb), len(extra))
        out += nb + extra + data
        # central directory header (same forced-zip64 extra)
        central += b"PK\x01\x02"
        central += struct.pack("<HH", 0x031e, 45)               # made-by, need
        central += struct.pack("<HHHH", 0, 0, _DOST, _DOSD)     # flags, method, time, date
        central += struct.pack("<III", crc, 0xFFFFFFFF, 0xFFFFFFFF)
        central += struct.pack("<HHH", len(nb), len(extra), 0)  # nlen, elen, clen
        central += struct.pack("<HHII", 0, 0, 0, off & 0xFFFFFFFF)  # disk, iatt, eatt, offset
        central += nb + extra

    cd_off=len(out); cd_size=len(central); n=len(entries)
    out += central
    # Zip64 end of central directory record (size-of-record field = 44)
    z64eocd_off=len(out)
    out += b"PK\x06\x06" + struct.pack("<QHHIIQQQQ", 44, 0x031e, 45, 0, 0, n, n, cd_size, cd_off)
    # Zip64 EOCD locator
    out += b"PK\x06\x07" + struct.pack("<IQI", 0, z64eocd_off, 1)
    # classic EOCD
    out += b"PK\x05\x06" + struct.pack("<HHHHIIH", 0, 0, n & 0xffff, n & 0xffff,
                                       cd_size & 0xFFFFFFFF, cd_off & 0xFFFFFFFF, 0)
    open(out_path,"wb").write(out)
    return out_path
