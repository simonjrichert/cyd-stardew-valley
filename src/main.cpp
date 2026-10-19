#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>

#include <TFT_eSPI.h>

#include "Assets.h"
#include "Config.h"
#include "Game.h"
#include "Sprites.h"

#include <stdio.h>
#include <string.h>

// ---------------------------------------------------------------------------
// CYD farm
//
// The ILI9341 has no framebuffer we can draw into safely, so every frame is
// assembled offscreen and pushed in one SPI burst (or one burst per tile
// row if the full frame does not fit). A second 320x240 buffer would be
// another 150 KB and does not fit in internal SRAM, so there is exactly one
// TFT_eSprite. pushSprite() is the frame flip.
//
// Tiles are 4-bit indexed bitmaps in flash. They are expanded to RGB565 only
// for the tile currently being drawn (512 bytes on the stack). Night is a
// channel scale at expand time, not a fullscreen alpha pass.
//
// The touch chip is on HSPI (clock 25, data out 32, data in 39, select 33).
// Reading it on the display bus never saw a finger.
// ---------------------------------------------------------------------------

extern "C" bool btStop(void);

static TFT_eSPI tft;
static TFT_eSprite spr(&tft);
static SPIClass touchSpi(HSPI);
static GameState game;
static bool fullFrame = false;

static uint32_t lastMs = 0;
static uint32_t lastDrawMs = 0;
static uint32_t nextStepMs = 0;
static uint32_t lastHitMs = 0;
static bool fingerDown = false;
static bool seenHit = false;
static int holdX = 0;
static int holdY = 0;

struct View {
    TFT_eSprite* spr;
    int originY;
    int height;
};

// The ILI9341 wants the high byte first. The sprite stores little-endian
// values and pushSprite does not swap them, so green was drawn as brown
// and then looked cyan once inversion was turned on.
static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
    uint16_t color = (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
    return (uint16_t)((color << 8) | (color >> 8));
}

static inline uint16_t swap565(uint16_t color) {
    return (uint16_t)((color << 8) | (color >> 8));
}

static const char* const TOOL_LABELS[TOOL_COUNT] = {
    "HOE", "WATER", "SEED", "HARVEST"
};

static void radioOff() {
    // Radios are stopped before the framebuffer allocation so their DMA
    // buffers are not sitting in the middle of DRAM. This sketch never
    // starts Wi-Fi again.
    WiFi.mode(WIFI_OFF);
    btStop();
}

static uint16_t shade565(uint16_t color, uint8_t num) {
    // Daytime passes pixels through. Night is a multiply, not a second buffer.
    if (num >= 16) return color;
    uint16_t r = ((color >> 11) & 0x1F) * num / 16;
    uint16_t g = ((color >> 5) & 0x3F) * num / 16;
    uint16_t b = (color & 0x1F) * num / 16;
    return (uint16_t)((r << 11) | (g << 5) | b);
}

static uint16_t palColor(uint8_t index, uint8_t shadeNum) {
    // pgm_read_word on this chip is a plain load, so a RAM palette from the
    // SD card and the flash fallback share one call.
    uint16_t color = assetsReady() ? assetPalette(index) : pgm_read_word(&PALETTE[index]);
    return swap565(shade565(color, shadeNum));
}

static const uint8_t* sceneryTile(uint8_t id) {
    const uint8_t* fromCard = assetArt(id);
    return fromCard != nullptr ? fromCard : artById(id);
}

static const uint8_t* namedTile(uint8_t slot, const uint8_t* flashTile) {
    const uint8_t* fromCard = assetNamed(slot);
    return fromCard != nullptr ? fromCard : flashTile;
}

