"""Compose the house interior from Pixel_16_interiors and emit src/Interior.cpp.

The screen is 20x15 tiles. Row 0 sits under the status bar and rows 13-14 sit
under the tool bar. The room itself is a Stardew-style octagon: black void
outside, a gold wall frame on every edge, and chamfered corners.
"""

import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_pack as ip

ROOT = ip.ROOT
SHEET = Path(r"C:\Users\simon\Downloads\Pixel_16_interiors_v2_free\Pixel_16_interiors_v2_free\tiles and items.png")
STARDEW = ROOT / "assets" / "stardew"
FARMHOUSE = STARDEW / "Tilesets" / "PC _ Computer - Stardew Valley - Tilesets - Farmhouse.png"
FURNITURE = STARDEW / "Tilesets" / "PC _ Computer - Stardew Valley - Tilesets - Furniture.png"
OUT_CPP = ROOT / "src" / "Interior.cpp"
PREVIEW = ROOT / "tools" / "_house_preview.png"

G_FENCE, G_FLOOR, G_BED, G_DOOR = 4, 5, 7, 9

W, H = 20, 15
PW, PH = W * 16, H * 16

# Octagon sits between the HUD and the hotbar.
X0, X1 = 6, 313
Y0, Y1 = 16, 207
CHAMFER = 40
BORDER = 7
WALL_H = 38
WALL_Y1 = Y0 + BORDER + WALL_H
DOOR_X0, DOOR_X1 = 144, 175


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def solid(r, g, b):
    return [(r, g, b)] * 256


def inside_octagon(x, y):
    if x < X0 or x > X1 or y < Y0 or y > Y1:
        return False
    if (x - X0) + (y - Y0) < CHAMFER:
        return False
    if (X1 - x) + (y - Y0) < CHAMFER:
        return False
    if (x - X0) + (Y1 - y) < CHAMFER:
        return False
    if (X1 - x) + (Y1 - y) < CHAMFER:
        return False
    return True


def edge_dist(x, y):
    d = min(x - X0, X1 - x, y - Y0, Y1 - y)
    d = min(d, (x - X0) + (y - Y0) - CHAMFER)
    d = min(d, (X1 - x) + (y - Y0) - CHAMFER)
    d = min(d, (x - X0) + (Y1 - y) - CHAMFER)
    d = min(d, (X1 - x) + (Y1 - y) - CHAMFER)
    return d


def in_door_gap(x, y):
    return DOOR_X0 <= x <= DOOR_X1 and y >= Y1 - BORDER - 2


def floor_color(x, y):
    plank = y // 8
    if plank % 2 == 0:
        c = (214, 158, 90) if x % 2 == 0 else (204, 146, 80)
    else:
        c = (190, 134, 70) if x % 2 == 0 else (180, 124, 62)
    if y % 8 == 0:
        c = (138, 88, 46)
    return c


def wall_color(x, y):
    board = x // 8
    if board % 2 == 0:
        c = (148, 78, 44)
    else:
        c = (130, 66, 36)
    if x % 8 == 0:
        c = (78, 38, 22)
    elif x % 8 == 1:
        c = (168, 96, 54)
    # Darker wainscot on the lower third of the north wall.
    if y >= WALL_Y1 - 14:
        c = tuple(max(0, v - 36) for v in c)
        if y >= WALL_Y1 - 2:
            c = (72, 36, 22)
    return c


def border_color(d):
    if d <= 0:
        return (72, 32, 12)
    if d == 1:
        return (196, 108, 40)
    if d == 2:
        return (228, 148, 58)
    if d == 3:
        return (236, 168, 74)
    if d == 4:
        return (204, 118, 44)
    if d == 5:
        return (176, 92, 34)
    return (110, 52, 22)


def is_farmhouse_wall(r, g, b, a):
    if a < 20 or r + g + b < 40:
        return True
    if g > 120 and r > 180 and b < 130:
        return True
    if g > 90 and r > 150 and (r - g) < 90 and (g - b) > 40 and b < 90:
        return True
    return False


def farmhouse_fireplace_pixels(frows, fbpp):
    """Brick chimney + hearth from the Stardew farmhouse tileset, wall keyed out."""
    from collections import deque

    seeds = ((144, 8), (144, 40), (136, 16), (152, 16), (130, 55), (124, 58))
    seen = set()
    q = deque(seeds)
    pixels = []
    while q:
        x, y = q.popleft()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        if not (118 <= x <= 163 and 0 <= y <= 78):
            continue
        if x >= 160 and y >= 62:
            continue
        if x < 128 and y >= 74:
            continue
        r, g, b, a = ip.pix(frows, fbpp, x, y)
        if is_farmhouse_wall(r, g, b, a):
            continue
        pixels.append((x, y, r, g, b))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            q.append((x + dx, y + dy))
    return pixels


