"""Build the CYD farm from the 16x16 Farm RPG pack PNGs.

Walk.png, Interior.png, and Spring Crops.png are RAR-compressed in the
download and are not used. Idle frames supply the character animation.
"""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "assets" / "farm-pack"

G_GRASS, G_SOIL, G_TILLED, G_WATER, G_FENCE, G_FLOOR, G_BIN, G_BED, G_PATH = range(9)


def load_png(path: Path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"not a png: {path}")
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
        rows.append(bytes(row))
    return w, h, bpp, rows


def pix(rows, bpp, x, y):
    o = x * bpp
    p = rows[y]
    if bpp == 4:
        return p[o], p[o + 1], p[o + 2], p[o + 3]
    return p[o], p[o + 1], p[o + 2], 255


def cell(rows, bpp, tx, ty):
    out = []
    for y in range(ty * 16, ty * 16 + 16):
        row = []
        for x in range(tx * 16, tx * 16 + 16):
            row.append(pix(rows, bpp, x, y))
        out.append(row)
    return out


def opaque_count(tile):
    return sum(1 for row in tile for _r, _g, _b, a in row if a >= 16)


def composite(tile, bg):
    out = []
    for y in range(16):
        row = []
        for x in range(16):
            r, g, b, a = tile[y][x]
            if a < 16:
                row.append(bg[y][x])
            elif a > 240:
                row.append((r, g, b, 255))
            else:
                br, bgc, bb, _ba = bg[y][x]
                u = a / 255
                row.append((int(r * u + br * (1 - u)), int(g * u + bgc * (1 - u)), int(b * u + bb * (1 - u)), 255))
        out.append(row)
    return out


def q565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def from565(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31)


class Atlas:
    def __init__(self):
        self.tiles = []
        self.index = {}
        self.colors = {(0, 0, 0): 0}
        self.order = [(0, 0, 0)]

    def color_index(self, r, g, b, a, allow_clear):
        if a < 16 and allow_clear:
            return 0
        key = from565(q565(r, g, b))
        if key not in self.colors:
            if len(self.order) >= 256:
                best = 1
                best_d = 1 << 30
                for i, (cr, cg, cb) in enumerate(self.order[1:], 1):
                    d = (cr - key[0]) ** 2 + (cg - key[1]) ** 2 + (cb - key[2]) ** 2
                    if d < best_d:
                        best, best_d = i, d
                return best
            self.colors[key] = len(self.order)
            self.order.append(key)
        return self.colors[key]

    def add(self, tile, allow_clear=False):
        indexed = []
        for row in tile:
            indexed.append(tuple(self.color_index(r, g, b, a, allow_clear) for r, g, b, a in row))
        key = tuple(indexed)
        if key not in self.index:
            self.index[key] = len(self.tiles)
            self.tiles.append(key)
        return self.index[key]

    def add_unique(self, tile, allow_clear=False):
        indexed = []
        for row in tile:
            indexed.append(tuple(self.color_index(r, g, b, a, allow_clear) for r, g, b, a in row))
        self.tiles.append(tuple(indexed))
        return len(self.tiles) - 1


