#include "Game.h"

#include "Assets.h"
#include "Interior.h"
#include "Mine.h"
#include "Tilemap.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void setToast(GameState& g, const char* msg) {
    strncpy(g.toast, msg, sizeof(g.toast) - 1);
    g.toast[sizeof(g.toast) - 1] = '\0';
    g.toastUntilMs = millis() + TOAST_MS;
}

static void markSave(GameState& g);
static uint8_t groundAt(const GameState& g, uint8_t x, uint8_t y);

static bool farmPassage(uint8_t x, uint8_t y) {
    // 4-way pathfinding cannot squeeze diagonally, so these gaps have to be
    // open or the lawn east of the house is sealed off.
    if (x == 7 && y == 7) return true;                 // house corner / pig
    if (y == 7 && (x == 8 || x == 9)) return true;     // pig / chest
    if (x == 10 && y == 9) return true;                // chest / fence
    // Cow and sheep sit on the straight line to the pond and oak. The slime
    // sits on the south approach. Walk through them; do not path around.
    if (x >= 8 && x <= 9 && y >= 3 && y <= 4) return true;    // cow
    if (x >= 10 && x <= 11 && y >= 4 && y <= 5) return true;  // sheep
    if (x >= 10 && x <= 11 && y >= 6 && y <= 7) return true;  // slime
    if (y == 8 && x >= 10 && x <= 18) return true;            // pond-to-mine lane
    return false;
}

static bool walkable(const GameState& g, uint8_t x, uint8_t y) {
    if (g.place == PLACE_MINE && g.mineHits[y][x] != 0) return false;
    uint8_t ground = groundAt(g, x, y);
    if (ground == G_GRASS || ground == G_SOIL || ground == G_TILLED ||
        ground == G_FLOOR || ground == G_PATH || ground == G_FORAGE) {
        return true;
    }
    return g.place == PLACE_FARM && farmPassage(x, y);
}

static bool isFarmDoor(uint8_t x, uint8_t y) {
    return y == FARM_DOOR_Y && x >= FARM_DOOR_X0 && x <= FARM_DOOR_X1;
}

static bool isFarmMine(uint8_t x, uint8_t y) {
    return x >= FARM_MINE_X0 && x <= FARM_MINE_X1 && y >= FARM_MINE_Y0 && y <= FARM_MINE_Y1;
}

static bool isFruitTree(uint8_t x, uint8_t y) {
    return x >= 12 && x <= 14 && y <= 4;
}

static bool indoors(const GameState& g) {
    return g.place == PLACE_HOUSE || g.place == PLACE_MINE;
}

static uint8_t groundAt(const GameState& g, uint8_t x, uint8_t y) {
    if (g.place == PLACE_HOUSE) return houseGround(x, y);
    if (g.place == PLACE_MINE) return mineGround(x, y);
    return g.cells[y][x].ground;
}

static void enterHouse(GameState& g) {
    g.place = PLACE_HOUSE;
    g.playerX = HOUSE_SPAWN_X;
    g.playerY = HOUSE_SPAWN_Y;
    g.hasDest = false;
    setToast(g, "Inside");
    if (gameSave(g)) g.saveDirty = false;
    else markSave(g);
}

static void exitHouse(GameState& g) {
    g.place = PLACE_FARM;
    g.playerX = FARM_EXIT_X;
    g.playerY = FARM_EXIT_Y;
    g.hasDest = false;
    setToast(g, "Outside");
    if (gameSave(g)) g.saveDirty = false;
    else markSave(g);
}

static void enterMine(GameState& g) {
    g.place = PLACE_MINE;
    g.playerX = MINE_SPAWN_X;
    g.playerY = MINE_SPAWN_Y;
    g.hasDest = false;
    setToast(g, "The mines");
    if (gameSave(g)) g.saveDirty = false;
    else markSave(g);
}

static void exitMine(GameState& g) {
    g.place = PLACE_FARM;
    g.playerX = FARM_MINE_EXIT_X;
    g.playerY = FARM_MINE_EXIT_Y;
    g.hasDest = false;
    setToast(g, "Outside");
    if (gameSave(g)) g.saveDirty = false;
    else markSave(g);
}

static void markSave(GameState& g) {
    g.saveDirty = true;
}

static bool spend(GameState& g, uint8_t cost) {
    if (g.stamina < cost) {
        setToast(g, "Too tired");
        return false;
    }
    g.stamina = (uint8_t)(g.stamina - cost);
    markSave(g);
    return true;
}

static void dryAll(GameState& g) {
    for (int y = 0; y < MAP_H; ++y) {
        for (int x = 0; x < MAP_W; ++x) {
            g.cells[y][x].watered = 0;
        }
    }
}

