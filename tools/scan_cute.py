import struct
import zlib
from pathlib import Path

ROOT = Path(r"C:\Users\simon\Downloads\Cute_Fantasy_Free\Cute_Fantasy_Free")


def load(path: Path):
    data = path.read_bytes()
    i = 8
    w = h = color = None
    idat = b""
    while i < len(data):
        n = struct.unpack(">I", data[i : i + 4])[0]
        typ = data[i + 4 : i + 8]
        chunk = data[i + 8 : i + 8 + n]
        if typ == b"IHDR":
            w, h, bit, color = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        i += 12 + n
    return w, h, color, bit, len(data)


for path in sorted(ROOT.rglob("*.png")):
    w, h, color, bit, n = load(path)
    print(f"{path.relative_to(ROOT)}  {w}x{h}  color={color} bit={bit}  {n}b")

# Opacity grids for sheets we will slice.
import importlib.util
spec = importlib.util.spec_from_file_location("imp", Path(r"C:\Users\simon\Desktop\cyd october\tools\import_pack.py"))
