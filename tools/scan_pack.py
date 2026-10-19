import struct
import zlib
from pathlib import Path

ROOT = Path(r"C:\Users\simon\Desktop\cyd october\assets\farm-pack")


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
            w, h, _bit, color = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        i += 12 + n
    raw = zlib.decompress(idat)
    bpp = {6: 4, 2: 3}[color]
    stride = w * bpp
    rows = []
    pos = 0
    prev = bytearray(stride)

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        return b if pb <= pc else c

    for _y in range(h):
        filt = raw[pos]
        pos += 1
        row = bytearray(raw[pos : pos + stride])
        pos += stride
        if filt == 1:
            for x in range(stride):
                left = row[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + left) & 255
        elif filt == 2:
            for x in range(stride):
                row[x] = (row[x] + prev[x]) & 255
        elif filt == 3:
            for x in range(stride):
                left = row[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + ((left + prev[x]) // 2)) & 255
        elif filt == 4:
            for x in range(stride):
                a = row[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + paeth(a, b, c)) & 255
        prev = row
        rows.append(row)
    return w, h, bpp, rows


def cell_avg(rows, bpp, tx, ty):
    rs = gs = bs = n = 0
    for y in range(ty * 16, ty * 16 + 16):
        for x in range(tx * 16, tx * 16 + 16):
            o = x * bpp
            p = rows[y]
            if p[o + 3] < 16:
                continue
            rs += p[o]
            gs += p[o + 1]
            bs += p[o + 2]
            n += 1
    if n == 0:
        return "...."
    return f"{rs // n:02x}{gs // n:02x}{bs // n:02x}"


files = [
    ROOT / "Objects" / "House.png",
    ROOT / "Character" / "Idle.png",
    ROOT / "Objects" / "Fence's copiar.png",
    ROOT / "Tileset" / "Tileset Grass Spring.png",
    ROOT / "Objects" / "Road copiar.png",
    ROOT / "Objects" / "Maple Tree.png",
    ROOT / "Objects" / "chest.png",
    ROOT / "Farm Animals" / "Chicken Red.png",
]
for path in files:
    w, h, bpp, rows = load(path)
    print("\n", path.name, w, h)
    for ty in range(h // 16):
        print(ty, " ".join(cell_avg(rows, bpp, tx, ty) for tx in range(w // 16)))