static void useTool(GameState& g, Cell& cell) {
    switch (g.tool) {
        case TOOL_HOE:
            if (cell.crop != 0) {
                setToast(g, cell.stage >= CROP_MATURE ? "Harvest it first" : "Crop is growing");
                return;
            }
            if (cell.ground == G_TILLED) {
                setToast(g, "Already tilled");
                return;
            }
            if (cell.ground != G_GRASS && cell.ground != G_SOIL) {
                setToast(g, "Can't hoe that");
                return;
            }
            if (!spend(g, COST_HOE)) return;
            cell.ground = G_TILLED;
            cell.watered = 0;
            break;

        case TOOL_WATER:
            if (cell.ground == G_GRASS || cell.ground == G_SOIL) {
                setToast(g, "Till it first");
                return;
            }
            if (cell.ground != G_TILLED) {
                setToast(g, "Can't water that");
                return;
            }
            if (cell.watered) {
                setToast(g, "Already watered");
                return;
            }
            if (!spend(g, COST_WATER)) return;
            cell.watered = 1;
            break;

        case TOOL_SEED:
            if (cell.ground != G_TILLED) {
                setToast(g, "Till it first");
                return;
            }
            if (cell.crop != 0) {
                setToast(g, "Already planted");
                return;
            }
            if (g.seeds == 0) {
                setToast(g, "No seeds");
                return;
            }
            if (!spend(g, COST_PLANT)) return;
            g.seeds--;
            cell.crop = 1;
            cell.stage = 0;
            break;

        case TOOL_HARVEST:
            if (cell.crop == 0 || cell.stage < CROP_MATURE) {
                setToast(g, "Not ready");
                return;
            }
            if (g.crops == 255) {
                setToast(g, "Pack full");
                return;
            }
            if (!spend(g, COST_HARVEST)) return;
            cell.crop = 0;
            cell.stage = 0;
            cell.watered = 0;
            cell.ground = G_TILLED;
            g.crops++;
            break;

        default:
            break;
    }
}

static void resetMineRocks(GameState& g) {
    for (int y = 0; y < MAP_H; ++y) {
        for (int x = 0; x < MAP_W; ++x) {
            g.mineHits[y][x] = mineRockKind((uint8_t)x, (uint8_t)y) ? 2 : 0;
        }
    }
    if (g.place == PLACE_MINE) g.mineHits[g.playerY][g.playerX] = 0;
}

static void useBin(GameState& g) {
    uint32_t earned = (uint32_t)g.crops * PRICE_CROP
                    + (uint32_t)g.eggs * PRICE_EGG
                    + (uint32_t)g.milk * PRICE_MILK
                    + (uint32_t)g.wool * PRICE_WOOL
                    + (uint32_t)g.apples * PRICE_APPLE
                    + (uint32_t)g.forage * PRICE_FORAGE
                    + (uint32_t)g.stone * PRICE_STONE
                    + (uint32_t)g.copperOre * PRICE_COPPER
                    + (uint32_t)g.ironOre * PRICE_IRON
                    + (uint32_t)g.coal * PRICE_COAL;
    if (earned > 0) {
        uint32_t sum = (uint32_t)g.gold + earned;
        if (sum > 65535u) sum = 65535u;
        char msg[40];
        snprintf(msg, sizeof(msg), "Sold +%luG", (unsigned long)earned);
        g.gold = (uint16_t)sum;
        g.crops = 0;
        g.eggs = 0;
        g.milk = 0;
        g.wool = 0;
        g.apples = 0;
        g.forage = 0;
        g.stone = 0;
        g.copperOre = 0;
        g.ironOre = 0;
        g.coal = 0;
        setToast(g, msg);
        markSave(g);
        return;
    }
    if (g.seeds == 255) {
        setToast(g, "Seed pack full");
        return;
    }
    if (g.gold < PRICE_SEED) {
        setToast(g, "Need 20G");
        return;
    }
    g.gold = (uint16_t)(g.gold - PRICE_SEED);
    g.seeds++;
    setToast(g, "Bought seed -20G");
    markSave(g);
}

static bool growWatered(GameState& g) {
    bool grew = false;
    for (int y = 0; y < MAP_H; ++y) {
        for (int x = 0; x < MAP_W; ++x) {
            Cell& cell = g.cells[y][x];
            if (cell.ground == G_FORAGE) continue;
            if (cell.crop && cell.watered && cell.stage < CROP_MATURE) {
                cell.stage++;
                grew = true;
            }
        }
    }
    return grew;
}