static const uint8_t* tileFor(const Cell& cell, int tx, int ty) {
    if (cell.crop) {
        const uint8_t* crops[] = {
            namedTile(ASSET_CROP0, TILE_CROP0),
            namedTile(ASSET_CROP1, TILE_CROP1),
            namedTile(ASSET_CROP2, TILE_CROP2),
            namedTile(ASSET_CROP3, TILE_CROP3),
        };
        uint8_t stage = cell.stage > 3 ? 3 : cell.stage;
        return crops[stage];
    }
    if (cell.ground == G_TILLED) {
        return cell.watered ? namedTile(ASSET_WATERED, TILE_WATERED) : namedTile(ASSET_TILLED, TILE_TILLED);
    }
    uint8_t id = gameArtAt((uint8_t)tx, (uint8_t)ty);
    if (gameIsChicken((uint8_t)tx, (uint8_t)ty)) {
        id = gameChickenFrameArt((uint8_t)((millis() / 160) % 4));
    } else {
        id = gameAnimArt(id);
    }
    return sceneryTile(id);
}

// One byte per pixel. A watered crop recolors tilled soil to the wet index
// so the plot looks damp without a second crop atlas.
static void blitOpaque(TFT_eSprite& dst, int x, int y, const uint8_t* packed,
                       uint8_t shadeNum, bool wet) {
    uint16_t buf[256];
    for (int i = 0; i < TILE_BYTES; ++i) {
        uint8_t index = pgm_read_byte(packed + i);
        if (wet && index == PAL_TILLED) index = PAL_WET;
        buf[i] = palColor(index, shadeNum);
    }
    // Values are numeric RGB565. Swapping bytes here would swap red and blue.
    dst.pushImage(x, y, TILE, TILE, buf);
}

static void blitTransparent(TFT_eSprite& dst, int x, int y, const uint8_t* sprite, uint8_t shadeNum) {
    for (int py = 0; py < TILE; ++py) {
        for (int px = 0; px < TILE; ++px) {
            uint8_t index = pgm_read_byte(sprite + py * TILE + px);
            if (index == PAL_SKIP) continue;
            dst.drawPixel(x + px, y + py, palColor(index, shadeNum));
        }
    }
}

static void blitPlayer(TFT_eSprite& dst, int originY, uint8_t shadeNum) {
    // Walk cycle from the Cute Fantasy sheet. Each frame is 32x32, four
    // tiles, with the feet sitting on the player's tile.
    uint8_t base = gamePlayerFrameArt((uint8_t)((millis() / 160) % 4));
    int ox = (int)game.playerX * TILE;
    int oy = (int)game.playerY * TILE - TILE - originY;
    for (int q = 0; q < 4; ++q) {
        int dx = (q & 1) * TILE;
        int dy = (q >> 1) * TILE;
        blitTransparent(dst, ox + dx, oy + dy, sceneryTile((uint8_t)(base + q)), shadeNum);
    }
}

static void fillScreenRect(const View& v, int x, int y, int w, int h, uint16_t color) {
    if (w <= 0 || h <= 0) return;
    if (x < 0) {
        w += x;
        x = 0;
    }
    if (x >= SCREEN_W) return;
    if (x + w > SCREEN_W) w = SCREEN_W - x;

    int y0 = y - v.originY;
    if (y0 < 0) {
        h += y0;
        y0 = 0;
    }
    if (y0 >= v.height) return;
    if (y0 + h > v.height) h = v.height - y0;
    if (w <= 0 || h <= 0) return;
    v.spr->fillRect(x, y0, w, h, color);
}

static void textAt(const View& v, int x, int y, uint16_t color, const char* text) {
    // Glyphs are 8 px tall. Skip a line that would be sliced by a strip edge.
    if (y < v.originY || y + 8 > v.originY + v.height) return;
    v.spr->setTextColor(color);
    v.spr->setTextSize(1);
    v.spr->setCursor(x, y - v.originY);
    v.spr->print(text);
}

