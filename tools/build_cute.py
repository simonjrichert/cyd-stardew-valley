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
    art = [[grass_tile for _ in range(20)] for _ in range(15)]
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
    for i, pos in enumerate(((0, 3), (8, 3), (10, 4), (15, 6), (19, 8))):
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
    place_quad(15, 7, slime0, G_PATH)
    for pos in ((0, 8), (19, 4)):
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

    start_x, start_y = 4, 8
    if ground[start_y][start_x] not in (G_GRASS, G_PATH, G_FLOOR, G_SOIL, G_TILLED):
        # The lane may have been covered. Fall back to the tile in front of the gate.
        start_x, start_y = 4, 8
        ground[start_y][start_x] = G_PATH
        art_ids[start_y][start_x] = atlas.add(path)
        indexed[start_y][start_x] = atlas.tiles[art_ids[start_y][start_x]]

    # Draw the farmer onto the preview, 32x32, feet on the start tile.
    preview = [[indexed[y][x] for x in range(20)] for y in range(15)]
    for y in range(15):
        for x in range(20):
            if crop[y][x]:
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
    print(f"tiles {len(atlas.tiles)} colors {len(atlas.order)} atlas {atlas_path.stat().st_size}")
    print("player", player_bases, "chick", chick)
    print("pig", pig0, pig1, "sheep", sheep0, sheep1, "cow", cow0, cow1, "slime", slime0, slime1)


if __name__ == "__main__":
    main()