// End of the day: watered crops grow one stage, the field dries, and the
// farmer wakes at 06:00 with a full bar. The bed and midnight share this.
static void sleepMorning(GameState& g) {
    growWatered(g);
    dryAll(g);
    g.stamina = STAMINA_MAX;
    g.hour = 6;
    g.minute = 0;
    g.minuteAccumMs = 0;
    g.day++;
    g.petted = 0;
    resetMineRocks(g);
    for (int y = 0; y < MAP_H; ++y) {
        for (int x = 0; x < MAP_W; ++x) {
            uint8_t mapG = pgm_read_byte(&MAP_GROUND[y][x]);
            if (mapG != G_FORAGE) continue;
            if (g.cells[y][x].ground != G_GRASS) continue;
            g.cells[y][x].ground = G_FORAGE;
            g.cells[y][x].crop = pgm_read_byte(&MAP_CROP[y][x]);
            g.cells[y][x].stage = 0;
            g.cells[y][x].watered = 0;
        }
    }
    setToast(g, "Rested until 06:00");
    markSave(g);
}

static void useBed(GameState& g) {
    sleepMorning(g);
}

// Shortest walk around fences and the house. One tile of that path
// is taken per call. A blocked target stops on a neighboring tile instead.
static bool stepToward(GameState& g, uint8_t tx, uint8_t ty) {
    const int count = MAP_W * MAP_H;
    static uint16_t parent[MAP_W * MAP_H];
    static uint8_t qx[MAP_W * MAP_H];
    static uint8_t qy[MAP_W * MAP_H];
    memset(parent, 0, sizeof(parent));

    const bool standOn = walkable(g, tx, ty);
    const int start = (int)g.playerY * MAP_W + (int)g.playerX;
    parent[start] = 0xFFFF;
    qx[0] = g.playerX;
    qy[0] = g.playerY;
    int qh = 0;
    int qt = 1;
    int found = -1;

    while (qh < qt) {
        const int x = qx[qh];
        const int y = qy[qh];
        qh++;
        const int here = y * MAP_W + x;
        if (here != start) {
            if (standOn && x == (int)tx && y == (int)ty) {
                found = here;
                break;
            }
            if (!standOn) {
                int dx = x > (int)tx ? x - (int)tx : (int)tx - x;
                int dy = y > (int)ty ? y - (int)ty : (int)ty - y;
                int cheb = dx > dy ? dx : dy;
                if (cheb <= 1) {
                    found = here;
                    break;
                }
                if (cheb <= 2 && (groundAt(g, tx, ty) == G_BED || isFruitTree(tx, ty) || isFarmMine(tx, ty))) {
                    found = here;
                    break;
                }
            }
        }

        const int towardX = ((int)tx == x) ? 0 : ((int)tx > x ? 1 : -1);
        const int towardY = ((int)ty == y) ? 0 : ((int)ty > y ? 1 : -1);
        const int dirs[4][2] = {
            {towardX != 0 ? towardX : 1, 0},
            {0, towardY != 0 ? towardY : 1},
            {towardX != 0 ? -towardX : -1, 0},
            {0, towardY != 0 ? -towardY : -1}
        };
        for (int d = 0; d < 4; ++d) {
            const int nx = x + dirs[d][0];
            const int ny = y + dirs[d][1];
            if (dirs[d][0] == 0 && dirs[d][1] == 0) continue;
            if (nx < 0 || ny < 0 || nx >= MAP_W || ny >= MAP_H) continue;
            const int ni = ny * MAP_W + nx;
            if (parent[ni] != 0) continue;
            if (!walkable(g, (uint8_t)nx, (uint8_t)ny)) continue;
            if (!standOn && nx == (int)tx && ny == (int)ty) continue;
            parent[ni] = (uint16_t)(here + 1);
            qx[qt] = (uint8_t)nx;
            qy[qt] = (uint8_t)ny;
            qt++;
        }
    }

    if (found < 0) return false;
    int cur = found;
    for (int guard = 0; parent[cur] != 0xFFFF && (int)parent[cur] - 1 != start && guard < count; ++guard) {
        cur = (int)parent[cur] - 1;
    }
    if (parent[cur] == 0xFFFF) return false;
    g.playerX = (uint8_t)(cur % MAP_W);
    g.playerY = (uint8_t)(cur / MAP_W);
    return true;
}

uint8_t gameArtAt(uint8_t x, uint8_t y) {
    if (x >= MAP_W || y >= MAP_H) return 0;
    return pgm_read_byte(&MAP_ART[y][x]);
}

uint8_t gamePlayerFrameArt(uint8_t frame) {
    return PLAYER_ANIM[frame & 3];
}

uint8_t gameChickenFrameArt(uint8_t frame) {
    return CHICKEN_ANIM[frame & 3];
}

