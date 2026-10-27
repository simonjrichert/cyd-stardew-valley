"""Compose the mine interior from the classic brown Mines tileset.

The screen is 20x15 tiles. Row 0 sits under the status bar and rows 13-14 sit
under the tool bar. The room copies the first Stardew mine level: a boulder
north wall with a wooden up-ladder, a diagonal shaft frame on the far left,
rails that leave the shaft and run east along the floor, scaffolding on the
right, vines and lanterns on the wall, and dark ferns outside the cave.

Wall tiles come from the pre-composed boulder chunk at sheet (4..12, 4..7):
row 4 is the top of a wall face, row 7 the bottom edge that overlaps the
floor, column 7 a face that ends with floor to its right, column 8 one that
ends with floor to its left.
"""

import base64
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_pack as ip

ROOT = ip.ROOT
STARDEW = ROOT / "assets" / "stardew"
MINES = STARDEW / "Tilesets" / "PC _ Computer - Stardew Valley - Tilesets - The Mines _ Skull Cavern.png"
MISC = (
    STARDEW
    / "Miscellaneous"
    / (
        "PC _ Computer - Stardew Valley - Miscellaneous - Harvested Crops, "
        "Seed Packets, Minerals, Food, Equipment, & Miscellaneous Objects.png"
    )
)
OUT_CPP = ROOT / "src" / "Mine.cpp"
PREVIEW = ROOT / "tools" / "_mine_preview.png"
HTML = ROOT / "tools" / "_mine_preview.html"

G_FENCE, G_FLOOR, G_DOOR = 4, 5, 9
ROCK_NONE, ROCK_STONE, ROCK_COPPER, ROCK_IRON = 0, 1, 2, 3

# Floor rocks. Keep spawn (7,5), the ladder walk-off, rails, crate, and barrel clear.
ROCKS = [
    (6, 6, ROCK_STONE),
    (10, 6, ROCK_STONE),
    (12, 6, ROCK_COPPER),
    (15, 6, ROCK_STONE),
    (4, 7, ROCK_STONE),
    (8, 7, ROCK_STONE),
    (11, 7, ROCK_IRON),
    (6, 9, ROCK_COPPER),
    (9, 9, ROCK_STONE),
    (12, 9, ROCK_STONE),
    (15, 9, ROCK_STONE),
    (4, 10, ROCK_STONE),
    (10, 10, ROCK_STONE),
    (14, 10, ROCK_IRON),
    (8, 11, ROCK_STONE),
]

W, H = 20, 15
PW, PH = W * 16, H * 16

# Ladder on the left of the north wall; the farmer steps off it onto the floor.
LADDER_X, LADDER_Y0, LADDER_Y1 = 7, 1, 4
SPAWN_X, SPAWN_Y = 7, 5

# '#' rock/void, '.' floor
LAYOUT = [
    "####################",  # 0  status bar
    "####################",  # 1
    "####################",  # 2
    "####################",  # 3
    "####################",  # 4
    "###........#########",  # 5
    "###..............###",  # 6
    "###..............###",  # 7
    "###..............###",  # 8
    "###..............###",  # 9
    "###..............###",  # 10
    "#####......#########",  # 11
    "####################",  # 12
    "####################",  # 13  tool bar
    "####################",  # 14  tool bar
]


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def hash16(x, y, n):
    v = (x * 374761393 + y * 668265263 + n * 1442695041) & 0xFFFFFFFF
    v = (v ^ (v >> 13)) * 1274126177 & 0xFFFFFFFF
    return v


def solid(r, g, b):
    return [[(r, g, b, 255) for _ in range(16)] for _ in range(16)]


def over(fg, bg):
    """Alpha-composite fg on bg; result is fully opaque."""
    out = []
    for y in range(16):
        row = []
        for x in range(16):
            r, g, b, a = fg[y][x]
            br, bgc, bb, _ = bg[y][x]
            if a >= 250:
                row.append((r, g, b, 255))
            elif a < 8:
                row.append((br, bgc, bb, 255))
            else:
                u = a / 255
                row.append((int(r * u + br * (1 - u)), int(g * u + bgc * (1 - u)), int(b * u + bb * (1 - u)), 255))
        out.append(row)
    return out