def door_tile(side):
    tile = solid(78, 52, 40)
    for y in range(16):
        for x in range(16):
            r, g, b = 150, 96, 52
            if y < 2 or y > 13:
                r, g, b = 96, 58, 36
            if side == 0 and x < 2:
                r, g, b = 96, 58, 36
            if side == 1 and x > 13:
                r, g, b = 96, 58, 36
            if side == 0 and x > 13:
                r, g, b = 70, 42, 28
            if side == 1 and x < 2:
                r, g, b = 70, 42, 28
            if 6 <= y <= 9 and ((side == 0 and 11 <= x <= 13) or (side == 1 and 2 <= x <= 4)):
                r, g, b = 230, 196, 90
            tile[y * 16 + x] = (r, g, b)
    return tile


def paint_shell():
    pix = [(0, 0, 0)] * (PW * PH)
    kind = [0] * (PW * PH)  # 0 void, 1 border, 2 wall, 3 floor, 4 door
    for y in range(PH):
        for x in range(PW):
            i = y * PW + x
            if not inside_octagon(x, y):
                continue
            if in_door_gap(x, y):
                pix[i] = floor_color(x, y)
                kind[i] = 4
                continue
            d = edge_dist(x, y)
            if d < BORDER:
                pix[i] = border_color(d)
                kind[i] = 1
            elif y < WALL_Y1:
                pix[i] = wall_color(x, y)
                kind[i] = 2
            else:
                pix[i] = floor_color(x, y)
                kind[i] = 3
    return pix, kind


def slice_tiles(pix, kind):
    room = [[None for _ in range(W)] for _ in range(H)]
    ground = [[G_FENCE for _ in range(W)] for _ in range(H)]
    for ty in range(H):
        for tx in range(W):
            tile = []
            counts = [0, 0, 0, 0, 0]
            for py in range(16):
                for px in range(16):
                    i = (ty * 16 + py) * PW + (tx * 16 + px)
                    tile.append(pix[i])
                    counts[kind[i]] += 1
            room[ty][tx] = tile
            floorish = counts[3] + counts[4]
            if counts[4] > 80:
                ground[ty][tx] = G_DOOR
            elif floorish > 140 and counts[1] < 40 and counts[2] < 80:
                ground[ty][tx] = G_FLOOR
            else:
                ground[ty][tx] = G_FENCE
    return room, ground