bool gameIsChicken(uint8_t x, uint8_t y) {
    uint8_t id = gameArtAt(x, y);
    for (uint8_t i = 0; i < 4; ++i) {
        if (id == CHICKEN_ANIM[i]) return true;
    }
    return false;
}

// 32x32 animals are stored as four tiles per frame. Swap the pair so they
// bob between the two frames in the sheet.
uint8_t gameAnimArt(uint8_t id) {
    const uint8_t bob = (uint8_t)((millis() / 280) & 1);
    const uint8_t first[4] = {PIG_A, SHEEP_A, COW_A, SLIME_A};
    const uint8_t second[4] = {PIG_B, SHEEP_B, COW_B, SLIME_B};
    for (uint8_t i = 0; i < 4; ++i) {
        if (id >= first[i] && id < first[i] + 4) {
            return (bob ? second[i] : first[i]) + (id - first[i]);
        }
        if (id >= second[i] && id < second[i] + 4) {
            return (bob ? second[i] : first[i]) + (id - second[i]);
        }
    }
    return id;
}

void gameInit(GameState& g) {
    memset(&g, 0, sizeof(g));
    for (int y = 0; y < MAP_H; ++y) {
        for (int x = 0; x < MAP_W; ++x) {
            g.cells[y][x].ground = pgm_read_byte(&MAP_GROUND[y][x]);
            uint8_t planted = pgm_read_byte(&MAP_CROP[y][x]);
            if (g.cells[y][x].ground == G_FORAGE) {
                g.cells[y][x].crop = planted;
            } else if (planted != 0) {
                g.cells[y][x].crop = 1;
                g.cells[y][x].stage = (uint8_t)(planted - 1);
                g.cells[y][x].watered = 1;
                g.cells[y][x].ground = G_TILLED;
            }
        }
    }
    g.playerX = PLAYER_START_X;
    g.playerY = PLAYER_START_Y;
    g.tool = TOOL_HOE;
    resetMineRocks(g);
    g.seeds = SEEDS_START;
    g.stamina = STAMINA_MAX;
    g.day = 1;
    g.hour = 6;
    g.minute = 0;
    setToast(g, "Hoe soil, water, plant");
}

void gameUpdate(GameState& g, uint32_t dtMs, bool advanceClock) {
    // A stalled frame (upload, breakpoint) must not fast-forward the farm.
    if (dtMs > 1000) dtMs = 1000;

    if (!advanceClock) {
        // The day is frozen, so midnight will not refill the bar. Rest here
        // instead: one point each 200 ms, empty to full in about 20 seconds.
        static uint32_t restMs = 0;
        restMs += dtMs;
        if (restMs >= 200) {
            uint32_t points = restMs / 200;
            restMs %= 200;
            if (g.stamina < STAMINA_MAX) {
                uint16_t sum = (uint16_t)g.stamina + (uint16_t)points;
                if (sum > STAMINA_MAX) sum = STAMINA_MAX;
                if ((uint8_t)sum != g.stamina) {
                    g.stamina = (uint8_t)sum;
                    markSave(g);
                }
            }
        }
    } else {
        g.minuteAccumMs += dtMs;
        while (g.minuteAccumMs >= MS_PER_GAME_MINUTE) {
            g.minuteAccumMs -= MS_PER_GAME_MINUTE;
            g.minute++;
            if (g.minute >= 60) {
                g.minute = 0;
                g.hour++;
                if (g.hour >= 24) {
                    sleepMorning(g);
                    break;
                }
            }
        }
    }

    g.growAccumMs += dtMs;
    bool grew = false;
    while (g.growAccumMs >= GROW_INTERVAL_MS) {
        g.growAccumMs -= GROW_INTERVAL_MS;
        if (growWatered(g)) grew = true;
    }
    if (grew) markSave(g);
}

void gameSelectTool(GameState& g, Tool tool) {
    if (tool >= TOOL_COUNT) return;
    g.tool = tool;
    static const char* names[TOOL_COUNT] = {"Hoe", "Water", "Seed", "Harvest", "Pickaxe"};
    setToast(g, names[tool]);
}

static int tileDist(const GameState& g, uint8_t tx, uint8_t ty) {
    int dx = tx > g.playerX ? tx - g.playerX : g.playerX - tx;
    int dy = ty > g.playerY ? ty - g.playerY : g.playerY - ty;
    return dx > dy ? dx : dy;
}

