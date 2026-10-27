#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Config.h"

enum Ground : uint8_t {
    G_GRASS = 0,
    G_SOIL,
    G_TILLED,
    G_WATER,
    G_FENCE,
    G_FLOOR,
    G_BIN,
    G_BED,
    G_PATH,
    G_DOOR,
    G_FORAGE
};

enum Place : uint8_t {
    PLACE_FARM = 0,
    PLACE_HOUSE = 1,
    PLACE_MINE = 2
};

enum Tool : uint8_t {
    TOOL_HOE = 0,
    TOOL_WATER,
    TOOL_SEED,
    TOOL_HARVEST,
    TOOL_PICKAXE,
    TOOL_COUNT
};

// Four bytes per cell. 20*15*4 = 1200 bytes of map state.
struct Cell {
    uint8_t ground;
    uint8_t crop;     // 0 = empty, 1 = parsnip
    uint8_t stage;    // 0 seed .. CROP_MATURE
    uint8_t watered;  // cleared when the farmer sleeps; required for growth
};

struct GameState {
    Cell cells[MAP_H][MAP_W];
    uint8_t playerX;
    uint8_t playerY;
    Tool tool;
    uint16_t gold;
    uint8_t seeds;
    uint8_t crops;
    uint8_t eggs;
    uint8_t milk;
    uint8_t wool;
    uint8_t apples;
    uint8_t forage;
    uint8_t stone;
    uint8_t copperOre;
    uint8_t ironOre;
    uint8_t coal;
    uint8_t mineHits[MAP_H][MAP_W];  // 0 gone, 1 cracked, 2 intact
    uint8_t petted;  // bitmask, cleared when the farmer sleeps
    uint8_t stamina;
    uint16_t day;
    uint8_t hour;
    uint8_t minute;
    char toast[40];
    uint32_t toastUntilMs;
    uint32_t minuteAccumMs;
    uint32_t growAccumMs;
    bool saveDirty;
    uint8_t destX;
    uint8_t destY;
    bool hasDest;
    uint8_t place;  // PLACE_FARM, PLACE_HOUSE, or PLACE_MINE
};

void gameInit(GameState& g);
void gameUpdate(GameState& g, uint32_t dtMs, bool advanceClock);
void gameTapTile(GameState& g, uint8_t tx, uint8_t ty);
void gameFollow(GameState& g);
void gameSelectTool(GameState& g, Tool tool);
uint8_t gameArtAt(uint8_t x, uint8_t y);
uint8_t gamePlayerFrameArt(uint8_t frame);
uint8_t gameChickenFrameArt(uint8_t frame);
bool gameIsChicken(uint8_t x, uint8_t y);
uint8_t gameAnimArt(uint8_t id);
bool gameSave(const GameState& g);
bool gameLoad(GameState& g);

inline bool gameIsNight(const GameState& g) {
    return g.hour >= NIGHT_HOUR_START || g.hour < NIGHT_HOUR_END;
}