def shade(tile, num, den):
    out = []
    for row in tile:
        nrow = []
        for r, g, b, a in row:
            nrow.append((r * num // den, g * num // den, b * num // den, a))
        out.append(nrow)
    return out


def paint_plants(base, stage):
    green = (50, 140, 48, 255)
    leaf = (90, 170, 56, 255)
    red = (180, 48, 36, 255)
    gold = (210, 170, 48, 255)
    tile = [row[:] for row in base]
    cols = (3, 8, 13)
    if stage == 0:
        for x in cols:
            tile[7][x] = gold
            tile[12][x] = gold
        return tile
    height = 3 if stage == 1 else 5 if stage == 2 else 7
    for x in cols:
        for yb in (8, 14):
            for dy in range(height):
                y = yb - dy
                if y < 1:
                    continue
                tile[y][x] = green
                if x > 0:
                    tile[y][x - 1] = leaf
                if x < 15:
                    tile[y][x + 1] = leaf
            if stage >= 3 and yb - 3 >= 0:
                tile[yb - 3][x] = red
                tile[yb - 2][x] = red
    return tile


def emit_bytes(grid):
    data = []
    for row in grid:
        data.extend(row)
    lines = []
    for i in range(0, 256, 16):
        lines.append("    " + ", ".join(f"0x{b:02X}" for b in data[i : i + 16]))
    return ",\n".join(lines)


def write_png(path, art_tiles, atlas):
    scale = 3
    w, h = 20 * 16 * scale, 15 * 16 * scale
    raw = bytearray()
    pal = atlas.order
    for ty in range(15):
        for sy in range(16):
            row = []
            for tx in range(20):
                for sx in range(16):
                    r, g, b = pal[art_tiles[ty][tx][sy][sx]]
                    row.extend((r, g, b))
            line = bytes(row)
            for _ in range(scale):
                expanded = bytearray()
                for i in range(0, len(line), 3):
                    expanded.extend(line[i : i + 3] * scale)
                raw += b"\x00" + bytes(expanded)

    def chunk(tag, payload):
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


CUTE = Path(r"C:\Users\simon\Downloads\Cute_Fantasy_Free\Cute_Fantasy_Free")


def grab32(img, fx, fy):
    _w, _h, bpp, rows = img
    tiles = []
    ox, oy = fx * 32, fy * 32
    for ty in range(2):
        for tx in range(2):
            tile = []
            for y in range(16):
                row = []
                for x in range(16):
                    row.append(pix(rows, bpp, ox + tx * 16 + x, oy + ty * 16 + y))
                tile.append(row)
            tiles.append(tile)
    return tiles


def downscale32(img, fx, fy):
    _w, _h, bpp, rows = img
    ox, oy = fx * 32, fy * 32
    tile = []
    for y in range(16):
        row = []
        for x in range(16):
            row.append(pix(rows, bpp, ox + x * 2, oy + y * 2))
        tile.append(row)
    return tile


def main():
    grass_img = load_png(PACK / "Tileset" / "Tileset Grass Spring.png")
    house_img = load_png(PACK / "Objects" / "House.png")
    tree_img = load_png(PACK / "Objects" / "Maple Tree.png")
    fence_img = load_png(PACK / "Objects" / "Fence's copiar.png")
    road_img = load_png(PACK / "Objects" / "Road copiar.png")
    chest_img = load_png(PACK / "Objects" / "chest.png")
    idle_img = load_png(PACK / "Character" / "Idle.png")
    chick_img = load_png(PACK / "Farm Animals" / "Chicken Red.png")

    def grab(img, tx, ty):
        _w, _h, bpp, rows = img
        return cell(rows, bpp, tx, ty)

    def fill_clear(tile, rgb):
        r, g, b = rgb
        return [[p if p[3] >= 16 else (r, g, b, 255) for p in row] for row in tile]

    # The sheet's grass cells are mostly opaque, with a few clear pixels.
    grass_rgb = (106, 175, 82)
    grasses = [fill_clear(grab(grass_img, tx, ty), grass_rgb) for tx, ty in ((5, 1), (6, 1), (5, 2), (9, 2))]
    grass_a, grass_b, grass_c, grass_d = grasses
    fence_h = composite(grab(fence_img, 1, 2), grass_a)
    fence_v = composite(grab(fence_img, 0, 1), grass_a)
    fence_post = composite(grab(fence_img, 0, 0), grass_a)
    roads = [composite(grab(road_img, tx, ty), grass_a) for tx, ty in ((0, 0), (1, 0), (0, 1), (2, 0))]
    road_raw = grab(road_img, 0, 0)
    dirt_px = [p for row in road_raw for p in row if p[3] >= 16]
    dr = sum(p[0] for p in dirt_px) // len(dirt_px)
    dg = sum(p[1] for p in dirt_px) // len(dirt_px)
    db = sum(p[2] for p in dirt_px) // len(dirt_px)
    dark = (dr * 2 // 3, dg * 2 // 3, db * 2 // 3, 255)
    solid = [[(dr, dg, db, 255) for _ in range(16)] for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if y % 4 == 0:
                solid[y][x] = dark
            elif (x + y) % 9 == 0:
                solid[y][x] = (min(255, dr + 18), min(255, dg + 12), db, 255)
    tilled = solid
    watered = shade(solid, 3, 4)
    crops = [paint_plants(solid, stage) for stage in range(4)]

    atlas = Atlas()
    art = [[None for _ in range(20)] for _ in range(15)]
    ground = [[G_GRASS for _ in range(20)] for _ in range(15)]
    crop = [[0 for _ in range(20)] for _ in range(15)]

    def stamp(tx, ty, tile, gnd, crop_v=0, clear=False):
        art[ty][tx] = tile
        ground[ty][tx] = gnd
        crop[ty][tx] = crop_v

    for y in range(15):
        for x in range(20):
            stamp(x, y, grasses[(x * 3 + y * 5) % 4], G_GRASS)

    # Left house from the sheet, under the HUD row.
    for ty in range(6):
        for tx in range(5):
            tile = grab(house_img, tx, ty)
            if opaque_count(tile) < 12:
                continue
            merged = composite(tile, grasses[(tx + ty) % 4])
            gnd = G_FENCE
            if tx == 2 and ty == 5:
                gnd = G_BED
            stamp(1 + tx, 1 + ty, merged, gnd)

    # Maple canopy and trunk, top right.
    for ty in range(3):
        for tx in range(4):
            tile = grab(tree_img, 4 + tx, ty)
            if opaque_count(tile) < 12:
                continue
            stamp(15 + tx, 1 + ty, composite(tile, grass_b), G_FENCE)

    # Shipping chest, 2x2. The lower-left tile is the one you tap.
    for ty in range(2):
        for tx in range(2):
            tile = composite(grab(chest_img, tx, ty), grass_c)
            gnd = G_BIN if (tx, ty) == (0, 1) else G_FENCE
            stamp(12 + tx, 6 + ty, tile, gnd)

    # Dirt path from the door down to the gate.
    for i, pos in enumerate(((3, 7), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8), (8, 8))):
        stamp(pos[0], pos[1], roads[i % len(roads)], G_PATH)

    # Fence ring with a gate on row 9 at columns 7-8.
    for x in range(1, 19):
        if x not in (7, 8):
            stamp(x, 9, fence_h if x not in (1, 18) else fence_post, G_FENCE)
        stamp(x, 12, fence_h if x not in (1, 18) else fence_post, G_FENCE)
    for y in range(10, 12):
        stamp(1, y, fence_v, G_FENCE)
        stamp(18, y, fence_v, G_FENCE)

    for y in range(10, 12):
        for x in range(2, 7):
            stamp(x, y, tilled, G_TILLED, 3)
    for y in range(10, 12):
        for x in range(10, 16):
            stamp(x, y, tilled, G_TILLED, 4)
    for y in range(10, 12):
        for x in range(16, 18):
            stamp(x, y, tilled, G_SOIL)

    # Chickens on the lawn. Frame 0 is what the map stores; the game cycles frames.
    chick_tiles = [grab(chick_img, i, 0) for i in range(4)]
    chicken_ids_placeholder = []
    for pos in ((0, 8), (19, 5)):
        stamp(pos[0], pos[1], chick_tiles[0], G_FENCE)

    player_tiles = [grab(idle_img, i, 0) for i in range(4)]

    # Index scenery first, then record animation ids.
    art_ids = [[0 for _ in range(20)] for _ in range(15)]
    indexed_art = [[None for _ in range(20)] for _ in range(15)]
    for y in range(15):
        for x in range(20):
            allow = art[y][x] is chick_tiles[0]
            # Player clear is separate. Chickens keep transparency over nothing;
            # composite them onto grass so the tile is opaque and stable.
            tile = art[y][x]
            if tile is chick_tiles[0]:
                tile = composite(chick_tiles[0], grass_d)
                art[y][x] = tile
            art_ids[y][x] = atlas.add(tile, allow_clear=False)
            indexed_art[y][x] = atlas.tiles[art_ids[y][x]]

    chick_indexed = []
    for frame in chick_tiles:
        chick_indexed.append(atlas.add(composite(frame, grass_d), allow_clear=False))
    # Point chicken cells at frame 0 id.
    for pos in ((0, 8), (19, 5)):
        art_ids[pos[1]][pos[0]] = chick_indexed[0]
        indexed_art[pos[1]][pos[0]] = atlas.tiles[chick_indexed[0]]

    player_ids = [atlas.add(frame, allow_clear=True) for frame in player_tiles]

    named_tiles = {
        "TILE_TILLED": atlas.add(tilled),
        "TILE_WATERED": atlas.add(watered),
        "TILE_CROP0": atlas.add(crops[0]),
        "TILE_CROP1": atlas.add(crops[1]),
        "TILE_CROP2": atlas.add(crops[2]),
        "TILE_CROP3": atlas.add(crops[3]),
        "TILE_PLAYER": player_ids[0],
    }
    # Named gameplay tiles are stored both as ids (for the flash table) and as
    # raw indexed grids in the named section of the SD pack.
    named_grids = [atlas.tiles[named_tiles[name]] for name in (
        "TILE_TILLED", "TILE_WATERED", "TILE_CROP0", "TILE_CROP1", "TILE_CROP2", "TILE_CROP3", "TILE_PLAYER"
    )]

    dirt_index = atlas.color_index(dr, dg, db, 255, False)
    wet_rgb = from565(q565(dr * 3 // 4, dg * 3 // 4, min(255, db + 40)))
    wet_index = atlas.color_index(wet_rgb[0], wet_rgb[1], wet_rgb[2], 255, False)

    start_x, start_y = 3, 7
    if ground[start_y][start_x] not in (G_GRASS, G_PATH, G_FLOOR, G_SOIL, G_TILLED):
        raise SystemExit(f"start blocked at {start_x},{start_y} ground {ground[start_y][start_x]}")

    sprites = []
    sprites.append("#pragma once\n\n#include <Arduino.h>\n#include <stdint.h>\n\n")
    sprites.append("// 16x16 cells cut from the Farm RPG tiny pack.\n")
    sprites.append("// Index 0 is clear on the player. One tile is 256 bytes in flash.\n\n")
    sprites.append("static constexpr uint8_t PAL_SKIP = 0;\n")
    sprites.append(f"static constexpr uint8_t PAL_TILLED = {dirt_index};\n")
    sprites.append(f"static constexpr uint8_t PAL_WET = {wet_index};\n")
    sprites.append("static constexpr int TILE_BYTES = 256;\n\n")
    sprites.append("static const uint16_t PALETTE[] PROGMEM = {\n")
    for r, g, b in atlas.order:
        sprites.append(f"    0x{q565(r, g, b):04X},\n")
    sprites.append("};\n\n")
    sprites.append(f"static constexpr int ART_COUNT = {len(atlas.tiles)};\n\n")
    for i, grid in enumerate(atlas.tiles):
        sprites.append(f"static const uint8_t ART_{i}[TILE_BYTES] PROGMEM = {{\n{emit_bytes(grid)}\n}};\n\n")
    sprites.append("static const uint8_t* artById(uint8_t id) {\n")
    sprites.append("    static const uint8_t* const table[ART_COUNT] = {\n")
    for i in range(len(atlas.tiles)):
        sprites.append(f"        ART_{i},\n")
    sprites.append("    };\n    if (id >= ART_COUNT) return ART_0;\n    return table[id];\n}\n\n")
    for name, grid in zip(
        ("TILE_TILLED", "TILE_WATERED", "TILE_CROP0", "TILE_CROP1", "TILE_CROP2", "TILE_CROP3", "TILE_PLAYER"),
        named_grids,
    ):
        sprites.append(f"static const uint8_t {name}[TILE_BYTES] PROGMEM = {{\n{emit_bytes(grid)}\n}};\n\n")
    (ROOT / "include" / "Sprites.h").write_text("".join(sprites), encoding="utf-8")

    def rows(matrix):
        return ",\n".join("    {" + ", ".join(str(v) for v in row) + "}" for row in matrix)

    anim = []
    anim.append("#pragma once\n\n#include <Arduino.h>\n\n#include \"Config.h\"\n\n")
    anim.append(f"static constexpr uint8_t PLAYER_START_X = {start_x};\n")
    anim.append(f"static constexpr uint8_t PLAYER_START_Y = {start_y};\n")
    anim.append("static constexpr uint8_t PLAYER_ANIM[4] = {" + ", ".join(str(i) for i in player_ids) + "};\n")
    anim.append("static constexpr uint8_t CHICKEN_ANIM[4] = {" + ", ".join(str(i) for i in chick_indexed) + "};\n\n")
    anim.append("static const uint8_t MAP_ART[15][20] PROGMEM = {\n" + rows(art_ids) + "\n};\n\n")
    anim.append("static const uint8_t MAP_GROUND[15][20] PROGMEM = {\n" + rows(ground) + "\n};\n\n")
    anim.append("static const uint8_t MAP_CROP[15][20] PROGMEM = {\n" + rows(crop) + "\n};\n")
    (ROOT / "include" / "Tilemap.h").write_text("".join(anim), encoding="utf-8")

    atlas_path = ROOT / "sdcard" / "sprites" / "atlas.bin"
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    with atlas_path.open("wb") as handle:
        handle.write(b"CYD1")
        handle.write(struct.pack("<HHH", len(atlas.order), len(atlas.tiles), 7))
        for r, g, b in atlas.order:
            handle.write(struct.pack("<H", q565(r, g, b)))
        for grid in atlas.tiles:
            handle.write(bytes(b for row in grid for b in row))
        for grid in named_grids:
            handle.write(bytes(b for row in grid for b in row))
    print(f"tiles {len(atlas.tiles)} colors {len(atlas.order)} atlas {atlas_path.stat().st_size}")
    print(f"player {player_ids} chicken {chick_indexed} dirt {dirt_index} wet {wet_index}")

    preview = [[indexed_art[y][x] for x in range(20)] for y in range(15)]
    base = [list(row) for row in preview[start_y][start_x]]
    player = atlas.tiles[player_ids[0]]
    for y in range(16):
        for x in range(16):
            if player[y][x] != 0:
                base[y][x] = player[y][x]
    preview[start_y][start_x] = base
    write_png(Path(r"C:\Users\simon\AppData\Local\Temp\cyd-farm-pack.png"), preview, atlas)


if __name__ == "__main__":
    main()
