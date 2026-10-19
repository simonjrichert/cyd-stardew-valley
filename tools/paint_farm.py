"""Paint an original Stardew-like 20x15 farm and emit flash tile data.

Art is drawn here, not copied from the game that inspired the layout.
"""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Must match Ground in Game.h
G_GRASS, G_SOIL, G_TILLED, G_WATER, G_FENCE, G_FLOOR, G_BIN, G_BED, G_PATH = range(9)

PAL = [
    (0, 0, 0),          # 0 skip
    (36, 26, 18),       # 1 outline
    (42, 122, 32),      # 2 grass dark
    (74, 168, 42),      # 3 grass
    (124, 196, 64),     # 4 grass light
    (186, 214, 86),     # 5 grass bright
    (214, 164, 78),     # 6 dirt
    (190, 138, 62),     # 7 dirt mid
    (150, 102, 48),     # 8 dirt dark
    (112, 72, 36),      # 9 soil deep
    (168, 112, 56),     # 10 tilled
    (96, 62, 34),       # 11 furrow
    (78, 92, 128),      # 12 wet
    (204, 146, 74),     # 13 wood light
    (168, 108, 52),     # 14 wood
    (116, 70, 32),      # 15 wood dark
    (186, 70, 42),      # 16 roof
    (140, 46, 36),      # 17 roof dark
    (214, 110, 62),     # 18 roof light
    (214, 164, 96),     # 19 log light
    (176, 122, 64),     # 20 log
    (132, 84, 40),      # 21 log dark
    (108, 188, 208),    # 22 window
    (214, 240, 244),    # 23 window shine
    (28, 96, 28),       # 24 leaf dark
    (52, 150, 40),      # 25 leaf
    (110, 190, 58),     # 26 leaf light
    (224, 86, 112),     # 27 flower pink
    (244, 236, 214),    # 28 cream
    (232, 186, 54),     # 29 gold / hat
    (236, 190, 146),    # 30 skin
    (112, 68, 36),      # 31 hair
    (214, 168, 64),     # 32 hat light
    (58, 96, 184),      # 33 shirt
    (36, 62, 140),      # 34 shirt dark
    (208, 52, 40),      # 35 tomato
    (56, 148, 40),      # 36 crop
    (32, 100, 30),      # 37 crop dark
    (164, 162, 146),    # 38 stone
    (112, 110, 98),     # 39 stone dark
    (92, 58, 32),       # 40 trunk
    (248, 244, 232),    # 41 white
    (48, 32, 22),       # 42 line
    (196, 150, 82),     # 43 porch
    (232, 168, 176),    # 44 blossom
    (150, 96, 48),      # 45 chest
    (208, 160, 84),     # 46 chest light
    (64, 140, 48),      # 47 bush
]

SKIP, OUTLINE = 0, 1
GRASS_D, GRASS, GRASS_L, GRASS_B = 2, 3, 4, 5
DIRT, DIRT_M, DIRT_D = 6, 7, 8
TILLED, FURROW, WET = 10, 11, 12
WOOD_L, WOOD, WOOD_D = 13, 14, 15
ROOF, ROOF_D, ROOF_L = 16, 17, 18
LOG_L, LOG, LOG_D = 19, 20, 21
WINDOW, SHINE = 22, 23
LEAF_D, LEAF, LEAF_L = 24, 25, 26
PINK, CREAM, GOLD = 27, 28, 29
SKIN, HAIR, HAT = 30, 31, 32
SHIRT, SHIRT_D = 33, 34
TOMATO, CROP, CROP_D = 35, 36, 37
STONE, STONE_D = 38, 39
TRUNK, WHITE, LINE = 40, 41, 42
PORCH, BLOSSOM, CHEST, CHEST_L, BUSH = 43, 44, 45, 46, 47


def new(fill):
    return [[fill for _ in range(16)] for _ in range(16)]