static void drawWorld(const View& v, uint8_t shadeNum) {
    int y0 = v.originY / TILE;
    int y1 = (v.originY + v.height - 1) / TILE;
    if (y0 < 0) y0 = 0;
    if (y1 >= MAP_H) y1 = MAP_H - 1;

    for (int ty = y0; ty <= y1; ++ty) {
        int sy = ty * TILE - v.originY;
        for (int tx = 0; tx < MAP_W; ++tx) {
            const Cell& cell = game.cells[ty][tx];
            blitOpaque(*v.spr, tx * TILE, sy, tileFor(cell, tx, ty), shadeNum, cell.crop && cell.watered);
        }
    }

    int top = (int)game.playerY * TILE - TILE;
    int bottom = (int)game.playerY * TILE + TILE;
    if (bottom > v.originY && top < v.originY + v.height) {
        blitPlayer(*v.spr, v.originY, shadeNum);
    }
}

static void drawHud(const View& v) {
    const uint16_t gold = rgb565(236, 196, 56);
    const uint16_t cream = rgb565(248, 236, 210);
    fillScreenRect(v, 0, 0, SCREEN_W, HUD_H, rgb565(62, 40, 22));
    fillScreenRect(v, 0, HUD_H - 1, SCREEN_W, 1, gold);

    char line[24];
    snprintf(line, sizeof(line), "D%u %02u:%02u", (unsigned)game.day, game.hour, game.minute);
    textAt(v, 2, 4, cream, line);

    snprintf(line, sizeof(line), "%uG", (unsigned)game.gold);
    textAt(v, 78, 4, gold, line);

    snprintf(line, sizeof(line), "S%u", (unsigned)game.seeds);
    textAt(v, 132, 4, cream, line);

    snprintf(line, sizeof(line), "C%u", (unsigned)game.crops);
    textAt(v, 168, 4, cream, line);

    const int bx = 210;
    const int bw = 106;
    fillScreenRect(v, bx, 4, bw, 8, rgb565(8, 8, 8));
    int inner = (bw - 2) * game.stamina / STAMINA_MAX;
    uint16_t staminaColor = rgb565(200, 56, 40);
    if (game.stamina > 50) staminaColor = rgb565(72, 180, 64);
    else if (game.stamina > 20) staminaColor = rgb565(220, 180, 48);
    if (inner > 0) fillScreenRect(v, bx + 1, 5, inner, 6, staminaColor);
}

static void drawHotbar(const View& v) {
    const uint16_t gold = rgb565(236, 196, 56);
    for (int i = 0; i < TOOL_COUNT; ++i) {
        int x = i * (SCREEN_W / TOOL_COUNT);
        int w = SCREEN_W / TOOL_COUNT;
        bool selected = ((int)game.tool == i);
        fillScreenRect(v, x, HOTBAR_Y, w, HOTBAR_H, selected ? rgb565(148, 96, 48) : rgb565(92, 58, 28));
        if (selected) {
            fillScreenRect(v, x, HOTBAR_Y, w, 2, gold);
            fillScreenRect(v, x, HOTBAR_Y + HOTBAR_H - 2, w, 2, gold);
            fillScreenRect(v, x, HOTBAR_Y, 2, HOTBAR_H, gold);
            fillScreenRect(v, x + w - 2, HOTBAR_Y, 2, HOTBAR_H, gold);
        }

        const char* label = TOOL_LABELS[i];
        int labelX = x + (w - (int)strlen(label) * 6) / 2;
        textAt(v, labelX, HOTBAR_Y + 6, rgb565(248, 236, 210), label);

        char sub[8];
        sub[0] = '\0';
        if (i == TOOL_SEED) snprintf(sub, sizeof(sub), "x%u", (unsigned)game.seeds);
        if (i == TOOL_HARVEST) snprintf(sub, sizeof(sub), "x%u", (unsigned)game.crops);
        if (sub[0] != '\0') {
            int subX = x + (w - (int)strlen(sub) * 6) / 2;
            textAt(v, subX, HOTBAR_Y + 16, gold, sub);
        }
    }
}

