#pragma once

#include <stdint.h>

// Mine interior. Tiles are RGB565 in flash. Column 7, rows 1-4 are the ladder
// back to the farm, on the left of the north wall. The farmer appears on the
// floor tile below its foot.
const uint16_t* mineTile(uint8_t x, uint8_t y);
uint8_t mineGround(uint8_t x, uint8_t y);

static constexpr uint8_t MINE_SPAWN_X = 7;
static constexpr uint8_t MINE_SPAWN_Y = 5;
static constexpr uint8_t FARM_MINE_X = 7;
static constexpr uint8_t FARM_MINE_Y0 = 4;
static constexpr uint8_t FARM_MINE_Y1 = 5;
static constexpr uint8_t FARM_MINE_EXIT_X = 7;
static constexpr uint8_t FARM_MINE_EXIT_Y = 6;