def rect(g, x, y, w, h, c):
    for yy in range(y, y + h):
        if yy < 0 or yy >= len(g):
            continue
        row = g[yy]
        for xx in range(x, x + w):
            if 0 <= xx < len(row):
                row[xx] = c


def px(g, x, y, c):
    if 0 <= y < len(g) and 0 <= x < len(g[0]):
        g[y][x] = c


def hash16(x, y, n):
    v = (x * 374761393 + y * 668265263 + n * 1442695041) & 0xFFFFFFFF
    v = (v ^ (v >> 13)) * 1274126177 & 0xFFFFFFFF
    return v


def grass_tile(variant):
    g = new(GRASS)
    for y in range(16):
        for x in range(16):
            h = hash16(x, y, variant) % 18
            if h == 0:
                g[y][x] = GRASS_D
            elif h == 1:
                g[y][x] = GRASS_L
    for i in range(6):
        x = hash16(i, variant, 21) % 16
        y = hash16(i, variant, 22) % 13
        g[y][x] = GRASS_D
        if y + 1 < 16:
            g[y + 1][x] = GRASS_B
        if y + 2 < 16 and hash16(x, y, 8) % 2 == 0:
            g[y + 2][x] = GRASS_L
    if variant == 4:
        px(g, 8, 6, PINK)
        px(g, 8, 5, PINK)
        px(g, 7, 6, CREAM)
        px(g, 9, 6, CREAM)
        px(g, 8, 7, CROP_D)
    if variant == 5:
        px(g, 5, 10, GOLD)
        px(g, 4, 11, GOLD)
        px(g, 6, 11, GOLD)
        px(g, 5, 12, CROP_D)
    if variant == 6:
        px(g, 11, 4, BLOSSOM)
        px(g, 12, 5, BLOSSOM)
        px(g, 11, 6, LEAF)
    return g


def dirt_tile(variant):
    g = new(DIRT)
    for y in range(16):
        for x in range(16):
            h = hash16(x, y, 40 + variant) % 10
            if h < 2:
                g[y][x] = DIRT_M
            elif h == 8:
                g[y][x] = DIRT_D
            elif h == 9:
                g[y][x] = WOOD_L
    if variant == 2 and hash16(3, 3, variant) % 2 == 0:
        px(g, 4, 12, GRASS_D)
        px(g, 5, 11, GRASS)
        px(g, 5, 12, GRASS_L)
        px(g, 6, 12, GRASS_D)
    return g


def tilled_tile(wet=False):
    soil = WET if wet else TILLED
    gap = STONE_D if wet else FURROW
    g = new(soil)
    for y in range(16):
        for x in range(16):
            if y % 4 == 0:
                g[y][x] = gap
            elif hash16(x, y, 7) % 8 == 0:
                g[y][x] = DIRT_D if not wet else 12
    return g


def crop_tile(stage, wet=False):
    g = tilled_tile(wet)
    cols = (2, 6, 10, 14)
    rows = (7, 13)
    if stage == 0:
        for x in cols:
            for y in (6, 12):
                px(g, x, y, GOLD)
                px(g, x, y + 1, CROP_D)
        return g
    height = 3 if stage == 1 else 6 if stage == 2 else 7
    for x in cols:
        for y in rows:
            for dy in range(height):
                yy = y - dy
                if yy < 1:
                    continue
                g[yy][x] = CROP_D
                if 0 <= x - 1:
                    g[yy][x - 1] = CROP
                if x + 1 < 16:
                    g[yy][x + 1] = LEAF_L
            if stage >= 3:
                px(g, x, y - 2, TOMATO)
                px(g, x - 1, y - 3, TOMATO)
                px(g, x + 1, y - 1, TOMATO)
    return g


