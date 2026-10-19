import struct
import zlib
from pathlib import Path

ROOT = Path(r"C:\Users\simon\Downloads\Cute_Fantasy_Free\Cute_Fantasy_Free")


def load(path):
    data = path.read_bytes()
    i = 8
    w = h = None
    idat = b""
    while i < len(data):
        n = struct.unpack(">I", data[i : i + 4])[0]
        typ = data[i + 4 : i + 8]
        chunk = data[i + 8 : i + 8 + n]
        if typ == b"IHDR":
            w, h = struct.unpack(">II", chunk[:8])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        i += 12 + n
    raw = zlib.decompress(idat)
    bpp = 4
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
    return w, h, rows


def grid(path, cell):
    w, h, rows = load(path)
    print(f"\n{path.name} {w}x{h} cell {cell}")
    tw, th = w // cell, h // cell
    for ty in range(th):
        vals = []
        for tx in range(tw):
            n = 0
            for y in range(ty * cell, ty * cell + cell):
                for x in range(tx * cell, tx * cell + cell):
                    if rows[y][x * 4 + 3] > 16:
                        n += 1
            vals.append(f"{int(100 * n / (cell * cell)):3d}")
        print(f"{ty:2d}", " ".join(vals))


pairs = [
    (ROOT / "Player" / "Player.png", 32),
    (ROOT / "Outdoor decoration" / "Outdoor_Decor_Free.png", 16),
    (ROOT / "Outdoor decoration" / "Fences.png", 16),
    (ROOT / "Tiles" / "Water_Tile.png", 16),
    (ROOT / "Tiles" / "FarmLand_Tile.png", 16),
    (ROOT / "Tiles" / "Path_Tile.png", 16),
    (ROOT / "Animals" / "Chicken" / "Chicken.png", 32),
    (ROOT / "Animals" / "Pig" / "Pig.png", 32),
    (ROOT / "Enemies" / "Slime_Green.png", 32),
    (ROOT / "Outdoor decoration" / "Oak_Tree.png", 16),
    (ROOT / "Outdoor decoration" / "House_1_Wood_Base_Blue.png", 16),
]
for path, cell in pairs:
    grid(path, cell)