static void drawToast(const View& v) {
    if (game.toast[0] == '\0' || millis() > game.toastUntilMs) return;
    int chars = (int)strlen(game.toast);
    int w = chars * 6 + 8;
    int x = (SCREEN_W - w) / 2;
    const int y = 178;
    fillScreenRect(v, x, y, w, 12, rgb565(48, 32, 18));
    textAt(v, x + 4, y + 2, rgb565(248, 236, 210), game.toast);
}

static void render() {
    uint8_t shadeNum = gameIsNight(game) ? NIGHT_NUM : 16;
    View view;
    view.spr = &spr;

    if (fullFrame) {
        view.originY = 0;
        view.height = SCREEN_H;
        // Tiles cover every pixel, so the 150 KB clear is skipped on purpose.
        drawWorld(view, shadeNum);
        drawHud(view);
        drawHotbar(view);
        drawToast(view);
        spr.pushSprite(0, 0);
        return;
    }

    // 10 KB strip. Each push is one tile row, top to bottom, so a row is
    // never shown half-drawn. HUD and hotbar are clipped into the rows
    // they overlap and are not night-shaded.
    view.height = TILE;
    for (int row = 0; row < MAP_H; ++row) {
        view.originY = row * TILE;
        spr.fillSprite(TFT_BLACK);
        drawWorld(view, shadeNum);
        drawHud(view);
        drawHotbar(view);
        drawToast(view);
        spr.pushSprite(0, view.originY);
    }
}

// Chip-select stays low for the whole conversion. Pulsing it between bytes
// was powering the controller down and dropping most taps.
static uint16_t xptRead(uint8_t command) {
    touchSpi.transfer(command);
    uint16_t hi = touchSpi.transfer(0);
    uint16_t lo = touchSpi.transfer(0);
    return (uint16_t)(((hi << 8) | lo) >> 3);
}

static bool closestPair(int a, int b, int c, int& avg) {
    int ab = a > b ? a - b : b - a;
    int ac = a > c ? a - c : c - a;
    int bc = b > c ? b - c : c - b;
    const int limit = 160;
    if (ab <= ac && ab <= bc) {
        if (ab > limit) return false;
        avg = (a + b) / 2;
        return true;
    }
    if (ac <= ab && ac <= bc) {
        if (ac > limit) return false;
        avg = (a + c) / 2;
        return true;
    }
    if (bc > limit) return false;
    avg = (b + c) / 2;
    return true;
}

static bool readTouch(int& sx, int& sy) {
    digitalWrite(PIN_TFT_CS, HIGH);
    digitalWrite(PIN_SD_CS, HIGH);

    touchSpi.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));
    digitalWrite(PIN_TOUCH_CS, LOW);
    delayMicroseconds(8);

    // 0xB1 / 0xC1 / 0xD1 / 0x91 keep the ADC awake (PD0 = 1). The first
    // conversion after idle is discarded.
    (void)xptRead(0xB1);
    uint16_t z1 = xptRead(0xB1);
    uint16_t z2 = xptRead(0xC1);
    int pressure = (int)z1 + 4095 - (int)z2;
    bool pressed = pressure > 80 && pressure < 5000;
    if (!pressed) {
        (void)xptRead(0x90);
        digitalWrite(PIN_TOUCH_CS, HIGH);
        touchSpi.endTransaction();
        return false;
    }

    int xs[3];
    int ys[3];
    (void)xptRead(0xD1);
    for (int i = 0; i < 3; ++i) {
        xs[i] = xptRead(0xD1);
        ys[i] = xptRead(0x91);
    }
    (void)xptRead(0x90);
    digitalWrite(PIN_TOUCH_CS, HIGH);
    touchSpi.endTransaction();

    int axAvg = 0;
    int ayAvg = 0;
    if (!closestPair(xs[0], xs[1], xs[2], axAvg)) return false;
    if (!closestPair(ys[0], ys[1], ys[2], ayAvg)) return false;
    if (axAvg < 80 || axAvg > 4080 || ayAvg < 80 || ayAvg > 4080) return false;

    int ax = TOUCH_SWAP_XY ? ayAvg : axAvg;
    int ay = TOUCH_SWAP_XY ? axAvg : ayAvg;
    long mx = map((long)ax, TOUCH_X_MIN, TOUCH_X_MAX, 0L, (long)SCREEN_W);
    long my = map((long)ay, TOUCH_Y_MIN, TOUCH_Y_MAX, 0L, (long)SCREEN_H);
    if (TOUCH_INVERT_X) mx = (SCREEN_W - 1) - mx;
    if (TOUCH_INVERT_Y) my = (SCREEN_H - 1) - my;
    if (mx < 0) mx = 0;
    if (my < 0) my = 0;
    if (mx >= SCREEN_W) mx = SCREEN_W - 1;
    if (my >= SCREEN_H) my = SCREEN_H - 1;
    sx = (int)mx;
    sy = (int)my;
    return true;
}