def fence_h(bg):
    g = [row[:] for row in bg]
    rect(g, 0, 6, 16, 2, WOOD)
    rect(g, 0, 8, 16, 1, WOOD_D)
    rect(g, 0, 11, 16, 2, WOOD_L)
    rect(g, 0, 13, 16, 1, WOOD_D)
    for x in (1, 13):
        rect(g, x, 3, 2, 12, WOOD)
        rect(g, x, 3, 1, 12, WOOD_L)
        rect(g, x + 1, 14, 1, 1, WOOD_D)
    return g


def fence_v(bg):
    g = [row[:] for row in bg]
    rect(g, 6, 0, 4, 16, WOOD)
    rect(g, 6, 0, 1, 16, WOOD_L)
    rect(g, 9, 0, 1, 16, WOOD_D)
    rect(g, 5, 4, 6, 2, WOOD_L)
    rect(g, 5, 10, 6, 2, WOOD_L)
    return g


def fence_post(bg):
    g = [row[:] for row in bg]
    rect(g, 5, 1, 6, 14, WOOD)
    rect(g, 5, 1, 2, 14, WOOD_L)
    rect(g, 9, 1, 2, 14, WOOD_D)
    rect(g, 4, 0, 8, 3, WOOD_D)
    return g


def tree_canopy(quadrant):
    g = grass_tile(quadrant)
    ox, oy = (0, 0) if quadrant == 0 else (0, 0)
    # quadrant 0 TL, 1 TR, 2 BL, 3 BR of a 2x2 canopy, plus trunk tiles separate
    centers = {0: (14, 14), 1: (1, 14), 2: (14, 1), 3: (1, 1)}
    cx, cy = centers[quadrant]
    for y in range(16):
        for x in range(16):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d < 150:
                h = hash16(x, y, 80 + quadrant) % 7
                g[y][x] = LEAF_D if h == 0 else LEAF_L if h > 4 else LEAF
            elif d < 175:
                g[y][x] = LEAF_D
    return g


def tree_trunk():
    g = grass_tile(1)
    rect(g, 6, 0, 4, 16, TRUNK)
    rect(g, 6, 0, 1, 16, LOG)
    rect(g, 9, 0, 1, 16, LINE)
    return g


def bush_tile():
    g = grass_tile(2)
    for y in range(4, 14):
        for x in range(2, 14):
            d = (x - 8) ** 2 + (y - 9) ** 2
            if d < 28:
                g[y][x] = BUSH if hash16(x, y, 3) % 4 else LEAF
            if d < 10 and hash16(x, y, 4) % 3 == 0:
                g[y][x] = BLOSSOM
    return g


def chest_tile(bg):
    g = [row[:] for row in bg]
    rect(g, 1, 3, 14, 12, CHEST)
    rect(g, 1, 3, 14, 4, CHEST_L)
    rect(g, 1, 7, 14, 1, WOOD_D)
    rect(g, 6, 6, 4, 4, GOLD)
    rect(g, 2, 2, 12, 2, WOOD)
    rect(g, 1, 14, 14, 1, LINE)
    rect(g, 1, 3, 1, 12, LINE)
    rect(g, 14, 3, 1, 12, LINE)
    return g


def draw_well():
    g = blank_big(32, 32, DIRT)
    for y in range(32):
        for x in range(32):
            g[y][x] = DIRT_M if hash16(x, y, 15) % 5 == 0 else DIRT
    # Posts and a small roof over the stone ring.
    rect(g, 6, 6, 3, 16, WOOD)
    rect(g, 23, 6, 3, 16, WOOD)
    for y in range(2, 16):
        half = 4 + (y - 2)
        if half > 14:
            half = 14
        for x in range(16 - half, 16 + half):
            g[y][x] = ROOF_D if y % 2 else ROOF
    # Stone ring and water.
    for y in range(16, 31):
        for x in range(4, 28):
            dx, dy = x - 15, y - 23
            if dx * dx + dy * dy <= 100:
                g[y][x] = STONE if dx * dx + dy * dy > 36 else WET
            if 30 < dx * dx + dy * dy < 40:
                g[y][x] = SHINE
    rect(g, 6, 18, 3, 4, WOOD_D)
    rect(g, 23, 18, 3, 4, WOOD_D)
    return g