// Beds cover two rows and the pillows sit against the wall, so a tap on the
// headboard is two tiles from the walkable foot. Allow that reach indoors.
static bool closeEnoughToAct(const GameState& g, uint8_t tx, uint8_t ty) {
    int dist = tileDist(g, tx, ty);
    if (dist <= 1) return true;
    if (g.place == PLACE_HOUSE && groundAt(g, tx, ty) == G_BED && dist <= 2) return true;
    if (g.place == PLACE_FARM && isFarmMine(tx, ty) && dist <= 2) return true;
    return g.place == PLACE_FARM && isFruitTree(tx, ty) && dist <= 2;
}

static bool toolReady(const GameState& g, const Cell& cell) {
    switch (g.tool) {
        case TOOL_HOE:
            return cell.crop == 0 && (cell.ground == G_GRASS || cell.ground == G_SOIL);
        case TOOL_WATER:
            return cell.ground == G_TILLED && cell.watered == 0;
        case TOOL_SEED:
            return cell.ground == G_TILLED && cell.crop == 0 && g.seeds > 0;
        case TOOL_HARVEST:
            return cell.crop != 0 && cell.stage >= CROP_MATURE;
        default:
            return false;
    }
}

static uint8_t petBitAt(uint8_t x, uint8_t y) {
    if (x >= 8 && x <= 9 && y >= 3 && y <= 4) return 1;      // cow
    if (x >= 8 && x <= 9 && y >= 6 && y <= 7) return 2;      // pig
    if (x >= 10 && x <= 11 && y >= 4 && y <= 5) return 4;    // sheep
    if (x == 0 && y == 8) return 8;                          // chicken
    if (x == 19 && y == 11) return 16;                       // chicken
    if (isFruitTree(x, y)) return 32;                        // apple tree
    return 0;
}

static bool giveProduce(GameState& g, uint8_t& slot, const char* name) {
    if (slot == 255) {
        setToast(g, "Pack full");
        return false;
    }
    slot++;
    char msg[40];
    snprintf(msg, sizeof(msg), "%s +1", name);
    setToast(g, msg);
    return true;
}

static bool dropMine(GameState& g, uint8_t x, uint8_t y, uint8_t kind) {
    uint8_t roll = (uint8_t)((g.day * 73u + (uint16_t)x * 19u + (uint16_t)y * 29u + g.minute) % 100u);
    if (kind == ROCK_COPPER) return giveProduce(g, g.copperOre, "Copper Ore");
    if (kind == ROCK_IRON) return giveProduce(g, g.ironOre, "Iron Ore");
    if (roll < 15) return giveProduce(g, g.coal, "Coal");
    if (roll < 25) return giveProduce(g, g.copperOre, "Copper Ore");
    return giveProduce(g, g.stone, "Stone");
}

static bool tryMine(GameState& g, uint8_t tx, uint8_t ty) {
    if (g.mineHits[ty][tx] == 0) return false;
    if (g.tool != TOOL_PICKAXE) {
        setToast(g, "Need a pickaxe");
        return true;
    }
    if (!spend(g, COST_MINE)) return true;
    g.mineHits[ty][tx]--;
    if (g.mineHits[ty][tx] != 0) {
        markSave(g);
        return true;
    }
    uint8_t kind = mineRockKind(tx, ty);
    if (!dropMine(g, tx, ty, kind)) {
        g.mineHits[ty][tx] = 1;
        return true;
    }
    markSave(g);
    return true;
}

static bool petAnimal(GameState& g, uint8_t x, uint8_t y) {
    uint8_t bit = petBitAt(x, y);
    if (bit == 0) return false;
    if (g.petted & bit) {
        setToast(g, bit == 32 ? "Picked today" : "Already petted");
        return true;
    }
    if (bit == 1) {
        if (!giveProduce(g, g.milk, "Milk")) return true;
    } else if (bit == 2) {
        setToast(g, "The pig oinks");
    } else if (bit == 4) {
        if (!giveProduce(g, g.wool, "Wool")) return true;
    } else if (bit == 32) {
        if (!giveProduce(g, g.apples, "Apple")) return true;
    } else if (!giveProduce(g, g.eggs, "Egg")) {
        return true;
    }
    g.petted = (uint8_t)(g.petted | bit);
    markSave(g);
    return true;
}

static bool interactable(const GameState& g, uint8_t tx, uint8_t ty) {
    if (g.place == PLACE_FARM && isFarmDoor(tx, ty)) return true;
    if (g.place == PLACE_FARM && isFarmMine(tx, ty)) return true;
    if (g.place == PLACE_FARM && petBitAt(tx, ty) != 0) return true;
    uint8_t ground = groundAt(g, tx, ty);
    if (g.place == PLACE_FARM && ground == G_FORAGE) return true;
    if (g.place == PLACE_MINE && g.mineHits[ty][tx] != 0) return true;
    if (indoors(g) && ground == G_DOOR) return true;
    if (ground == G_BED || ground == G_BIN) return true;
    return g.place == PLACE_FARM && toolReady(g, g.cells[ty][tx]);
}