static void dispatchTouch(int sx, int sy, bool freshPress) {
    if (sy >= HOTBAR_HIT_Y) {
        int slot = sx / (SCREEN_W / TOOL_COUNT);
        if (slot < 0) slot = 0;
        if (slot >= TOOL_COUNT) slot = TOOL_COUNT - 1;
        static int heldSlot = -1;
        if (freshPress) heldSlot = -1;
        game.hasDest = false;
        if (slot != heldSlot) {
            heldSlot = slot;
            gameSelectTool(game, (Tool)slot);
        }
        return;
    }
    if (sy < HUD_H) return;

    int tx = sx / TILE;
    int ty = sy / TILE;
    if (tx < 0 || ty < 0 || tx >= MAP_W || ty >= MAP_H) return;
    gameTapTile(game, (uint8_t)tx, (uint8_t)ty);
}

static void setupSprite() {
    Serial.printf("Heap before sprite: free %u, largest %u\n",
                  (unsigned)ESP.getFreeHeap(),
                  (unsigned)ESP.getMaxAllocHeap());

    spr.setColorDepth(16);
    spr.setSwapBytes(false);
    spr.setTextWrap(false);

    void* buf = spr.createSprite(SCREEN_W, SCREEN_H);
    if (buf != nullptr) {
        fullFrame = true;
    } else {
        spr.deleteSprite();
        buf = spr.createSprite(SCREEN_W, TILE);
        fullFrame = false;
    }

    Serial.printf("Sprite %s, free %u, largest %u\n",
                  buf == nullptr ? "FAILED" : (fullFrame ? "320x240" : "320x16 strip"),
                  (unsigned)ESP.getFreeHeap(),
                  (unsigned)ESP.getMaxAllocHeap());

    if (buf == nullptr) {
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
        tft.setCursor(4, 8);
        tft.print("Sprite alloc failed");
        while (true) delay(1000);
    }
}

void setup() {
    Serial.begin(115200);
    delay(50);
    radioOff();

    pinMode(PIN_TFT_BL, OUTPUT);
    digitalWrite(PIN_TFT_BL, HIGH);
    pinMode(PIN_TOUCH_CS, OUTPUT);
    digitalWrite(PIN_TOUCH_CS, HIGH);
    pinMode(PIN_SD_CS, OUTPUT);
    digitalWrite(PIN_SD_CS, HIGH);

    tft.init();
    tft.setRotation(1);
    tft.fillScreen(TFT_BLACK);

    // Display stays on VSPI. Touch uses its own clock and data pins.
    // CS is toggled by hand, so the SPI driver must not own that pin.
    SPI.begin(PIN_TFT_SCLK, PIN_TFT_MISO, PIN_TFT_MOSI);
    touchSpi.begin(PIN_TOUCH_CLK, PIN_TOUCH_MISO, PIN_TOUCH_MOSI, -1);
    digitalWrite(PIN_TOUCH_CS, HIGH);
    digitalWrite(PIN_SD_CS, HIGH);
    digitalWrite(PIN_TFT_CS, HIGH);

    setupSprite();
    gameInit(game);
    // The framebuffer is allocated first so the 150 KB block stays contiguous.
    // Sprite bytes from the card are a smaller malloc after that.
    const char* sdNote = nullptr;
    switch (assetsBegin()) {
        case ASSET_NO_CARD: sdNote = "No SD card"; break;
        case ASSET_NO_PACK: sdNote = "No /sprites/atlas.bin"; break;
        case ASSET_BAD_PACK: sdNote = "Bad atlas.bin"; break;
        case ASSET_OK:
            if (gameLoad(game)) sdNote = "Save loaded";
            break;
    }
    if (sdNote != nullptr) {
        strncpy(game.toast, sdNote, sizeof(game.toast) - 1);
        game.toast[sizeof(game.toast) - 1] = '\0';
        game.toastUntilMs = millis() + TOAST_MS;
    }
    lastMs = millis();
    lastDrawMs = lastMs;
}

