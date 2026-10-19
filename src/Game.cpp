#include "Game.h"

#include "Assets.h"
#include "Tilemap.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void setToast(GameState& g, const char* msg) {
    strncpy(g.toast, msg, sizeof(g.toast) - 1);
    g.toast[sizeof(g.toast) - 1] = '\0';
    g.toastUntilMs = millis() + TOAST_MS;
}

static bool walkable(uint8_t ground) {
    return ground == G_GRASS || ground == G_SOIL || ground == G_TILLED || ground == G_FLOOR || ground == G_PATH;
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

static void useBin(GameState& g) {
    if (g.crops > 0) {
        uint32_t earned = (uint32_t)g.crops * PRICE_CROP;
        uint32_t sum = (uint32_t)g.gold + earned;
        if (sum > 65535u) sum = 65535u;
        char msg[40];
        snprintf(msg, sizeof(msg), "Sold %u +%luG", (unsigned)g.crops, (unsigned long)earned);
        g.gold = (uint16_t)sum;
        g.crops = 0;
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

static void useBed(GameState& g) {
    g.stamina = STAMINA_MAX;
    g.hour = 6;
    g.minute = 0;
    g.day++;
    dryAll(g);
    setToast(g, "Rested until 06:00");
    markSave(g);
}

// Shortest walk around fences, water, and the house. One tile of that path
// is taken per call. A blocked target stops on a neighboring tile instead.
static bool stepToward(GameState& g, uint8_t tx, uint8_t ty) {
    const int count = MAP_W * MAP_H;
    static uint16_t parent[MAP_W * MAP_H];
    static uint8_t qx[MAP_W * MAP_H];
    static uint8_t qy[MAP_W * MAP_H];
    memset(parent, 0, sizeof(parent));

    const bool standOn = walkable(g.cells[ty][tx].ground);
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
                if ((dx > dy ? dx : dy) <= 1) {
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
            if (!walkable(g.cells[ny][nx].ground)) continue;
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
            if (planted != 0) {
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
    g.seeds = SEEDS_START;
    g.stamina = STAMINA_MAX;
    g.day = 1;
    g.hour = 6;
    g.minute = 0;
    setToast(g, "Hoe soil, water, plant");
}

void gameUpdate(GameState& g, uint32_t dtMs) {
    // A stalled frame (upload, breakpoint) must not fast-forward the farm.
    if (dtMs > 1000) dtMs = 1000;

    g.minuteAccumMs += dtMs;
    while (g.minuteAccumMs >= MS_PER_GAME_MINUTE) {
        g.minuteAccumMs -= MS_PER_GAME_MINUTE;
        g.minute++;
        if (g.minute >= 60) {
            g.minute = 0;
            g.hour++;
            if (g.hour >= 24) {
                g.hour = 0;
                g.day++;
                dryAll(g);
                markSave(g);
            }
        }
    }

    g.growAccumMs += dtMs;
    bool grew = false;
    while (g.growAccumMs >= GROW_INTERVAL_MS) {
        g.growAccumMs -= GROW_INTERVAL_MS;
        for (int y = 0; y < MAP_H; ++y) {
            for (int x = 0; x < MAP_W; ++x) {
                Cell& cell = g.cells[y][x];
                if (cell.crop && cell.watered && cell.stage < CROP_MATURE) {
                    cell.stage++;
                    grew = true;
                }
            }
        }
    }
    if (grew) markSave(g);
}

void gameSelectTool(GameState& g, Tool tool) {
    if (tool >= TOOL_COUNT) return;
    g.tool = tool;
    static const char* names[TOOL_COUNT] = {"Hoe", "Water", "Seed", "Harvest"};
    setToast(g, names[tool]);
}

static int tileDist(const GameState& g, uint8_t tx, uint8_t ty) {
    int dx = tx > g.playerX ? tx - g.playerX : g.playerX - tx;
    int dy = ty > g.playerY ? ty - g.playerY : g.playerY - ty;
    return dx > dy ? dx : dy;
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

static void actOnTile(GameState& g, uint8_t tx, uint8_t ty) {
    Cell& cell = g.cells[ty][tx];
    if (cell.ground == G_BED) {
        useBed(g);
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

    if (tileDist(g, tx, ty) <= 1) {
        g.hasDest = false;
        actOnTile(g, tx, ty);
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

    const Cell& cell = g.cells[g.destY][g.destX];
    if (tileDist(g, g.destX, g.destY) <= 1) {
        if (cell.ground == G_BED || cell.ground == G_BIN || toolReady(g, cell)) {
            g.hasDest = false;
            actOnTile(g, g.destX, g.destY);
            return;
        }
        if (!walkable(cell.ground)) {
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
    static char body[2048];
    char cells[1608];
    if (b64Encode((const uint8_t*)g.cells, sizeof(g.cells), cells, sizeof(cells)) == 0) return false;
    int n = snprintf(
        body, sizeof(body),
        "{\"v\":1,\"day\":%u,\"hour\":%u,\"minute\":%u,\"gold\":%u,\"seeds\":%u,\"crops\":%u,"
        "\"stamina\":%u,\"px\":%u,\"py\":%u,\"tool\":%u,\"cells\":\"%s\"}",
        (unsigned)g.day, g.hour, g.minute, (unsigned)g.gold, (unsigned)g.seeds,
        (unsigned)g.crops, (unsigned)g.stamina, g.playerX, g.playerY, (unsigned)g.tool, cells);
    if (n <= 0 || (size_t)n >= sizeof(body)) return false;
    return assetsWriteFile(SD_SAVE_PATH, (const uint8_t*)body, (size_t)n);
}

bool gameLoad(GameState& g) {
    static char body[2048];
    size_t n = 0;
    if (!assetsReadFile(SD_SAVE_PATH, (uint8_t*)body, sizeof(body) - 1, &n)) return false;
    body[n] = '\0';
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
    int stamina = jsonInt(body, "stamina", STAMINA_MAX);
    int px = jsonInt(body, "px", g.playerX);
    int py = jsonInt(body, "py", g.playerY);
    int tool = jsonInt(body, "tool", TOOL_HOE);
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return false;
    if (px < 0 || py < 0 || px >= MAP_W || py >= MAP_H) return false;
    if (tool < 0 || tool >= TOOL_COUNT) return false;

    memcpy(g.cells, decoded, sizeof(g.cells));
    g.day = (uint16_t)(day < 1 ? 1 : day);
    g.hour = (uint8_t)hour;
    g.minute = (uint8_t)minute;
    g.gold = (uint16_t)(gold < 0 ? 0 : gold > 65535 ? 65535 : gold);
    g.seeds = (uint8_t)(seeds < 0 ? 0 : seeds > 255 ? 255 : seeds);
    g.crops = (uint8_t)(crops < 0 ? 0 : crops > 255 ? 255 : crops);
    g.stamina = (uint8_t)(stamina < 0 ? 0 : stamina > STAMINA_MAX ? STAMINA_MAX : stamina);
    if (walkable(g.cells[py][px].ground)) {
        g.playerX = (uint8_t)px;
        g.playerY = (uint8_t)py;
    }
    g.tool = (Tool)tool;
    g.saveDirty = false;
    return true;
}