def shade(tile, k):
    return [[(int(r * k), int(g * k), int(b * k), a) for r, g, b, a in row] for row in tile]


def rot180(tile):
    return [list(reversed(row)) for row in reversed(tile)]


def write_png(path, room, scale):
    pw, ph = PW * scale, PH * scale
    out = bytearray(pw * ph * 3)
    for y in range(H):
        for x in range(W):
            tile = room[y][x]
            for py in range(16):
                for sy in range(scale):
                    oy = (y * 16 + py) * scale + sy
                    o = (oy * pw + x * 16 * scale) * 3
                    line = b"".join(bytes(tile[py][px][:3]) * scale for px in range(16))
                    out[o : o + len(line)] = line
    hud, gold, bar = (62, 40, 22), (236, 196, 56), (92, 58, 28)
    for y in range(16 * scale):
        c = bytes(hud if y < 16 * scale - 2 else gold)
        out[y * pw * 3 : (y + 1) * pw * 3] = c * pw
    for y in range(208 * scale, ph):
        out[y * pw * 3 : (y + 1) * pw * 3] = bytes(bar) * pw
    raw = b"".join(b"\x00" + out[y * pw * 3 : (y + 1) * pw * 3] for y in range(ph))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", pw, ph, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def write_html(png_path, html_path):
    b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    html_path.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Mine interior preview</title>