void loop() {
    uint32_t now = millis();
    uint32_t dt = now - lastMs;
    lastMs = now;
    gameUpdate(game, dt);

    // Writes are throttled. The card select is raised again before the
    // display refresh inside assetsWriteFile.
    static uint32_t lastSaveMs = 0;
    if (game.saveDirty && (now - lastSaveMs) >= 5000) {
        lastSaveMs = now;
        if (gameSave(game)) game.saveDirty = false;
    }

    static uint32_t lastPollMs = 0;
    static bool sampleReady = false;
    if ((now - lastPollMs) >= 12) {
        lastPollMs = now;
        int sx = 0;
        int sy = 0;
        if (readTouch(sx, sy)) {
            seenHit = true;
            sampleReady = true;
            lastHitMs = now;
            if (fingerDown &&
                (sx > holdX ? sx - holdX : holdX - sx) <= 12 &&
                (sy > holdY ? sy - holdY : holdY - sy) <= 12) {
                sx = holdX;
                sy = holdY;
            } else {
                holdX = sx;
                holdY = sy;
            }
        }
    }

    // Held across a frame redraw. The full-screen push takes longer than one sample.
    // Tools fire on the press only. A finger that stays down keeps steering the walk.
    bool down = seenHit && (now - lastHitMs) < 220;
    if (down && !fingerDown) {
        fingerDown = true;
        sampleReady = false;
        Serial.printf("touch %d %d\n", holdX, holdY);
        dispatchTouch(holdX, holdY, true);
        if (game.hasDest) gameFollow(game);
        nextStepMs = now + TOUCH_DEBOUNCE_MS;
        render();
        lastDrawMs = millis();
    } else if (down && sampleReady && now >= nextStepMs) {
        sampleReady = false;
        nextStepMs = now + TOUCH_DEBOUNCE_MS;
        if (holdY >= HOTBAR_HIT_Y) {
            dispatchTouch(holdX, holdY, false);
        } else if (holdY >= HUD_H) {
            int tx = holdX / TILE;
            int ty = holdY / TILE;
            int dx = tx > game.playerX ? tx - game.playerX : game.playerX - tx;
            int dy = ty > game.playerY ? ty - game.playerY : game.playerY - ty;
            if (tx >= 0 && ty >= 0 && tx < MAP_W && ty < MAP_H && (dx > 1 || dy > 1)) {
                gameTapTile(game, (uint8_t)tx, (uint8_t)ty);
                if (game.hasDest) gameFollow(game);
            }
        }
        render();
        lastDrawMs = millis();
    } else if (!down) {
        fingerDown = false;
        sampleReady = false;
        if (game.hasDest && now >= nextStepMs) {
            gameFollow(game);
            nextStepMs = now + TOUCH_DEBOUNCE_MS;
            render();
            lastDrawMs = millis();
        }
    }

    // A per-tile dirty mask would replace this full refresh if the map
    // grew beyond one screen. At 20x15 the SPI transfer is the limit.
    if ((now - lastDrawMs) >= FRAME_MS) {
        render();
        lastDrawMs = millis();
    }
}
