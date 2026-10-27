import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_pack as ip
from build_hotbar import write_png

FURN = (
    ip.ROOT
    / "assets"
    / "stardew"
    / "Tilesets"
    / "PC _ Computer - Stardew Valley - Tilesets - Furniture.png"
)
w, h, bpp, rows = ip.load_png(FURN)

x0, y0, tw, th, sc = 720, 0, 260, 200, 3
pw, ph = tw * sc, th * sc
pix = [(16, 80, 32)] * (pw * ph)
for y in range(th):
    for x in range(tw):
        r, g, b, a = ip.pix(rows, bpp, x0 + x, y0 + y)
        if a < 16:
            r, g, b = 16, 80, 32
        if x % 16 == 0 or y % 16 == 0:
            r, g, b = min(255, r + 40), min(255, g + 40), min(255, b + 80)
        for sy in range(sc):
            for sx in range(sc):
                pix[(y * sc + sy) * pw + (x * sc + sx)] = (r, g, b)
write_png(Path("tools/_furn_caves.png"), pix, pw, ph)
print("caves grid", pw, ph)

# Also grab candidate sprites by flood-fill of opaque blobs in this region.
visited = [[False] * tw for _ in range(th)]
blobs = []
for y in range(th):
    for x in range(tw):
        if visited[y][x]:
            continue
        r, g, b, a = ip.pix(rows, bpp, x0 + x, y0 + y)
        if a < 16:
            visited[y][x] = True
            continue
        q = [(x, y)]
        visited[y][x] = True
        minx = maxx = x
        miny = maxy = y
        n = 0
        while q:
            cx, cy = q.pop()
            n += 1
            minx, maxx = min(minx, cx), max(maxx, cx)
            miny, maxy = min(miny, cy), max(maxy, cy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if nx < 0 or ny < 0 or nx >= tw or ny >= th or visited[ny][nx]:
                    continue
                rr, gg, bb, aa = ip.pix(rows, bpp, x0 + nx, y0 + ny)
                if aa < 16:
                    visited[ny][nx] = True
                    continue
                visited[ny][nx] = True
                q.append((nx, ny))
        bw, bh = maxx - minx + 1, maxy - miny + 1
        if n > 80 and bw >= 24 and bh >= 24:
            blobs.append((x0 + minx, y0 + miny, bw, bh, n))

blobs.sort(key=lambda t: -t[4])
print("blobs", len(blobs))
for b in blobs[:12]:
    print(b)
