#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>

#include <TFT_eSPI.h>
#include <XPT2046_Touchscreen.h>

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
// Touch shares VSPI with the panel. XPT2046_Touchscreen::begin() calls
// SPI.begin() with the default ESP32 pins and would disconnect the display.
// setup() puts SCLK/MISO/MOSI back on 14/12/13 immediately after that call.
// ---------------------------------------------------------------------------

extern "C" bool btStop(void);

static TFT_eSPI tft;
static TFT_eSprite spr(&tft);
static XPT2046_Touchscreen ts(PIN_TOUCH_CS, PIN_TOUCH_IRQ);
static GameState game;
static bool fullFrame = false;

static uint32_t lastMs = 0;
static uint32_t lastDrawMs = 0;
static uint32_t lastTouchMs = 0;

struct View {
    TFT_eSprite* spr;
    int originY;
    int height;
};

static constexpr uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
    return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
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
    return shade565(color, shadeNum);
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

static void blitPlayer(TFT_eSprite& dst, int x, int y, uint8_t shadeNum) {
    // Idle.png is 4 frames across the top row. Cycle them so the farmer animates.
    uint8_t frame = (uint8_t)((millis() / 180) % 4);
    const uint8_t* sprite = sceneryTile(gamePlayerFrameArt(frame));
    if (sprite == nullptr) sprite = namedTile(ASSET_PLAYER, TILE_PLAYER);
    for (int py = 0; py < TILE; ++py) {
        for (int px = 0; px < TILE; ++px) {
            uint8_t index = pgm_read_byte(sprite + py * TILE + px);
            if (index == PAL_SKIP) continue;
            dst.drawPixel(x + px, y + py, palColor(index, shadeNum));
        }
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

    int py = (int)game.playerY * TILE - v.originY;
    if (py > -TILE && py < v.height) {
        blitPlayer(*v.spr, (int)game.playerX * TILE, py, shadeNum);
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

static bool readTouch(int& sx, int& sy) {
    // Hold the panel's chip-select high so a touch transfer is ignored by
    // the ILI9341. The touch library drives its own CS. GPIO 36 is sampled
    // inside touched(); it has no internal pull-up, and the XPT2046 drives it.
    digitalWrite(PIN_TFT_CS, HIGH);
    if (!ts.touched()) {
        digitalWrite(PIN_TOUCH_CS, HIGH);
        return false;
    }
    TS_Point raw = ts.getPoint();
    digitalWrite(PIN_TOUCH_CS, HIGH);

    int ax = TOUCH_SWAP_XY ? raw.y : raw.x;
    int ay = TOUCH_SWAP_XY ? raw.x : raw.y;
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
    Serial.printf("raw %d %d -> %d %d\n", raw.x, raw.y, sx, sy);
    return true;
}

static void dispatchTouch(int sx, int sy) {
    if (sy >= HOTBAR_Y) {
        int slot = sx / (SCREEN_W / TOOL_COUNT);
        if (slot < 0) slot = 0;
        if (slot >= TOOL_COUNT) slot = TOOL_COUNT - 1;
        gameSelectTool(game, (Tool)slot);
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

    // Library begin() resets VSPI to pins 18/19/23. Restore the CYD bus.
    // Chip-select stays under software control (TFT 15, touch 33, SD 5).
    ts.begin();
    SPI.begin(PIN_TFT_SCLK, PIN_TFT_MISO, PIN_TFT_MOSI);
    digitalWrite(PIN_TOUCH_CS, HIGH);
    digitalWrite(PIN_SD_CS, HIGH);

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

    int sx = 0;
    int sy = 0;
    if ((now - lastTouchMs) >= TOUCH_DEBOUNCE_MS && readTouch(sx, sy)) {
        lastTouchMs = now;
        dispatchTouch(sx, sy);
        // Input redraw is immediate. The 15 fps cap still paces the clock.
        render();
        lastDrawMs = millis();
        return;
    }

    // A per-tile dirty mask would replace this full refresh if the map
    // grew beyond one screen. At 20x15 the SPI transfer is the limit.
    if ((now - lastDrawMs) >= FRAME_MS) {
        render();
        lastDrawMs = millis();
    }
}
