"""Mix the Cute Fantasy free pack into the 16x16 farm."""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_pack as ip

ROOT = ip.ROOT
CUTE = Path(r"C:\Users\simon\Downloads\Cute_Fantasy_Free\Cute_Fantasy_Free")
G_GRASS, G_SOIL, G_TILLED, G_FENCE, G_FLOOR, G_BIN, G_BED, G_PATH, G_WATER = (
    ip.G_GRASS, ip.G_SOIL, ip.G_TILLED, ip.G_FENCE, ip.G_FLOOR, ip.G_BIN, ip.G_BED, ip.G_PATH, ip.G_WATER,
)
G_FORAGE = 10
ENV = ROOT / "assets" / "stardew" / "Environment"


def main():
    grass = ip.load_png(CUTE / "Tiles" / "Grass_Middle.png")
    grass_tile = ip.cell(grass[3], grass[2], 0, 0)
    farmland = ip.load_png(CUTE / "Tiles" / "FarmLand_Tile.png")
    soils = [ip.cell(farmland[3], farmland[2], tx, ty) for ty in range(3) for tx in range(3)]
    path = ip.cell(ip.load_png(CUTE / "Tiles" / "Path_Middle.png")[3], 4, 0, 0)
    water_mid = ip.cell(ip.load_png(CUTE / "Tiles" / "Water_Middle.png")[3], 4, 0, 0)
    water = ip.load_png(CUTE / "Tiles" / "Water_Tile.png")
    shore = lambda tx, ty: ip.cell(water[3], water[2], tx, ty)

    decor = ip.load_png(CUTE / "Outdoor decoration" / "Outdoor_Decor_Free.png")
    fences = ip.load_png(CUTE / "Outdoor decoration" / "Fences.png")
    house = ip.load_png(CUTE / "Outdoor decoration" / "House_1_Wood_Base_Blue.png")
    oak = ip.load_png(CUTE / "Outdoor decoration" / "Oak_Tree.png")
    chest = ip.cell(ip.load_png(CUTE / "Outdoor decoration" / "Chest.png")[3], 4, 0, 0)
    player = ip.load_png(CUTE / "Player" / "Player.png")
    chicken = ip.load_png(CUTE / "Animals" / "Chicken" / "Chicken.png")
    pig = ip.load_png(CUTE / "Animals" / "Pig" / "Pig.png")
    sheep = ip.load_png(CUTE / "Animals" / "Sheep" / "Sheep.png")
    cow = ip.load_png(CUTE / "Animals" / "Cow" / "Cow.png")
    slime = ip.load_png(CUTE / "Enemies" / "Slime_Green.png")

    def dcell(tx, ty):
        return ip.composite(ip.cell(decor[3], decor[2], tx, ty), grass_tile)

    def fcell(tx, ty):
        return ip.composite(ip.cell(fences[3], fences[2], tx, ty), grass_tile)

    fence_h = fcell(1, 1)
    fence_v = fcell(0, 1)
    fence_post = fcell(2, 2)
    flowers = [dcell(0, 8), dcell(1, 8), dcell(2, 9), dcell(3, 10), dcell(0, 11)]
    rocks = dcell(0, 2)
    lamp = dcell(6, 1)
    sprouts = [ip.cell(decor[3], decor[2], tx, ty) for tx, ty in ((4, 1), (5, 2), (6, 2), (4, 5))]

    def crop_tile(stage):
        return ip.composite(sprouts[stage], soils[stage % len(soils)])

    atlas = ip.Atlas()

    def copy_tile(tile):
        return [list(row) for row in tile]

    art = [[copy_tile(grass_tile) for _ in range(20)] for _ in range(15)]
    ground = [[G_GRASS for _ in range(20)] for _ in range(15)]
    crop = [[0 for _ in range(20)] for _ in range(15)]

    def stamp(tx, ty, tile, gnd, crop_v=0):
        art[ty][tx] = tile
        ground[ty][tx] = gnd
        crop[ty][tx] = crop_v

    # Log house with a blue roof. The step is the bottom row.
    hx, hy = 1, 0
    for ty in range(8):
        for tx in range(6):
            tile = ip.cell(house[3], house[2], tx, ty)
            if ip.opaque_count(tile) < 8:
                continue
            merged = ip.composite(tile, grass_tile)
            gnd = G_FENCE
            if ty == 7:
                gnd = G_FLOOR
            if ty == 6 and tx in (2, 3):
                gnd = G_BED
            stamp(hx + tx, hy + ty, merged, gnd)

    # Oak on the hill.
    for ty in range(5):
        for tx in range(4):
            tile = ip.cell(oak[3], oak[2], tx, ty)
            if ip.opaque_count(tile) < 8:
                continue
            stamp(16 + tx, ty, ip.composite(tile, grass_tile), G_FENCE)

    # Pond with a grassy shore, and a slime on the bank.
    pond = {
        (12, 5): shore(0, 0), (13, 5): shore(1, 0), (14, 5): shore(2, 0),
        (12, 6): shore(0, 1), (13, 6): water_mid, (14, 6): shore(2, 1),
        (12, 7): shore(0, 2), (13, 7): shore(1, 2), (14, 7): shore(2, 2),
    }
    for (x, y), tile in pond.items():
        stamp(x, y, tile, G_WATER)

    # Flowers, a rock, and a lamp along the lawn.
    for i, pos in enumerate(((0, 3), (8, 3), (10, 4), (15, 6), (16, 8))):
        stamp(pos[0], pos[1], flowers[i % len(flowers)], G_PATH)
    stamp(0, 5, rocks, G_FENCE)
    stamp(7, 7, lamp, G_PATH)
    # Chest sits beside the lane so the lane itself stays open.
    stamp(9, 8, ip.composite(chest, grass_tile), G_BIN)

    # Dirt lane from the door, through both gates, to the gap between the plots.
    for pos in ((3, 8), (4, 8), (4, 9), (5, 8), (6, 8), (7, 8), (8, 8), (8, 9), (9, 9)):
        if ground[pos[1]][pos[0]] == G_GRASS:
            stamp(pos[0], pos[1], path, G_PATH)

    # Pasture fence. Gates at the door and between the two plots.
    for x in range(1, 19):
        piece = fence_post if x in (1, 18) else fence_h
        if x not in (4, 5, 8, 9, 10):
            stamp(x, 9, piece, G_FENCE)
        stamp(x, 12, piece, G_FENCE)
    for y in range(10, 12):
        stamp(1, y, fence_v, G_FENCE)
        stamp(18, y, fence_v, G_FENCE)

    for y in range(10, 12):
        for x in range(2, 8):
            stamp(x, y, soils[(x + y) % 9], G_TILLED, 3 if (x + y) % 2 == 0 else 2)
    for y in range(10, 12):
        for x in range(10, 17):
            stamp(x, y, soils[(x * 2 + y) % 9], G_TILLED, 4)
    stamp(16, 10, soils[0], G_SOIL)
    stamp(16, 11, soils[1], G_SOIL)

    grass_sheet = ip.load_png(ENV / "PC _ Computer - Stardew Valley - Environment - Grass.png")
    fruit_sheet = ip.load_png(ENV / "PC _ Computer - Stardew Valley - Environment - Fruit Trees.png")
    bush_sheet = ip.load_png(ENV / "PC _ Computer - Stardew Valley - Environment - Bushes.png")
    forage_sheet = ip.load_png(ENV / "PC _ Computer - Stardew Valley - Environment - Forage.png")

    def mutable_tile(tx, ty):
        return art[ty][tx]

    def blit_sheet(sheet, sx0, sy0, sw, sh, dx, dy, gnd=None, crop_v=0, cover=40):
        _, _, bpp, rows = sheet
        hit = {}
        for y in range(sh):
            for x in range(sw):
                X, Y = dx + x, dy + y
                if X < 0 or Y < 0 or X >= 320 or Y >= 240:
                    continue
                r, g, b, a = ip.pix(rows, bpp, sx0 + x, sy0 + y)
                if a < 24 or (r > 248 and g > 248 and b > 248) or (r + g + b < 24):
                    continue
                tx, ty = X // 16, Y // 16
                if tx < 0 or tx >= 20 or ty < 0 or ty >= 13:
                    continue
                if ground[ty][tx] != G_GRASS and ground[ty][tx] != G_FORAGE:
                    continue
                tile = mutable_tile(tx, ty)
                px, py = X % 16, Y % 16
                if a >= 240:
                    tile[py][px] = (r, g, b, 255)
                else:
                    br, bgc, bb, _ba = tile[py][px]
                    u = a / 255
                    tile[py][px] = (
                        int(r * u + br * (1 - u)),
                        int(g * u + bgc * (1 - u)),
                        int(b * u + bb * (1 - u)),
                        255,
                    )
                if a >= 200:
                    hit[(tx, ty)] = hit.get((tx, ty), 0) + 1
        if gnd is None:
            return
        for (tx, ty), n in hit.items():
            if n < cover:
                continue
            if ground[ty][tx] not in (G_GRASS, G_FORAGE):
                continue
            ground[ty][tx] = gnd
            if gnd == G_FORAGE and crop_v:
                crop[ty][tx] = crop_v
            elif gnd == G_FENCE:
                crop[ty][tx] = 0

    misc_sheet = ip.load_png(
        ROOT / "assets" / "stardew" / "Miscellaneous" / (
            "PC _ Computer - Stardew Valley - Miscellaneous - Harvested Crops, "
            "Seed Packets, Minerals, Food, Equipment, & Miscellaneous Objects.png"
        )
    )

    # Grass tufts first so bushes and the tree sit on top. Stay walkable.
    for tx, ty, gx in (
        (7, 0, 0), (8, 1, 15), (9, 2, 31), (9, 0, 0),
        (0, 1, 31), (0, 6, 15), (0, 7, 0),
        (11, 6, 31), (11, 8, 15), (15, 2, 0), (15, 5, 15),
    ):
        x0, y0 = gx, 2 if gx else 0
        w0, h0 = 14, 18
        blit_sheet(grass_sheet, x0, y0, w0, h0, tx * 16 + (16 - w0) // 2, ty * 16 + 16 - h0)

    # Spring forage you can pick up. Walkable; corridors stay open.
    blit_sheet(forage_sheet, 7, 6, 16, 16, 7 * 16, 1 * 16, G_FORAGE, crop_v=2, cover=8)
    blit_sheet(forage_sheet, 62, 6, 16, 16, 0 * 16, 4 * 16, G_FORAGE, crop_v=3, cover=8)
    blit_sheet(forage_sheet, 34, 6, 15, 16, 11 * 16, 7 * 16, G_FORAGE, crop_v=4, cover=8)

    # One modest bush north of the pond. The east corner is the mineshaft.
    blit_sheet(bush_sheet, 1, 132, 32, 32, 10 * 16, 1 * 16 + 2, G_FENCE, cover=28)

    # Apple tree, 3x5 tiles, north of the pond. Trunk is blocked; fruit is tappable.
    blit_sheet(fruit_sheet, 192, 400, 48, 80, 12 * 16, 0, G_FENCE, cover=24)
    # Fallen apple beside the trunk.
    blit_sheet(misc_sheet, 208, 400, 16, 16, 15 * 16, 4 * 16, G_FORAGE, crop_v=1, cover=8)

    # East-edge mine: overlapping cute rocks form an irregular hill under the
    # oak. Only the timber frame and rails from the mines sheet sit in it —
    # the rectangular cave fill is dropped so the silhouette isn't a box.
    mines_sheet = ip.load_png(
        ROOT / "assets" / "stardew" / "Tilesets" / (
            "PC _ Computer - Stardew Valley - Tilesets - The Mines _ Skull Cavern.png"
        )
    )

    def blit_over(sheet, sx0, sy0, sw, sh, dx, dy, gnd=None, key=18, a_cut=16, flip_h=False, cover=12, skip_green=False):
        _, _, bpp, rows = sheet
        hit = {}
        for y in range(sh):
            for x in range(sw):
                X, Y = dx + x, dy + y
                if X < 0 or Y < 0 or X >= 320 or Y >= 240:
                    continue
                tx, ty = X // 16, Y // 16
                if tx < 0 or tx >= 20 or ty < 0 or ty >= 13:
                    continue
                srcx = sx0 + (sw - 1 - x) if flip_h else sx0 + x
                r, g, b, a = ip.pix(rows, bpp, srcx, sy0 + y)
                if a < a_cut or (key and r + g + b < key):
                    continue
                if skip_green and g > r + 18 and g > b + 10 and g > 70:
                    continue
                art[ty][tx][Y % 16][X % 16] = (r, g, b, 255)
                hit[(tx, ty)] = hit.get((tx, ty), 0) + 1
        if gnd is None:
            return
        for (tx, ty), n in hit.items():
            if n >= cover:
                ground[ty][tx] = gnd
                crop[ty][tx] = 0

    def blit_rock(stx, sty, dx, dy):
        blit_over(decor, stx * 16, sty * 16, 16, 16, dx, dy, G_FENCE, key=0, a_cut=24, cover=8, skip_green=True)

    GRASS_RGB = grass_tile[8][8][:3]
    ROCK_PAL = ((38, 43, 68), (60, 66, 88), (108, 124, 157), (142, 154, 180))
    mouth_cx, mouth_cy, mouth_rx, mouth_ry = 298, 96, 11, 20

    def is_lawn(p, y=0):
        r, g, b = p[:3]
        if abs(r - GRASS_RGB[0]) + abs(g - GRASS_RGB[1]) + abs(b - GRASS_RGB[2]) <= 24:
            return True
        if abs(r - 57) + abs(g - 137) + abs(b - 74) <= 14:
            return True
        if abs(r - 49) + abs(g - 113) + abs(b - 57) <= 18:
            return True
        # Keep oak leaves in the canopy; fill decor-grass specks below it.
        if y < 56 and g > 145:
            return False
        if g > r + 18 and g > b + 10 and g > 70:
            return True
        return False

    def in_mouth(x, y):
        dx = (x - mouth_cx) / mouth_rx
        dy = (y - mouth_cy) / mouth_ry
        return dx * dx + dy * dy < 1.2

    def hill_left(y):
        # Irregular west face of the east-edge hill. Stays right of the flower
        # at (16,8) and above the fence at y=144.
        if y < 34 or y > 141:
            return 320
        if y < 52:
            base = 282
        elif y < 72:
            base = 268
        elif y < 118:
            base = 262
        else:
            base = 270
        wave = ((y * 3) ^ (y >> 2)) % 7 - 3
        return base + wave

    def paint_rock_px(x, y):
        pal = ROCK_PAL[(x * 7 + y * 13) & 3]
        j = (x + y) & 1
        art[y // 16][x // 16][y % 16][x % 16] = (
            min(255, pal[0] + j * 4),
            min(255, pal[1] + j * 4),
            min(255, pal[2] + j * 2),
            255,
        )
        tx, ty = x // 16, y // 16
        if ground[ty][tx] in (G_GRASS, G_FORAGE):
            ground[ty][tx] = G_FENCE
            crop[ty][tx] = 0

    def fill_hill_gaps(eat_dark=True):
        n = 0
        for y in range(34, 144):
            x0 = hill_left(y) - 6
            if y >= 128:
                x0 = max(x0, 272)
            for x in range(max(x0, 256), 320):
                if in_mouth(x, y):
                    continue
                r, g, b, _a = art[y // 16][x // 16][y % 16][x % 16]
                if is_lawn((r, g, b), y) or (eat_dark and r + g + b < 50):
                    paint_rock_px(x, y)
                    n += 1
        return n

    # Hill first, then the shaft and cart on top so rocks cannot bury them.
    timber_dx, timber_dy = 280, 62
    cart_oy = timber_dy + 64
    _, _, mbpp, mrows = mines_sheet

    fill_hill_gaps()
    kinds = ((2, 2), (1, 3), (0, 3), (2, 3), (1, 2))
    k = 0
    for dy in range(36, 128, 7):
        for dx in range(hill_left(dy) - 6, 320, 7):
            # Keep row 8 west of the rails as a walkable strip to the mine.
            if dy + 16 > 128 and dx < 272:
                continue
            stx, sty = kinds[k % 5]
            blit_rock(stx, sty, dx, dy)
            k += 1
    leftover = fill_hill_gaps()
    print("hill grass gaps", leftover)

    def shaft_opaque(x, y):
        lx, ly = x - timber_dx, y - timber_dy
        if not (0 <= lx < 32 and 0 <= ly < 80):
            return False
        r, g, b, a = ip.pix(mrows, mbpp, 31 - lx, 128 + ly)
        return a >= 16 and r + g + b >= 18

    timber_hit = {}
    for y in range(80):
        for x in range(32):
            r, g, b, a = ip.pix(mrows, mbpp, 31 - x, 128 + y)
            if a < 16 or r + g + b < 18:
                continue
            X, Y = timber_dx + x, timber_dy + y
            if not (0 <= X < 320 and 0 <= Y < 208):
                continue
            tx, ty = X // 16, Y // 16
            art[ty][tx][Y % 16][X % 16] = (r, g, b, 255)
            timber_hit[(tx, ty)] = timber_hit.get((tx, ty), 0) + 1
    for (tx, ty), n in timber_hit.items():
        if n >= 10:
            ground[ty][tx] = G_FENCE
            crop[ty][tx] = 0

    ground[8][17] = G_PATH
    ground[8][18] = G_PATH
    crop[8][17] = 0
    crop[8][18] = 0

    cart_minx, cart_maxx = 16, -1
    for y in range(16):
        for x in range(16):
            r, g, b, a = ip.pix(mrows, mbpp, 2 * 16 + x, 12 * 16 + y)
            if a >= 96:
                cart_minx, cart_maxx = min(cart_minx, x), max(cart_maxx, x)
    flip_min, flip_max = 15 - cart_maxx, 15 - cart_minx
    cart_ox = timber_dx + 16 - (flip_min + flip_max + 1) // 2
    blit_over(mines_sheet, 2 * 16, 12 * 16, 16, 16, cart_ox, cart_oy, key=0, a_cut=96, flip_h=True)

    def cart_opaque(x, y):
        lx, ly = x - cart_ox, y - cart_oy
        if not (0 <= lx < 16 and 0 <= ly < 16):
            return False
        r, g, b, a = ip.pix(mrows, mbpp, 2 * 16 + (15 - lx), 12 * 16 + ly)
        return a >= 96

    # Plug lawn holes in the hill without painting over the door or cart.
    plugged = 0
    for y in range(34, 144):
        for x in range(max(hill_left(y) - 6, 256), 320):
            if y >= 128 and x < 272:
                continue
            if shaft_opaque(x, y) or cart_opaque(x, y):
                continue
            r, g, b, _a = art[y // 16][x // 16][y % 16][x % 16]
            if is_lawn((r, g, b), y):
                paint_rock_px(x, y)
                plugged += 1
    print("plugged around door", plugged)

    # Pond-to-mine lane between the water and the pasture fence.
    for x in range(12, 19):
        if ground[8][x] == G_FENCE:
            ground[8][x] = G_GRASS
            crop[8][x] = 0
    ground[8][17] = G_PATH
    ground[8][18] = G_PATH

    # 32x32 animals, two frames each, quadrants TL TR BL BR.
    def add_quad(img, fx, fy, onto_grass=True):
        ids = []
        for tile in ip.grab32(img, fx, fy):
            if onto_grass:
                tile = ip.composite(tile, grass_tile)
            ids.append(atlas.add_unique(tile, allow_clear=not onto_grass))
        return ids[0]

    # atlas is used above before it is filled with map tiles. Add map first.
    # Reorder: index the map, then animals, and patch animal cells.
    indexed = [[None for _ in range(20)] for _ in range(15)]
    art_ids = [[0 for _ in range(20)] for _ in range(15)]
    for y in range(15):
        for x in range(20):
            art_ids[y][x] = atlas.add(art[y][x], allow_clear=False)
            indexed[y][x] = atlas.tiles[art_ids[y][x]]

    pig0 = add_quad(pig, 0, 0)
    pig1 = add_quad(pig, 1, 0)
    sheep0 = add_quad(sheep, 0, 0)
    sheep1 = add_quad(sheep, 1, 0)
    cow0 = add_quad(cow, 0, 0)
    cow1 = add_quad(cow, 1, 0)
    slime0 = add_quad(slime, 0, 0)
    slime1 = add_quad(slime, 1, 0)
    chick = [atlas.add(ip.composite(ip.downscale32(chicken, i, 0), grass_tile)) for i in range(2)]
    chick += [atlas.add(ip.composite(ip.downscale32(chicken, i, 1), grass_tile)) for i in range(2)]

    def place_quad(tx, ty, base, gnd):
        for q in range(4):
            dx, dy = q & 1, q >> 1
            art_ids[ty + dy][tx + dx] = base + q
            indexed[ty + dy][tx + dx] = atlas.tiles[base + q]
            ground[ty + dy][tx + dx] = gnd

    place_quad(8, 3, cow0, G_PATH)
    place_quad(8, 6, pig0, G_FENCE)
    # Feet stay drawn, but the row in front of the pig is a walk gap.
    ground[7][8] = G_PATH
    ground[7][9] = G_PATH
    place_quad(10, 4, sheep0, G_PATH)
    place_quad(10, 6, slime0, G_PATH)
    for pos in ((0, 8), (19, 11)):
        art_ids[pos[1]][pos[0]] = chick[0]
        indexed[pos[1]][pos[0]] = atlas.tiles[chick[0]]
        ground[pos[1]][pos[0]] = G_FENCE

    player_bases = []
    for frame in range(4):
        player_bases.append(add_quad(player, frame, 0, onto_grass=False))

    dirt_rgb = soils[0][8][8]
    dirt_index = atlas.color_index(dirt_rgb[0], dirt_rgb[1], dirt_rgb[2], 255, False)
    wet_index = atlas.color_index(max(0, dirt_rgb[0] - 30), max(0, dirt_rgb[1] - 10), min(255, dirt_rgb[2] + 50), 255, False)

    named_grids = []
    for stage, tile in enumerate((soils[0], ip.shade(soils[4], 3, 4), crop_tile(0), crop_tile(1), crop_tile(2), crop_tile(3))):
        named_grids.append(atlas.tiles[atlas.add(tile)])
    named_grids.append(atlas.tiles[player_bases[0]])  # placeholder, replaced below
    # Player named tile is the top-left of frame 0, clear pixels included.
    named_grids[-1] = atlas.tiles[player_bases[0]]

    grass_art_id = atlas.add(grass_tile)
    if len(atlas.tiles) > 255:
        raise SystemExit(f"too many unique tiles: {len(atlas.tiles)}")

    start_x, start_y = 4, 8
    if ground[start_y][start_x] not in (G_GRASS, G_PATH, G_FLOOR, G_SOIL, G_TILLED, G_FORAGE):
        # The lane may have been covered. Fall back to the tile in front of the gate.
        start_x, start_y = 4, 8
        ground[start_y][start_x] = G_PATH
        art_ids[start_y][start_x] = atlas.add(path)
        indexed[start_y][start_x] = atlas.tiles[art_ids[start_y][start_x]]

    # Draw the farmer onto the preview, 32x32, feet on the start tile.
    preview = [[indexed[y][x] for x in range(20)] for y in range(15)]
    for y in range(15):
        for x in range(20):
            if crop[y][x] and ground[y][x] in (G_TILLED, G_SOIL):
                preview[y][x] = named_grids[1 + crop[y][x]]
    quads = [atlas.tiles[player_bases[0] + q] for q in range(4)]
    for q in range(4):
        dx, dy = q & 1, q >> 1
        tx, ty = start_x + dx, start_y - 1 + dy
        if not (0 <= tx < 20 and 0 <= ty < 15):
            continue
        base = [list(row) for row in preview[ty][tx]]
        src = quads[q]
        for y in range(16):
            for x in range(16):
                if src[y][x] != 0:
                    base[y][x] = src[y][x]
        preview[ty][tx] = base

    sprites = ["#pragma once\n\n#include <Arduino.h>\n#include <stdint.h>\n\n"]
    sprites.append("// Farm scene using the Cute Fantasy free pack plus the earlier 16x16 set.\n")
    sprites.append("// Index 0 is clear. Tiles are 256 bytes in flash, or loaded from the SD pack.\n\n")
    sprites.append("static constexpr uint8_t PAL_SKIP = 0;\n")
    sprites.append(f"static constexpr uint8_t PAL_TILLED = {dirt_index};\n")
    sprites.append(f"static constexpr uint8_t PAL_WET = {wet_index};\n")
    sprites.append("static constexpr int TILE_BYTES = 256;\n\n")
    sprites.append("static const uint16_t PALETTE[] PROGMEM = {\n")
    for r, g, b in atlas.order:
        sprites.append(f"    0x{ip.q565(r, g, b):04X},\n")
    sprites.append("};\n\n")
    sprites.append(f"static constexpr int ART_COUNT = {len(atlas.tiles)};\n\n")
    for i, grid in enumerate(atlas.tiles):
        sprites.append(f"static const uint8_t ART_{i}[TILE_BYTES] PROGMEM = {{\n{ip.emit_bytes(grid)}\n}};\n\n")
    sprites.append("static const uint8_t* artById(uint8_t id) {\n")
    sprites.append("    static const uint8_t* const table[ART_COUNT] = {\n")
    for i in range(len(atlas.tiles)):
        sprites.append(f"        ART_{i},\n")
    sprites.append("    };\n    if (id >= ART_COUNT) return ART_0;\n    return table[id];\n}\n\n")
    for name, grid in zip(
        ("TILE_TILLED", "TILE_WATERED", "TILE_CROP0", "TILE_CROP1", "TILE_CROP2", "TILE_CROP3", "TILE_PLAYER"),
        named_grids,
    ):
        sprites.append(f"static const uint8_t {name}[TILE_BYTES] PROGMEM = {{\n{ip.emit_bytes(grid)}\n}};\n\n")
    (ROOT / "include" / "Sprites.h").write_text("".join(sprites), encoding="utf-8")

    def rows(matrix):
        return ",\n".join("    {" + ", ".join(str(v) for v in row) + "}" for row in matrix)

    header = ["#pragma once\n\n#include <Arduino.h>\n\n#include \"Config.h\"\n\n"]
    header.append(f"static constexpr uint8_t PLAYER_START_X = {start_x};\n")
    header.append(f"static constexpr uint8_t PLAYER_START_Y = {start_y};\n")
    header.append(f"static constexpr uint8_t TILE_GRASS_ART = {grass_art_id};\n")
    header.append("// Each walk frame is four tiles: top-left, top-right, bottom-left, bottom-right.\n")
    header.append("static constexpr uint8_t PLAYER_ANIM[4] = {" + ", ".join(str(i) for i in player_bases) + "};\n")
    header.append("static constexpr uint8_t CHICKEN_ANIM[4] = {" + ", ".join(str(i) for i in chick) + "};\n")
    header.append(f"static constexpr uint8_t PIG_A = {pig0};\nstatic constexpr uint8_t PIG_B = {pig1};\n")
    header.append(f"static constexpr uint8_t SHEEP_A = {sheep0};\nstatic constexpr uint8_t SHEEP_B = {sheep1};\n")
    header.append(f"static constexpr uint8_t COW_A = {cow0};\nstatic constexpr uint8_t COW_B = {cow1};\n")
    header.append(f"static constexpr uint8_t SLIME_A = {slime0};\nstatic constexpr uint8_t SLIME_B = {slime1};\n\n")
    header.append("static const uint8_t MAP_ART[15][20] PROGMEM = {\n" + rows(art_ids) + "\n};\n\n")
    header.append("static const uint8_t MAP_GROUND[15][20] PROGMEM = {\n" + rows(ground) + "\n};\n\n")
    header.append("static const uint8_t MAP_CROP[15][20] PROGMEM = {\n" + rows(crop) + "\n};\n")
    (ROOT / "include" / "Tilemap.h").write_text("".join(header), encoding="utf-8")

    atlas_path = ROOT / "sdcard" / "sprites" / "atlas.bin"
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    with atlas_path.open("wb") as handle:
        handle.write(b"CYD1")
        handle.write(struct.pack("<HHH", len(atlas.order), len(atlas.tiles), 7))
        for r, g, b in atlas.order:
            handle.write(struct.pack("<H", ip.q565(r, g, b)))
        for grid in atlas.tiles:
            handle.write(bytes(b for row in grid for b in row))
        for grid in named_grids:
            handle.write(bytes(b for row in grid for b in row))

    ip.write_png(Path(r"C:\Users\simon\AppData\Local\Temp\cyd-farm-cute.png"), preview, atlas)

    import base64
    import zlib
    pal = atlas.order
    pix = []
    for ty in range(15):
        for sy in range(16):
            for tx in range(20):
                for sx in range(16):
                    pix.append(pal[preview[ty][tx][sy][sx]])
    farm_png = ROOT / "tools" / "_farm_preview.png"
    raw = bytearray()
    for y in range(240):
        raw.append(0)
        for x in range(320):
            raw.extend(pix[y * 320 + x])

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 240, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    farm_png.write_bytes(png)
    b64 = base64.b64encode(png).decode("ascii")
    (ROOT / "tools" / "_farm_preview.html").write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Mine entrance preview</title>
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
  <h1>Mine entrance</h1>
  <p>Rock hill on the east edge, timber mouth tucked in &middot; 320&times;240</p>
  <div class="row">
    <figure><img alt="Farm 2x" width="640" height="480" src="data:image/png;base64,{b64}"><figcaption>2&times;</figcaption></figure>
    <figure><img alt="Farm 1x" width="320" height="240" src="data:image/png;base64,{b64}"><figcaption>Actual pixels</figcaption></figure>
  </div>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )

    print(f"tiles {len(atlas.tiles)} colors {len(atlas.order)} atlas {atlas_path.stat().st_size}")
    print("player", player_bases, "chick", chick)
    print("pig", pig0, pig1, "sheep", sheep0, sheep1, "cow", cow0, cow1, "slime", slime0, slime1)


if __name__ == "__main__":
    main()