<style>
  body {{ margin: 0; background: #120c08; color: #e8d2b0; font-family: Georgia, serif; text-align: center; }}
  main {{ padding: 28px 20px 48px; }}
  h1 {{ font-size: 22px; font-weight: normal; margin: 0 0 8px; }}
  p {{ margin: 0 0 18px; color: #b89a72; font-size: 14px; }}
  .row {{ display: flex; gap: 32px; justify-content: center; align-items: flex-start; flex-wrap: wrap; }}
  figure {{ margin: 0; }}
  figcaption {{ font-size: 13px; color: #b89a72; margin-top: 8px; }}
  img {{ display: block; image-rendering: pixelated; border: 3px solid #8a5a28; }}
</style>
</head>
<body>
<main>
  <h1>The Mines</h1>
  <p>Temporary preview of the 320&times;240 CYD screen</p>
  <div class="row">
    <figure><img alt="Mine 2x" width="640" height="480" src="data:image/png;base64,{b64}"><figcaption>2&times;</figcaption></figure>
    <figure><img alt="Mine 1x" width="320" height="240" src="data:image/png;base64,{b64}"><figcaption>Actual pixels</figcaption></figure>
  </div>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def main():
    _w, _h, bpp, rows = ip.load_png(MINES)

    def t(tx, ty):
        return ip.cell(rows, bpp, tx, ty)

    black = solid(0, 0, 0)
    # Variants within ~2 luma of each other so the floor does not checkerboard.
    floor_plain = [t(x, y) for x, y in ((9, 8), (10, 8), (12, 8), (10, 9), (10, 10), (11, 10), (8, 10), (6, 10))]
    floor_plain = [shade(over(f, black), 0.85) for f in floor_plain]

    floor = [[b"." == c.encode() for c in row] for row in LAYOUT]

    def is_floor(x, y):
        return 0 <= x < W and 0 <= y < H and floor[y][x]

    room = [[black for _ in range(W)] for _ in range(H)]
    ground = [[G_FENCE for _ in range(W)] for _ in range(H)]

    def base_floor(x, y):
        return floor_plain[hash16(x, y, 3) % len(floor_plain)]

    for y in range(H):
        for x in range(W):
            if floor[y][x]:
                room[y][x] = base_floor(x, y)
                ground[y][x] = G_FLOOR

    face_row = {1: 7, 2: 6, 3: 5, 4: 4}
    face_cols = (9, 10, 11, 12)

    for y in range(H):
        for x in range(W):
            if floor[y][x]:
                continue
            d = 0
            for k in range(1, 5):
                if is_floor(x, y + k):
                    d = k
                    break
                if y + k >= H:
                    break
            left, right = is_floor(x - 1, y), is_floor(x + 1, y)
            up = is_floor(x, y - 1)
            under = base_floor(x, y)
            if d:
                row = face_row[d]
                if left and not right:
                    room[y][x] = over(t(8, row), under)
                elif right and not left:
                    room[y][x] = over(t(7, row), under)
                else:
                    room[y][x] = over(t(face_cols[hash16(x, y, 7) % 4], row), black if d > 1 else under)
            elif up:
                room[y][x] = over(t(6 + hash16(x, y, 9) % 2, 13), under)
            elif right:
                room[y][x] = over(t(7, 5 + (y % 2)), under)
            elif left:
                room[y][x] = over(t(8, 5 + (y % 2)), under)
            elif is_floor(x + 1, y - 1) or is_floor(x - 1, y - 1):
                room[y][x] = over(t(5, 13), black)

    # Diagonal shaft frame on the far left; its foot sits on the floor and
    # the rails come out of it.
    for i in range(5):
        for j in range(2):
            x, y = 3 + j, 1 + i
            room[y][x] = over(t(j, 8 + i), room[y][x])
            ground[y][x] = G_FENCE
    ground[5][4] = G_FLOOR

    # Rails: out of the shaft, down, then east along the floor.
    room[5][5] = over(t(2, 14), base_floor(5, 5))
    for y in (6, 7):
        room[y][5] = over(t(1, 13), base_floor(5, y))
    room[8][5] = over(rot180(t(2, 14)), base_floor(5, 8))
    for x in range(6, 17):
        room[8][x] = over(t(3, 13), base_floor(x, 8))

    # Stone cobbles under the rails, like the patches in the first mine level.
    for j, y in enumerate((9, 10)):
        for i, x in enumerate((8, 9, 10)):
            room[y][x] = shade(over(t(1 + i, 1 + j), black), 0.85)

    # Wooden up-ladder: hole at the top, feet on the floor.
    for i, y in enumerate(range(LADDER_Y0, LADDER_Y1 + 1)):
        room[y][LADDER_X] = over(t(3, 4 + i), room[y][LADDER_X])
        ground[y][LADDER_X] = G_DOOR

    # Vines on the wall left of the ladder and on the right section.
    room[2][5] = over(t(7, 1), room[2][5])
    room[3][5] = over(t(7, 2), room[3][5])
    room[3][12] = over(t(8, 1), room[3][12])
    room[4][12] = over(t(8, 2), room[4][12])

    # Lanterns on the wall.
    room[2][10] = over(t(1, 6), room[2][10])
    room[3][14] = over(t(1, 7), room[3][14])

    # Scaffold against the east wall.
    for j in range(3):
        for i in range(3):
            x, y = 15 + i, 3 + j
            room[y][x] = over(t(4 + i, j), room[y][x])

    # Crate by the ladder, barrel on the right.
    room[5][9] = over(t(15, 14), room[5][9])
    ground[5][9] = G_FENCE
    room[7][13] = over(t(13, 10), room[7][13])
    ground[7][13] = G_FENCE

    # Dark ferns outside the cave.
    ferns = [(9, 1), (10, 1), (11, 1), (12, 1), (13, 1), (9, 2), (10, 2), (11, 2), (13, 2), (14, 2), (15, 1), (12, 3)]
    for y in range(1, 13):
        for x in range(W):
            if room[y][x] is black and hash16(x, y, 21) % 3 == 0:
                fx, fy = ferns[hash16(x, y, 23) % len(ferns)]
                room[y][x] = over(t(fx, fy), black)

    _mw, _mh, mbpp, misc = ip.load_png(MISC)

    def grab_obj(tx, ty):
        tile = []
        for y in range(16):
            row = []
            for x in range(16):
                r, g, b, a = ip.pix(misc, mbpp, tx * 16 + x, ty * 16 + y)
                row.append((r, g, b, 255) if a >= 40 else (0, 0, 0, 0))
            tile.append(row)
        return tile

    rock_art = {
        ROCK_STONE: grab_obj(10, 1),
        ROCK_COPPER: grab_obj(14, 1),
        ROCK_IRON: grab_obj(12, 1),
    }

    rock_kind = [[ROCK_NONE] * W for _ in range(H)]
    for x, y, kind in ROCKS:
        if ground[y][x] != G_FLOOR:
            raise SystemExit(f"rock at {x},{y} is not floor")
        if (x, y) == (SPAWN_X, SPAWN_Y):
            raise SystemExit("rock on spawn")
        rock_kind[y][x] = kind

    if ground[SPAWN_Y][SPAWN_X] != G_FLOOR:
        raise SystemExit(f"spawn not on floor at {SPAWN_X},{SPAWN_Y}")

    tiles, index_of = [], {}
    art = [[0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            flat = [px[:3] for row in room[y][x] for px in row]
            key = bytes(c for p in flat for c in p)
            if key not in index_of:
                index_of[key] = len(tiles)
                tiles.append(flat)
            art[y][x] = index_of[key]
    if len(tiles) > 255:
        raise SystemExit(f"too many unique tiles: {len(tiles)}")

    lines = [
        "#include <Arduino.h>",
        "",
        '#include "Mine.h"',
        "",
        "// Generated by tools/build_mine.py from the classic brown Mines tileset.",
        f"static const uint16_t MINE_TILES[{len(tiles)}][256] PROGMEM = {{",
    ]
    for tile in tiles:
        lines.append("    {" + ", ".join(f"0x{rgb565(*p):04X}" for p in tile) + "},")
    lines += ["};", "", "static const uint8_t MINE_ART[15][20] PROGMEM = {"]
    lines += ["    {" + ", ".join(str(v) for v in row) + "}," for row in art]
    lines += ["};", "", "static const uint8_t MINE_GROUND[15][20] PROGMEM = {"]
    lines += ["    {" + ", ".join(str(v) for v in row) + "}," for row in ground]
    lines += ["};", "", "static const uint8_t MINE_ROCK[15][20] PROGMEM = {"]
    lines += ["    {" + ", ".join(str(v) for v in row) + "}," for row in rock_kind]

    def emit_rock(name, tile):
        vals = []
        for row in tile:
            for px in row:
                if px[3] < 40:
                    vals.append("0x0000")
                else:
                    vals.append(f"0x{rgb565(px[0], px[1], px[2]):04X}")
        return [
            f"static const uint16_t {name}[256] PROGMEM = {{",
            "    " + ", ".join(vals) + ",",
            "};",
            "",
        ]

    lines += ["};", ""]
    lines += emit_rock("ROCK_ART_STONE", rock_art[ROCK_STONE])
    lines += emit_rock("ROCK_ART_COPPER", rock_art[ROCK_COPPER])
    lines += emit_rock("ROCK_ART_IRON", rock_art[ROCK_IRON])
    lines += [
        "const uint16_t* mineTile(uint8_t x, uint8_t y) {",
        "    if (x >= 20 || y >= 15) return MINE_TILES[0];",
        "    uint8_t id = pgm_read_byte(&MINE_ART[y][x]);",
        "    if (id >= (sizeof(MINE_TILES) / sizeof(MINE_TILES[0]))) return MINE_TILES[0];",
        "    return MINE_TILES[id];",
        "}",
        "",
        "uint8_t mineGround(uint8_t x, uint8_t y) {",
        "    if (x >= 20 || y >= 15) return 4;  // G_FENCE",
        "    return pgm_read_byte(&MINE_GROUND[y][x]);",
        "}",
        "",
        "uint8_t mineRockKind(uint8_t x, uint8_t y) {",
        "    if (x >= 20 || y >= 15) return 0;",
        "    return pgm_read_byte(&MINE_ROCK[y][x]);",
        "}",
        "",
        "const uint16_t* mineRockArt(uint8_t kind) {",
        "    if (kind == 2) return ROCK_ART_COPPER;",
        "    if (kind == 3) return ROCK_ART_IRON;",
        "    return ROCK_ART_STONE;",
        "}",
        "",
    ]
    OUT_CPP.write_text("\n".join(lines), encoding="utf-8")
    print(f"tiles {len(tiles)} -> {OUT_CPP}")

    preview = [row[:] for row in room]
    for x, y, kind in ROCKS:
        preview[y][x] = over(rock_art[kind], preview[y][x])
    write_png(PREVIEW, preview, 1)
    write_html(PREVIEW, HTML)
    write_png(ROOT / "tools" / "_mine_preview_3x.png", preview, 3)
    print(f"preview {PREVIEW}")


if __name__ == "__main__":
    main()