static void actOnTile(GameState& g, uint8_t tx, uint8_t ty) {
    // The outdoor door tiles are still stored as beds in old saves.
    if (g.place == PLACE_FARM && isFarmDoor(tx, ty)) {
        enterHouse(g);
        return;
    }
    if (g.place == PLACE_FARM && isFarmMine(tx, ty)) {
        enterMine(g);
        return;
    }
    uint8_t ground = groundAt(g, tx, ty);
    if (g.place == PLACE_HOUSE && ground == G_DOOR) {
        exitHouse(g);
        return;
    }
    if (g.place == PLACE_MINE && ground == G_DOOR) {
        exitMine(g);
        return;
    }
    if (g.place == PLACE_MINE) {
        tryMine(g, tx, ty);
        return;
    }
    if (ground == G_BED) {
        useBed(g);
        return;
    }
    if (indoors(g)) return;
    if (petAnimal(g, tx, ty)) return;
    Cell& cell = g.cells[ty][tx];
    if (cell.ground == G_FORAGE) {
        uint8_t kind = cell.crop;
        bool ok = false;
        if (kind == 1) ok = giveProduce(g, g.apples, "Apple");
        else if (kind == 3) ok = giveProduce(g, g.forage, "Leek");
        else if (kind == 4) ok = giveProduce(g, g.forage, "Onion");
        else ok = giveProduce(g, g.forage, "Horseradish");
        if (ok) {
            cell.ground = G_GRASS;
            cell.crop = 0;
            markSave(g);
        }
        return;
    }
    if (cell.ground == G_BIN) {
        useBin(g);
        return;
    }
    useTool(g, cell);
}

void gameTapTile(GameState& g, uint8_t tx, uint8_t ty) {
    if (tx >= MAP_W || ty >= MAP_H) return;
    // Only the ladder's foot can be reached from the floor.
    if (g.place == PLACE_MINE) {
        while (ty + 1 < MAP_H && mineGround(tx, ty) == G_DOOR && mineGround(tx, ty + 1) == G_DOOR) ty++;
    }

    if (closeEnoughToAct(g, tx, ty)) {
        if (interactable(g, tx, ty)) {
            g.hasDest = false;
            actOnTile(g, tx, ty);
            return;
        }
        if (indoors(g) && walkable(g, tx, ty)) {
            g.playerX = tx;
            g.playerY = ty;
            g.hasDest = false;
            return;
        }
        g.hasDest = false;
        if (g.place == PLACE_FARM) actOnTile(g, tx, ty);
        return;
    }

    g.destX = tx;
    g.destY = ty;
    g.hasDest = true;
}

// Keeps walking after the finger lifts, one tile per call, until the farmer
// is standing on the tapped tile. A door or the shipping bin is used on arrival.
void gameFollow(GameState& g) {
    if (!g.hasDest) return;
    if (g.destX >= MAP_W || g.destY >= MAP_H) {
        g.hasDest = false;
        return;
    }
    if (g.playerX == g.destX && g.playerY == g.destY) {
        g.hasDest = false;
        return;
    }

    if (closeEnoughToAct(g, g.destX, g.destY)) {
        if (interactable(g, g.destX, g.destY)) {
            g.hasDest = false;
            actOnTile(g, g.destX, g.destY);
            return;
        }
        if (!walkable(g, g.destX, g.destY)) {
            g.hasDest = false;
            return;
        }
    }
    if (!stepToward(g, g.destX, g.destY)) {
        g.hasDest = false;
    }
}