def blank_big(w, h, fill):
    return [[fill for _ in range(w)] for _ in range(h)]


def big_rect(g, x, y, w, h, c):
    rect(g, x, y, w, h, c)


def draw_house():
    w, h = 128, 80
    g = blank_big(w, h, GRASS)
    for y in range(h):
        for x in range(w):
            g[y][x] = GRASS_D if hash16(x, y, 2) % 9 == 0 else GRASS
    # Roof trapezoid
    for y in range(4, 38):
        t = (y - 4) / 34
        half = int(10 + t * 50)
        x0, x1 = 64 - half, 64 + half
        for x in range(x0, x1):
            band = (y // 3) % 2
            g[y][x] = ROOF_D if band else ROOF
            if (x + y) % 11 == 0:
                g[y][x] = ROOF_L
        g[y][x0] = LINE
        if x1 - 1 < w:
            g[y][x1 - 1] = LINE
    # Chimney
    big_rect(g, 88, 8, 14, 22, STONE)
    big_rect(g, 90, 6, 10, 6, STONE_D)
    for yy in range(10, 28, 4):
        for xx in range(88, 102):
            g[yy][xx] = STONE_D
    # Log wall
    for y in range(36, 66):
        for x in range(18, 110):
            g[y][x] = LOG_L if (y % 4) < 2 else LOG
            if y % 4 == 0:
                g[y][x] = LOG_D
    big_rect(g, 18, 36, 92, 1, LINE)
    big_rect(g, 18, 36, 1, 30, LINE)
    big_rect(g, 109, 36, 1, 30, LINE)
    # Windows
    for wx in (30, 82):
        big_rect(g, wx, 42, 16, 14, WOOD_D)
        big_rect(g, wx + 2, 44, 12, 10, WINDOW)
        big_rect(g, wx + 2, 44, 5, 4, SHINE)
        big_rect(g, wx + 7, 44, 1, 10, WOOD)
        # flower box
        big_rect(g, wx, 56, 16, 3, WOOD)
        for i in range(4):
            g[55][wx + 2 + i * 4] = PINK
            g[54][wx + 3 + i * 4] = LEAF
    # Door
    big_rect(g, 54, 40, 20, 26, WOOD_D)
    big_rect(g, 56, 42, 16, 24, LOG_D)
    big_rect(g, 58, 44, 12, 10, WOOD)
    g[52][68] = GOLD
    # Porch
    for y in range(66, 80):
        for x in range(10, 118):
            g[y][x] = PORCH if (y % 3) else WOOD
            if x % 16 == 0:
                g[y][x] = WOOD_D
    big_rect(g, 10, 66, 108, 1, LINE)
    # Step
    big_rect(g, 50, 76, 28, 4, WOOD_L)
    big_rect(g, 54, 78, 20, 2, DIRT_M)
    return g


def slice_tile(big, tx, ty):
    x0, y0 = tx * 16, ty * 16
    return [row[x0:x0 + 16] for row in big[y0:y0 + 16]]


def player_tile():
    g = new(SKIP)
    rect(g, 5, 0, 6, 3, HAT)
    rect(g, 6, 0, 4, 1, GOLD)
    rect(g, 3, 3, 10, 2, HAT)
    rect(g, 4, 4, 8, 1, WOOD_D)
    rect(g, 5, 5, 6, 4, SKIN)
    px(g, 6, 6, LINE)
    px(g, 9, 6, LINE)
    px(g, 7, 8, PINK)
    rect(g, 4, 9, 8, 4, SHIRT)
    rect(g, 5, 10, 6, 2, SHIRT_D)
    rect(g, 6, 9, 4, 1, CREAM)
    rect(g, 5, 13, 2, 3, HAIR)
    rect(g, 9, 13, 2, 3, HAIR)
    px(g, 5, 15, LINE)
    px(g, 6, 15, LINE)
    px(g, 9, 15, LINE)
    px(g, 10, 15, LINE)
    # outline the hat brim
    px(g, 2, 3, LINE)
    px(g, 13, 3, LINE)
    return g


class Atlas:
    def __init__(self):
        self.tiles = []
        self.index = {}

    def add(self, grid):
        key = tuple(tuple(row) for row in grid)
        if key not in self.index:
            self.index[key] = len(self.tiles)
            self.tiles.append(key)
        return self.index[key]


def emit_bytes(grid):
    data = []
    for row in grid:
        data.extend(row)
    if len(data) != 256:
        raise SystemExit(f"tile size {len(data)}")
    lines = []
    for i in range(0, 256, 16):
        lines.append("    " + ", ".join(f"0x{b:02X}" for b in data[i:i + 16]))
    return ",\n".join(lines)


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def write_png(path, art, ground_note=None):
    # art is 15x20 of tile grids. Scale 3x so the preview is easy to read.
    scale = 3
    w, h = 20 * 16 * scale, 15 * 16 * scale
    raw = bytearray()
    for ty in range(15):
        for sy in range(16):
            row = []
            for tx in range(20):
                for sx in range(16):
                    r, g, b = PAL[art[ty][tx][sy][sx]]
                    row.extend((r, g, b))
            line = bytes(row)
            for _ in range(scale):
                expanded = bytearray()
                for i in range(0, len(line), 3):
                    expanded.extend(line[i:i + 3] * scale)
                raw += b"\x00" + bytes(expanded)

    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main():
    raise SystemExit("Farm art is built by tools/import_pack.py from the 16x16 pack.")
    atlas = Atlas()
    art = [[None for _ in range(20)] for _ in range(15)]
    ground = [[G_GRASS for _ in range(20)] for _ in range(15)]
    crop = [[0 for _ in range(20)] for _ in range(15)]

    grasses = [grass_tile(i) for i in range(7)]
    dirts = [dirt_tile(i) for i in range(4)]
    grass_ids = [atlas.add(g) for g in grasses]
    dirt_ids = [atlas.add(g) for g in dirts]

    def stamp(tx, ty, grid, gnd, crop_v=0):
        art[ty][tx] = grid
        ground[ty][tx] = gnd
        crop[ty][tx] = crop_v

    for y in range(15):
        for x in range(20):
            stamp(x, y, grasses[hash16(x, y, 1) % 4], G_GRASS)

    # Flowers on a few lawn tiles.
    for x, y in ((2, 1), (4, 6), (16, 1), (3, 13)):
        if 0 <= x < 20:
            stamp(x, y, grasses[4 + (x & 1)], G_GRASS)

    # Dirt yard, rows 6-12, inside the border. The top row fades into grass.
    edge = dirt_tile(0)
    for x in range(16):
        edge[0][x] = GRASS
        edge[1][x] = GRASS_D
        if hash16(x, 2, 9) % 2 == 0:
            edge[2][x] = GRASS
    for y in range(6, 13):
        for x in range(1, 19):
            grid = edge if y == 6 else dirts[hash16(x, y, 5) % 3]
            stamp(x, y, grid, G_PATH)

    # House over the lawn, cols 6-13, rows 1-5.
    house = draw_house()
    for ty in range(5):
        for tx in range(8):
            grid = slice_tile(house, tx, ty)
            gnd = G_FENCE
            if ty == 4:
                gnd = G_FLOOR
            if ty == 3 and tx in (3, 4):
                gnd = G_BED
            # Roof corners that stayed grass should be walkable lawn.
            grassish = sum(1 for row in grid for c in row if c in (GRASS, GRASS_D, GRASS_L, GRASS_B))
            if grassish > 200:
                gnd = G_GRASS
            stamp(6 + tx, 1 + ty, grid, gnd)

    # Trees, 2x3: canopy 2x2 plus trunks. Left and right.
    for ox, oy in ((0, 0), (18, 0)):
        for q, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
            stamp(ox + dx, oy + dy, tree_canopy(q), G_FENCE)
        stamp(ox, oy + 2, tree_trunk(), G_FENCE)
        stamp(ox + 1, oy + 2, tree_trunk(), G_FENCE)

    # Bushes along the grass/dirt edge.
    bush = bush_tile()
    for x in (1, 3, 17):
        stamp(x, 5, bush, G_FENCE)

    # Chest and a small post mailbox.
    stamp(14, 6, chest_tile(dirts[0]), G_BIN)
    mail = dirt_tile(0)
    rect(mail, 7, 2, 2, 12, WOOD_D)
    rect(mail, 4, 3, 8, 6, WOOD)
    rect(mail, 5, 4, 6, 4, CHEST_L)
    stamp(15, 6, mail, G_FENCE)

    # Well, 2x2, on the right of the yard.
    well = draw_well()
    for ty in range(2):
        for tx in range(2):
            stamp(16 + tx, 6 + ty, slice_tile(well, tx, ty), G_FENCE)

    # Garden fence around rows 8-12, cols 1-18, with a gate at cols 9-10 on row 8.
    fh = fence_h(dirts[1])
    fv = fence_v(dirts[1])
    fp = fence_post(dirts[0])
    for x in range(1, 19):
        if x not in (9, 10):
            stamp(x, 8, fh if x not in (1, 18) else fp, G_FENCE)
        stamp(x, 12, fh if x not in (1, 18) else fp, G_FENCE)
    for y in range(9, 12):
        stamp(1, y, fv, G_FENCE)
        stamp(18, y, fv, G_FENCE)

    # Crop patches. Value stored is stage+1.
    tilled = tilled_tile(False)
    for y in range(9, 12):
        for x in range(2, 7):
            stamp(x, y, tilled, G_TILLED, 2 + 1)
    for y in range(9, 12):
        for x in range(11, 15):
            stamp(x, y, tilled, G_TILLED, 3 + 1)
    # Empty beds the player can still hoe and plant.
    for y in range(9, 11):
        for x in range(7, 9):
            stamp(x, y, tilled, G_SOIL)

    # Named gameplay tiles are appended even if a scenery tile matches,
    # so the firmware can address them directly.
    named = {
        "TILE_TILLED": tilled_tile(False),
        "TILE_WATERED": tilled_tile(True),
        "TILE_CROP0": crop_tile(0),
        "TILE_CROP1": crop_tile(1),
        "TILE_CROP2": crop_tile(2),
        "TILE_CROP3": crop_tile(3),
        "TILE_PLAYER": player_tile(),
    }

    # Resolve art grids to ids. Named tiles are not part of the scenery atlas
    # unless an identical grid was already inserted.
    art_ids = [[atlas.add(art[y][x]) for x in range(20)] for y in range(15)]

    # Player start: dirt just above the gate.
    start_x, start_y = 9, 7
    if ground[start_y][start_x] not in (G_GRASS, G_SOIL, G_TILLED, G_FLOOR, G_PATH):
        raise SystemExit(f"start tile blocked {ground[start_y][start_x]}")

    sprites = []
    sprites.append("#pragma once\n\n#include <Arduino.h>\n#include <stdint.h>\n\n")
    sprites.append("// Original 16x16 farm art in a warm rural palette.\n")
    sprites.append("// One byte per pixel, index into PALETTE. Index 0 is transparent\n")
    sprites.append("// on the player only. Tiles live in flash; the blit expands one\n")
    sprites.append("// tile at a time into a 512-byte stack buffer.\n\n")
    sprites.append("static constexpr uint8_t PAL_SKIP = 0;\n")
    sprites.append(f"static constexpr uint8_t PAL_TILLED = {TILLED};\n")
    sprites.append(f"static constexpr uint8_t PAL_WET = {WET};\n")
    sprites.append("static constexpr int TILE_BYTES = 256;\n\n")
    sprites.append("static const uint16_t PALETTE[] PROGMEM = {\n")
    for r, g, b in PAL:
        sprites.append(f"    0x{rgb565(r, g, b):04X},\n")
    sprites.append("};\n\n")
    sprites.append(f"static constexpr int ART_COUNT = {len(atlas.tiles)};\n\n")

    for i, grid in enumerate(atlas.tiles):
        sprites.append(f"static const uint8_t ART_{i}[TILE_BYTES] PROGMEM = {{\n")
        sprites.append(emit_bytes(grid))
        sprites.append("\n};\n\n")

    sprites.append("static const uint8_t* artById(uint8_t id) {\n")
    sprites.append("    static const uint8_t* const table[ART_COUNT] = {\n")
    for i in range(len(atlas.tiles)):
        sprites.append(f"        ART_{i},\n")
    sprites.append("    };\n")
    sprites.append("    if (id >= ART_COUNT) return ART_0;\n")
    sprites.append("    return table[id];\n")
    sprites.append("}\n\n")

    for name, grid in named.items():
        sprites.append(f"static const uint8_t {name}[TILE_BYTES] PROGMEM = {{\n")
        sprites.append(emit_bytes(grid))
        sprites.append("\n};\n\n")

    (ROOT / "include" / "Sprites.h").write_text("".join(sprites), encoding="utf-8")
    write_atlas(atlas, named)

    def rows(matrix):
        lines = []
        for row in matrix:
            lines.append("    {" + ", ".join(str(v) for v in row) + "}")
        return ",\n".join(lines)

    tilemap = []
    tilemap.append("#pragma once\n\n#include <Arduino.h>\n\n#include \"Config.h\"\n\n")
    tilemap.append("// Scenery index per cell, plus the gameplay ground underneath.\n")
    tilemap.append("// Crop cells store stage+1. 0 means nothing is planted.\n")
    tilemap.append(f"static constexpr uint8_t PLAYER_START_X = {start_x};\n")
    tilemap.append(f"static constexpr uint8_t PLAYER_START_Y = {start_y};\n\n")
    tilemap.append(f"static const uint8_t MAP_ART[{15}][{20}] PROGMEM = {{\n")
    tilemap.append(rows(art_ids))
    tilemap.append("\n};\n\n")
    tilemap.append(f"static const uint8_t MAP_GROUND[{15}][{20}] PROGMEM = {{\n")
    tilemap.append(rows(ground))
    tilemap.append("\n};\n\n")
    tilemap.append(f"static const uint8_t MAP_CROP[{15}][{20}] PROGMEM = {{\n")
    tilemap.append(rows(crop))
    tilemap.append("\n};\n")
    (ROOT / "include" / "Tilemap.h").write_text("".join(tilemap), encoding="utf-8")

    preview = [[art[y][x] for x in range(20)] for y in range(15)]
    for y in range(15):
        for x in range(20):
            if crop[y][x]:
                preview[y][x] = crop_tile(crop[y][x] - 1)
    player = player_tile()
    base = [row[:] for row in preview[start_y][start_x]]
    for y in range(16):
        for x in range(16):
            if player[y][x] != SKIP:
                base[y][x] = player[y][x]
    preview[start_y][start_x] = base
    write_png(Path(r"C:\Users\simon\AppData\Local\Temp\cyd-farm-preview.png"), preview)
    html_path = Path(r"C:\Users\simon\AppData\Local\Cursor\AgentStores\cursor_agent_stores\7fb77068-4b60-42fb-a90b-afbbc3a8d7a9\files\visualizations\cyd-farm-look.html")
    if not html_path.exists():
        write_html(preview)
    print(f"tiles {len(atlas.tiles)} named {len(named)} start {start_x},{start_y}")


def tile_bytes(grid):
    data = bytearray()
    for row in grid:
        data.extend(row)
    if len(data) != 256:
        raise SystemExit(f"tile is {len(data)} bytes")
    return data


def write_atlas(atlas, named):
    """FAT pack copied to the microSD card as /sprites/atlas.bin."""
    order = [
        "TILE_TILLED",
        "TILE_WATERED",
        "TILE_CROP0",
        "TILE_CROP1",
        "TILE_CROP2",
        "TILE_CROP3",
        "TILE_PLAYER",
    ]
    path = ROOT / "sdcard" / "sprites" / "atlas.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(b"CYD1")
        handle.write(struct.pack("<HHH", len(PAL), len(atlas.tiles), len(order)))
        for r, g, b in PAL:
            handle.write(struct.pack("<H", rgb565(r, g, b)))
        for grid in atlas.tiles:
            handle.write(tile_bytes(grid))
        for name in order:
            handle.write(tile_bytes(named[name]))
    print(f"atlas {path} ({path.stat().st_size} bytes)")


def write_html(preview):
    pixels = []
    for ty in range(15):
        for sy in range(16):
            for tx in range(20):
                pixels.extend(preview[ty][tx][sy])
    raw = bytes(pixels)
    import base64
    b64 = base64.b64encode(raw).decode("ascii")
    pal = ",".join(f"[{r},{g},{b}]" for r, g, b in PAL)
    html = f"""<div id="cyd-farm-look" class="vis-section-stack">
  <p class="vis-sr-only">Farm screen with a log house, red roof, dirt yard, fenced crop rows, a well, and the farmer standing above the gate.</p>
  <canvas id="cyd-farm-look-canvas" width="320" height="240" role="img" aria-label="Farm with log house, crops, and dirt yard"></canvas>
</div>
<style>
  #cyd-farm-look canvas {{
    display: block;
    width: 100%;
    max-width: 640px;
    height: auto;
    image-rendering: pixelated;
    image-rendering: crisp-edges;
  }}
</style>
<script>
(function () {{
  var canvas = document.getElementById("cyd-farm-look-canvas");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var pal = [{pal}];
  var raw = atob("{b64}");
  var image = ctx.createImageData(320, 240);
  var px = image.data;
  for (var i = 0; i < raw.length; i++) {{
    var c = pal[raw.charCodeAt(i)];
    var o = i * 4;
    px[o] = c[0];
    px[o + 1] = c[1];
    px[o + 2] = c[2];
    px[o + 3] = 255;
  }}
  function fill(x, y, w, h, c) {{
    for (var yy = y; yy < y + h; yy++) {{
      for (var xx = x; xx < x + w; xx++) {{
        var o = (yy * 320 + xx) * 4;
        px[o] = c[0]; px[o + 1] = c[1]; px[o + 2] = c[2]; px[o + 3] = 255;
      }}
    }}
  }}
  var wood = [92, 58, 28];
  var woodHi = [148, 96, 48];
  var gold = [236, 196, 56];
  fill(0, 0, 320, 16, [62, 40, 22]);
  fill(0, 15, 320, 1, gold);
  fill(210, 4, 106, 8, [8, 8, 8]);
  fill(211, 5, 104, 6, [72, 180, 64]);
  for (var i = 0; i < 4; i++) {{
    fill(i * 80, 208, 80, 32, i === 0 ? woodHi : wood);
    if (i === 0) {{
      fill(i * 80, 208, 80, 2, gold);
      fill(i * 80, 238, 80, 2, gold);
    }}
  }}
  ctx.putImageData(image, 0, 0);
}})();
</script>
"""
    out = Path(r"C:\Users\simon\AppData\Local\Cursor\AgentStores\cursor_agent_stores\7fb77068-4b60-42fb-a90b-afbbc3a8d7a9\files\visualizations")
    out.mkdir(parents=True, exist_ok=True)
    (out / "cyd-farm-look.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
