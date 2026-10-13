# Brute-force dump of Qt rcc compressed blobs (zlib / zstd) embedded in a binary.
import sys, zlib, os, struct
try:
    import zstandard
except ImportError:
    zstandard = None
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
d = open(src, 'rb').read()
n = 0
i = 0
while True:
    i = d.find(b'\x78', i + 1)
    if i < 0: break
    if d[i+1] not in (0x01, 0x5e, 0x9c, 0xda): continue
    if i < 8: continue
    total, usize = struct.unpack('>II', d[i-8:i])
    if not (0 < usize < 50_000_000 and 4 < total < 50_000_000): continue
    try:
        dec = zlib.decompressobj().decompress(d[i:i+total-4], usize + 1)
    except Exception:
        continue
    if len(dec) != usize: continue
    open(f'{out}/{i:08x}.bin', 'wb').write(dec); n += 1
if zstandard:
    i = 0
    while True:
        i = d.find(b'\x28\xb5\x2f\xfd', i + 1)
        if i < 0: break
        total = struct.unpack('>I', d[i-4:i])[0]
        try:
            dec = zstandard.ZstdDecompressor().decompress(d[i:i+total], max_output_size=50_000_000)
        except Exception:
            continue
        open(f'{out}/{i:08x}.zst.bin', 'wb').write(dec); n += 1
print(src, '->', n, 'blobs', 'zstd' if zstandard else 'no-zstd')
