#pragma once

#include <stdint.h>

// ---------------------------------------------------------------------------
// CYD ESP32-2432S028R pin map.
// Display and touch share VSPI. Touch uses its own chip-select only.
// GPIO 36 is input-only, which is what the XPT2046 IRQ pin needs.
// Some board revisions tie the panel reset to EN. If the screen stays white,
// set -DTFT_RST=-1 in platformio.ini and leave this constant unused.
// ---------------------------------------------------------------------------
static constexpr int PIN_TFT_CS   = 15;
static constexpr int PIN_TFT_DC   = 2;
static constexpr int PIN_TFT_RST  = 4;
static constexpr int PIN_TFT_MOSI = 13;
static constexpr int PIN_TFT_SCLK = 14;
static constexpr int PIN_TFT_MISO = 12;
static constexpr int PIN_TFT_BL   = 21;

static constexpr int PIN_TOUCH_CS   = 33;
static constexpr int PIN_TOUCH_IRQ  = 36;
// This CYD wires the touch controller on its own SPI bus, not the display bus.
static constexpr int PIN_TOUCH_CLK  = 25;
static constexpr int PIN_TOUCH_MISO = 39;
static constexpr int PIN_TOUCH_MOSI = 32;

// MicroSD shares VSPI with the display and touch. GPIO 5 is the card's
// chip-select. It must stay high during TFT and touch transfers, or the
// card answers those clocks and the picture breaks up.
static constexpr int PIN_SD_CS = 5;

static constexpr int SCREEN_W = 320;
static constexpr int SCREEN_H = 240;
static constexpr int TILE     = 16;
static constexpr int MAP_W    = 20;
static constexpr int MAP_H    = 15;

// Display rotation 1 swaps the panel axes (row/column). The touch axes follow
// that: finger left/right selects the tool, finger up/down selects the row.
// The bottom of the glass is the hotbar.
static constexpr int  TOUCH_X_MIN    = 200;
static constexpr int  TOUCH_X_MAX    = 3700;
static constexpr int  TOUCH_Y_MIN    = 240;
static constexpr int  TOUCH_Y_MAX    = 3800;
static constexpr bool TOUCH_SWAP_XY  = true;
static constexpr bool TOUCH_INVERT_X = false;
static constexpr bool TOUCH_INVERT_Y = false;

// 100 ms of real time is one game minute, so a full day lasts ~2.4 minutes.
// Watered crops advance one stage every GROW_INTERVAL_MS (mature at stage 3).
static constexpr uint32_t MS_PER_GAME_MINUTE = 100;
static constexpr uint32_t GROW_INTERVAL_MS   = 15000;
static constexpr uint32_t TOAST_MS           = 2000;
static constexpr uint32_t TOUCH_DEBOUNCE_MS  = 180;
static constexpr uint32_t FRAME_MS           = 66;  // ~15 fps cap

static constexpr uint8_t STAMINA_MAX  = 100;
static constexpr uint8_t COST_HOE     = 8;
static constexpr uint8_t COST_WATER   = 4;
static constexpr uint8_t COST_PLANT   = 2;
static constexpr uint8_t COST_HARVEST = 3;

static constexpr uint16_t PRICE_CROP = 35;
static constexpr uint16_t PRICE_SEED = 20;
static constexpr uint8_t  SEEDS_START = 10;

static constexpr uint8_t CROP_MATURE = 3;

// HUD covers the top 16 px. Hotbar is drawn at y 208..239.
// The hit row starts 8 px higher so the buttons are easier to press,
// and it stops there so the crop rows above are not treated as buttons.
static constexpr int HUD_H         = 16;
static constexpr int HOTBAR_Y      = 208;
static constexpr int HOTBAR_H      = 32;
static constexpr int HOTBAR_HIT_Y  = 200;

// Night window is 18:00 through 05:59. World pixels are scaled by NIGHT_NUM/16.
static constexpr uint8_t NIGHT_HOUR_START = 18;
static constexpr uint8_t NIGHT_HOUR_END   = 6;
static constexpr uint8_t NIGHT_NUM        = 9;  // 9/16 ~= 56%
