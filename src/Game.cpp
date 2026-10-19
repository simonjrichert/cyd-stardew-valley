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
            if (cell.crop != 0) return;
            if (cell.ground != G_GRASS && cell.ground != G_SOIL) return;
            if (!spend(g, COST_HOE)) return;
            cell.ground = G_TILLED;
            cell.watered = 0;
            break;

        case TOOL_WATER:
            if (cell.ground != G_TILLED || cell.watered) return;
            if (!spend(g, COST_WATER)) return;
            cell.watered = 1;
            break;

        case TOOL_SEED:
            if (cell.ground != G_TILLED || cell.crop != 0) return;
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
            if (cell.crop == 0 || cell.stage < CROP_MATURE) return;
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

static bool tryStep(GameState& g, int dx, int dy) {
    int nx = (int)g.playerX + dx;
    int ny = (int)g.playerY + dy;
    if (nx < 0 || ny < 0 || nx >= MAP_W || ny >= MAP_H) return false;
    if (!walkable(g.cells[ny][nx].ground)) return false;
    g.playerX = (uint8_t)nx;
    g.playerY = (uint8_t)ny;
    return true;
}

// One tile per tap. Prefer the axis with more ground left to cover so a
// diagonal target still reaches the plot without a pathfinder.
static void stepToward(GameState& g, uint8_t tx, uint8_t ty) {
    int dx = (int)tx - (int)g.playerX;
    int dy = (int)ty - (int)g.playerY;
    int sx = 0;
    int sy = 0;
    if (dx > 0) sx = 1;
    else if (dx < 0) sx = -1;
    if (dy > 0) sy = 1;
    else if (dy < 0) sy = -1;
    int ax = dx < 0 ? -dx : dx;
    int ay = dy < 0 ? -dy : dy;
    if (ax >= ay) {
        if (!tryStep(g, sx, 0)) tryStep(g, 0, sy);
    } else {
        if (!tryStep(g, 0, sy)) tryStep(g, sx, 0);
    }
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
    return gameArtAt(x, y) == CHICKEN_ANIM[0];
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
}

void gameTapTile(GameState& g, uint8_t tx, uint8_t ty) {
    if (tx >= MAP_W || ty >= MAP_H) return;

    int dx = tx > g.playerX ? tx - g.playerX : g.playerX - tx;
    int dy = ty > g.playerY ? ty - g.playerY : g.playerY - ty;
    int dist = dx > dy ? dx : dy;

    if (dist <= 1) {
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
        return;
    }

    stepToward(g, tx, ty);
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