static const char B64_ALPHABET[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static int b64Value(char ch) {
    if (ch >= 'A' && ch <= 'Z') return ch - 'A';
    if (ch >= 'a' && ch <= 'z') return ch - 'a' + 26;
    if (ch >= '0' && ch <= '9') return ch - '0' + 52;
    if (ch == '+') return 62;
    if (ch == '/') return 63;
    return -1;
}

static size_t b64Encode(const uint8_t* src, size_t len, char* dst, size_t cap) {
    size_t out = 0;
    for (size_t i = 0; i < len; i += 3) {
        uint32_t n = ((uint32_t)src[i] << 16);
        if (i + 1 < len) n |= ((uint32_t)src[i + 1] << 8);
        if (i + 2 < len) n |= src[i + 2];
        if (out + 5 > cap) return 0;
        dst[out++] = B64_ALPHABET[(n >> 18) & 63];
        dst[out++] = B64_ALPHABET[(n >> 12) & 63];
        dst[out++] = (i + 1 < len) ? B64_ALPHABET[(n >> 6) & 63] : '=';
        dst[out++] = (i + 2 < len) ? B64_ALPHABET[n & 63] : '=';
    }
    dst[out] = '\0';
    return out;
}

static size_t b64Decode(const char* src, uint8_t* dst, size_t cap) {
    size_t out = 0;
    int val = 0;
    int bits = -8;
    for (const char* p = src; *p != '\0' && *p != '"'; ++p) {
        int d = b64Value(*p);
        if (d < 0) continue;
        val = (val << 6) + d;
        bits += 6;
        if (bits >= 0) {
            if (out >= cap) return 0;
            dst[out++] = (uint8_t)((val >> bits) & 0xFF);
            bits -= 8;
        }
    }
    return out;
}

static int jsonInt(const char* json, const char* key, int fallback) {
    char pattern[24];
    snprintf(pattern, sizeof(pattern), "\"%s\":", key);
    const char* found = strstr(json, pattern);
    if (found == nullptr) return fallback;
    return atoi(found + strlen(pattern));
}

bool gameSave(const GameState& g) {
    static char body[3072];
    char cells[1608];
    char rocks[420];
    if (b64Encode((const uint8_t*)g.cells, sizeof(g.cells), cells, sizeof(cells)) == 0) return false;
    if (b64Encode((const uint8_t*)g.mineHits, sizeof(g.mineHits), rocks, sizeof(rocks)) == 0) return false;
    int n = snprintf(
        body, sizeof(body),
        "{\"v\":1,\"day\":%u,\"hour\":%u,\"minute\":%u,\"gold\":%u,\"seeds\":%u,\"crops\":%u,"
        "\"eggs\":%u,\"milk\":%u,\"wool\":%u,\"apples\":%u,\"forage\":%u,"
        "\"stone\":%u,\"cu\":%u,\"fe\":%u,\"coal\":%u,\"pet\":%u,"
        "\"stamina\":%u,\"px\":%u,\"py\":%u,\"tool\":%u,\"in\":%u,\"cells\":\"%s\",\"rocks\":\"%s\"}",
        (unsigned)g.day, g.hour, g.minute, (unsigned)g.gold, (unsigned)g.seeds,
        (unsigned)g.crops, (unsigned)g.eggs, (unsigned)g.milk, (unsigned)g.wool,
        (unsigned)g.apples, (unsigned)g.forage, (unsigned)g.stone, (unsigned)g.copperOre,
        (unsigned)g.ironOre, (unsigned)g.coal, (unsigned)g.petted, (unsigned)g.stamina,
        g.playerX, g.playerY, (unsigned)g.tool, (unsigned)g.place, cells, rocks);
    if (n <= 0 || (size_t)n >= sizeof(body)) return false;
    return assetsWriteFile(SD_SAVE_PATH, (const uint8_t*)body, (size_t)n);
}

static bool gameLoadBody(GameState& g, char* body);

bool gameLoad(GameState& g) {
    static const char* paths[] = { SD_SAVE_PATH, "/save.json.bak", "/save.json.tmp" };
    static char body[3072];
    for (size_t i = 0; i < sizeof(paths) / sizeof(paths[0]); ++i) {
        size_t n = 0;
        if (!assetsReadFile(paths[i], (uint8_t*)body, sizeof(body) - 1, &n)) continue;
        body[n] = '\0';
        if (gameLoadBody(g, body)) {
            Serial.printf("Save loaded from %s\n", paths[i]);
            return true;
        }
    }
    return false;
}

static bool gameLoadBody(GameState& g, char* body) {
    if (jsonInt(body, "v", 0) != 1) return false;

    uint8_t decoded[sizeof(g.cells)];
    const char* cells = strstr(body, "\"cells\":\"");
    if (cells == nullptr) return false;
    cells += 9;
    if (b64Decode(cells, decoded, sizeof(decoded)) != sizeof(decoded)) return false;

    int day = jsonInt(body, "day", 1);
    int hour = jsonInt(body, "hour", 6);
    int minute = jsonInt(body, "minute", 0);
    int gold = jsonInt(body, "gold", 0);
    int seeds = jsonInt(body, "seeds", 0);
    int crops = jsonInt(body, "crops", 0);
    int eggs = jsonInt(body, "eggs", 0);
    int milk = jsonInt(body, "milk", 0);
    int wool = jsonInt(body, "wool", 0);
    int apples = jsonInt(body, "apples", 0);
    int forage = jsonInt(body, "forage", 0);
    int stone = jsonInt(body, "stone", 0);
    int copper = jsonInt(body, "cu", 0);
    int iron = jsonInt(body, "fe", 0);
    int coal = jsonInt(body, "coal", 0);
    int petted = jsonInt(body, "pet", 0);
    int stamina = jsonInt(body, "stamina", STAMINA_MAX);
    int px = jsonInt(body, "px", g.playerX);
    int py = jsonInt(body, "py", g.playerY);
    int tool = jsonInt(body, "tool", TOOL_HOE);
    int inside = jsonInt(body, "in", PLACE_FARM);
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return false;
    if (px < 0 || py < 0 || px >= MAP_W || py >= MAP_H) return false;
    if (tool < 0 || tool >= TOOL_COUNT) return false;
    if (inside != PLACE_FARM && inside != PLACE_HOUSE && inside != PLACE_MINE) return false;

    memcpy(g.cells, decoded, sizeof(g.cells));
    g.place = (uint8_t)inside;
    g.day = (uint16_t)(day < 1 ? 1 : day);
    g.hour = (uint8_t)hour;
    g.minute = (uint8_t)minute;
    g.gold = (uint16_t)(gold < 0 ? 0 : gold > 65535 ? 65535 : gold);
    g.seeds = (uint8_t)(seeds < 0 ? 0 : seeds > 255 ? 255 : seeds);
    g.crops = (uint8_t)(crops < 0 ? 0 : crops > 255 ? 255 : crops);
    g.eggs = (uint8_t)(eggs < 0 ? 0 : eggs > 255 ? 255 : eggs);
    g.milk = (uint8_t)(milk < 0 ? 0 : milk > 255 ? 255 : milk);
    g.wool = (uint8_t)(wool < 0 ? 0 : wool > 255 ? 255 : wool);
    g.apples = (uint8_t)(apples < 0 ? 0 : apples > 255 ? 255 : apples);
    g.forage = (uint8_t)(forage < 0 ? 0 : forage > 255 ? 255 : forage);
    g.stone = (uint8_t)(stone < 0 ? 0 : stone > 255 ? 255 : stone);
    g.copperOre = (uint8_t)(copper < 0 ? 0 : copper > 255 ? 255 : copper);
    g.ironOre = (uint8_t)(iron < 0 ? 0 : iron > 255 ? 255 : iron);
    g.coal = (uint8_t)(coal < 0 ? 0 : coal > 255 ? 255 : coal);
    g.petted = (uint8_t)(petted < 0 ? 0 : petted > 255 ? 255 : petted);
    uint8_t decodedRocks[sizeof(g.mineHits)];
    const char* rocks = strstr(body, "\"rocks\":\"");
    if (rocks != nullptr && b64Decode(rocks + 9, decodedRocks, sizeof(decodedRocks)) == sizeof(decodedRocks)) {
        memcpy(g.mineHits, decodedRocks, sizeof(g.mineHits));
    } else {
        resetMineRocks(g);
    }
    for (int y = 0; y < MAP_H; ++y) {
        for (int x = 0; x < MAP_W; ++x) {
            uint8_t mapG = pgm_read_byte(&MAP_GROUND[y][x]);
            uint8_t saved = g.cells[y][x].ground;
            // Layout moved: old fence on the pond-to-mine lane must not stick.
            if (saved == G_FENCE && (mapG == G_GRASS || mapG == G_PATH || mapG == G_FORAGE || mapG == G_FLOOR)) {
                g.cells[y][x].ground = mapG;
                g.cells[y][x].crop = pgm_read_byte(&MAP_CROP[y][x]);
                continue;
            }
            if (saved != G_GRASS || g.cells[y][x].crop != 0) continue;
            if (mapG == G_FORAGE) {
                g.cells[y][x].ground = G_FORAGE;
                g.cells[y][x].crop = pgm_read_byte(&MAP_CROP[y][x]);
            } else if (mapG == G_FENCE || mapG == G_WATER) {
                g.cells[y][x].ground = mapG;
            }
        }
    }
    g.stamina = (uint8_t)(stamina < 0 ? 0 : stamina > STAMINA_MAX ? STAMINA_MAX : stamina);
    if (walkable(g, (uint8_t)px, (uint8_t)py)) {
        g.playerX = (uint8_t)px;
        g.playerY = (uint8_t)py;
    } else if (g.place == PLACE_HOUSE) {
        g.playerX = HOUSE_SPAWN_X;
        g.playerY = HOUSE_SPAWN_Y;
    } else if (g.place == PLACE_MINE) {
        g.playerX = MINE_SPAWN_X;
        g.playerY = MINE_SPAWN_Y;
    }
    g.tool = (Tool)tool;
    g.saveDirty = false;
    return true;
}