def main():
    w, h, bpp, rows = ip.load_png(SHEET)
    _, _, fbpp, frows = ip.load_png(FARMHOUSE)
    _, _, ubpp, urows = ip.load_png(FURNITURE)
    pix, kind = paint_shell()
    room, ground = slice_tiles(pix, kind)

    def cell_opaque(sx, sy):
        return any(ip.pix(rows, bpp, sx * 16 + x, sy * 16 + y)[3] > 20 for y in range(16) for x in range(16))

    def stamp_tile(sx, sy, px, py, mark, flip_x=False, flip_y=False):
        if not cell_opaque(sx, sy):
            return
        base = room[py][px]
        for y in range(16):
            for x in range(16):
                sxpx = (15 - x) if flip_x else x
                sypy = (15 - y) if flip_y else y
                r, g, b, a = ip.pix(rows, bpp, sx * 16 + sxpx, sy * 16 + sypy)
                if a > 20:
                    base[y * 16 + x] = (r, g, b)
        if mark == "block":
            ground[py][px] = G_FENCE
        elif mark == "bed":
            ground[py][px] = G_BED

    def paste(sx, sy, tw, th, dx, dy, mark, flip_x=False, flip_y=False):
        for ty in range(th):
            for tx in range(tw):
                stamp_tile(sx + tx, sy + ty, dx + tx, dy + ty, mark, flip_x, flip_y)

    def put_px(X, Y, c, a):
        if X < 0 or Y < 0 or X >= PW or Y >= PH:
            return
        if not inside_octagon(X, Y):
            return
        tile = room[Y // 16][X // 16]
        i = (Y % 16) * 16 + (X % 16)
        if a >= 250:
            tile[i] = c
        else:
            r0, g0, b0 = tile[i]
            tile[i] = tuple((c[k] * a + (r0, g0, b0)[k] * (255 - a)) // 255 for k in range(3))

    SPRITES = {
        "bed_green": (16, 96, 38, 127),
        "bed_blue": (16, 128, 38, 159),
        "table": (49, 107, 78, 127),
        "stool_a": (83, 103, 93, 111),
        "stool_b": (83, 118, 93, 127),
        "nightstand": (99, 115, 110, 127),
        "books": (66, 131, 75, 143),
        "sofa": (82, 131, 125, 156),
        "plant": (49, 140, 60, 159),
        "lamp": (68, 148, 76, 159),
        "chair_back": (129, 147, 142, 159),
        "chair_front": (145, 142, 158, 159),
        "chair_side": (161, 141, 173, 159),
        "rug_oval_tan": (162, 65, 188, 78),
        "rug_oval_blue": (162, 81, 188, 94),
        "rug_orange": (128, 80, 159, 95),
        "rug_teal": (133, 101, 168, 122),
    }

    def stamp_box(src_rows, src_bpp, box, X, Y, mark="block"):
        x0, y0, x1, y1 = box
        cover = {}
        for y in range(y1 - y0 + 1):
            for x in range(x1 - x0 + 1):
                r, g, b, a = ip.pix(src_rows, src_bpp, x0 + x, y0 + y)
                if a <= 20:
                    continue
                put_px(X + x, Y + y, (r, g, b), a)
                if a >= 250:
                    key = ((Y + y) // 16, (X + x) // 16)
                    cover[key] = cover.get(key, 0) + 1
        for (ty, tx), n in cover.items():
            if mark == "floor" or n < 40:
                continue
            if not (0 <= ty < H and 0 <= tx < W):
                continue
            ground[ty][tx] = G_BED if mark == "bed" else G_FENCE

    def sprite(name, X, Y, mark="block", flip_x=False):
        x0, y0, x1, y1 = SPRITES[name]
        cover = {}
        for y in range(y1 - y0 + 1):
            for x in range(x1 - x0 + 1):
                sx = x1 - x if flip_x else x0 + x
                r, g, b, a = ip.pix(rows, bpp, sx, y0 + y)
                if a <= 20:
                    continue
                put_px(X + x, Y + y, (r, g, b), a)
                if a >= 250:
                    key = ((Y + y) // 16, (X + x) // 16)
                    cover[key] = cover.get(key, 0) + 1
        for (ty, tx), n in cover.items():
            if mark == "floor" or n < 48:
                continue
            if not (0 <= ty < H and 0 <= tx < W):
                continue
            ground[ty][tx] = G_BED if mark == "bed" else G_FENCE

    def furn(box, X, Y, mark="block"):
        stamp_box(urows, ubpp, box, X, Y, mark)

    # Stardew farmhouse fireplace on the north wall, left of the beds.
    fp = farmhouse_fireplace_pixels(frows, fbpp)
    fp_x0 = min(x for x, y, r, g, b in fp)
    fp_y0 = min(y for x, y, r, g, b in fp)
    FP_DX, FP_DY = 46, 22
    cover = {}
    for x, y, r, g, b in fp:
        put_px(FP_DX + (x - fp_x0), FP_DY + (y - fp_y0), (r, g, b), 255)
        key = ((FP_DY + (y - fp_y0)) // 16, (FP_DX + (x - fp_x0)) // 16)
        cover[key] = cover.get(key, 0) + 1
    for (ty, tx), n in cover.items():
        if n >= 40 and 0 <= ty < H and 0 <= tx < W:
            ground[ty][tx] = G_FENCE

    CLOCK = (706, 371, 721, 386)
    HILLS = (289, 770, 335, 797)
    MOUNTAIN = (81, 771, 110, 798)
    LAMP_WOOD = (50, 733, 62, 766)
    PLANT_RED = (32, 695, 47, 719)
    PLANT_LEAF = (112, 689, 127, 719)
    PLANT_BUSH = (80, 695, 95, 719)
    BOOKSHELF = (690, 790, 721, 837)
    DRESSER = (610, 792, 641, 821)
    FLOOR_LAMP = (531, 945, 544, 980)
    BROOM = (706, 1109, 720, 1151)

    # Rugs first so furniture draws on top.
    sprite("rug_teal", 126, 136, "floor")
    sprite("rug_orange", 54, 150, "floor")
    sprite("rug_oval_tan", 70, 168, "floor")
    sprite("rug_oval_blue", 198, 168, "floor")

    # Wall hangings on the north wall, east of the beds.
    furn(HILLS, 172, 26, "floor")
    furn(CLOCK, 226, 32, "floor")
    furn(MOUNTAIN, 250, 26, "floor")

    # Beds against the north wall, east of the hearth.
    sprite("bed_green", 98, 52, "bed")
    sprite("nightstand", 126, 64)
    furn(LAMP_WOOD, 128, 38)
    sprite("bed_blue", 142, 52, "bed")
    furn(PLANT_BUSH, 270, 54)

    # West reading corner.
    furn(BOOKSHELF, 18, 98)
    furn(BROOM, 22, 146)
    furn(PLANT_RED, 90, 104)

    sprite("sofa", 122, 104)
    furn(PLANT_LEAF, 106, 102)
    furn(FLOOR_LAMP, 176, 96)

    TX, TY = 220, 86
    sprite("chair_front", TX + 8, TY - 13)
    sprite("table", TX, TY)
    sprite("chair_back", TX + 8, TY + 15)
    sprite("chair_side", TX - 14, TY + 3, flip_x=True)
    sprite("chair_side", TX + 31, TY + 3)

    furn(DRESSER, 266, 118)
    furn(PLANT_BUSH, 278, 152)

    # Double door in the south wall gap. Farmer stands on the tile above it.
    room[12][9] = door_tile(0)
    room[12][10] = door_tile(1)
    ground[12][9] = G_DOOR
    ground[12][10] = G_DOOR
    ground[11][9] = G_FLOOR
    ground[11][10] = G_FLOOR

    tiles = []
    index_of = {}
    art = [[0 for _ in range(W)] for _ in range(H)]
    for y in range(H):
        for x in range(W):
            raw = b"".join(bytes(p) for p in room[y][x])
            if raw not in index_of:
                index_of[raw] = len(tiles)
                tiles.append(room[y][x])
            art[y][x] = index_of[raw]
    if len(tiles) > 255:
        raise SystemExit(f"too many unique tiles: {len(tiles)}")

    lines = [
        '#include <Arduino.h>',
        '',
        '#include "Interior.h"',
        "",
        "// Generated by tools/build_interior.py from Pixel_16_interiors.",
        f"static const uint16_t HOUSE_TILES[{len(tiles)}][256] PROGMEM = {{",
    ]
    for tile in tiles:
        vals = ", ".join(f"0x{rgb565(*p):04X}" for p in tile)
        lines.append(f"    {{{vals}}},")
    lines.append("};")
    lines.append("")
    lines.append("static const uint8_t HOUSE_ART[15][20] PROGMEM = {")
    for row in art:
        lines.append("    {" + ", ".join(str(v) for v in row) + "},")
    lines.append("};")
    lines.append("")
    lines.append("static const uint8_t HOUSE_GROUND[15][20] PROGMEM = {")
    for row in ground:
        lines.append("    {" + ", ".join(str(v) for v in row) + "},")
    lines.append("};")
    lines.append("")
    lines.append("const uint16_t* houseTile(uint8_t x, uint8_t y) {")
    lines.append("    if (x >= 20 || y >= 15) return HOUSE_TILES[0];")
    lines.append("    uint8_t id = pgm_read_byte(&HOUSE_ART[y][x]);")
    lines.append("    if (id >= (sizeof(HOUSE_TILES) / sizeof(HOUSE_TILES[0]))) return HOUSE_TILES[0];")
    lines.append("    return HOUSE_TILES[id];")
    lines.append("}")
    lines.append("")
    lines.append("uint8_t houseGround(uint8_t x, uint8_t y) {")
    lines.append("    if (x >= 20 || y >= 15) return 4;  // G_FENCE")
    lines.append("    return pgm_read_byte(&HOUSE_GROUND[y][x]);")
    lines.append("}")
    lines.append("")
    OUT_CPP.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"tiles {len(tiles)} -> {OUT_CPP}")

    scale = 2
    pw, ph = PW * scale, PH * scale
    out = bytearray(pw * ph * 3)
    for y in range(H):
        for x in range(W):
            tile = room[y][x]
            for py in range(16):
                for px in range(16):
                    r, g, b = tile[py * 16 + px]
                    for sy in range(scale):
                        for sx in range(scale):
                            ox = (x * 16 + px) * scale + sx
                            oy = (y * 16 + py) * scale + sy
                            o = (oy * pw + ox) * 3
                            out[o : o + 3] = bytes((r, g, b))
    for y in range(16 * scale):
        for x in range(pw):
            o = (y * pw + x) * 3
            out[o : o + 3] = b"\x3e\x28\x16"
    for y in range(208 * scale, ph):
        for x in range(pw):
            o = (y * pw + x) * 3
            out[o : o + 3] = b"\x5c\x3a\x1c"
    raw = b"".join(b"\x00" + out[y * pw * 3 : (y + 1) * pw * 3] for y in range(ph))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", pw, ph, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    PREVIEW.write_bytes(png)
    print(f"preview {PREVIEW}")


if __name__ == "__main__":
    main()
