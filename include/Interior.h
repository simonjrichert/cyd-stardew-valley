#pragma once

#include <stdint.h>

// House interior. Tiles are RGB565 in flash. Row 12, columns 9 and 10 are the
// door back to the farm. The farmer appears on the floor tile just above it.
const uint16_t* houseTile(uint8_t x, uint8_t y);
uint8_t houseGround(uint8_t x, uint8_t y);

static constexpr uint8_t HOUSE_SPAWN_X = 9;
static constexpr uint8_t HOUSE_SPAWN_Y = 11;
static constexpr uint8_t FARM_DOOR_X0 = 3;
static constexpr uint8_t FARM_DOOR_X1 = 4;
static constexpr uint8_t FARM_DOOR_Y = 6;
static constexpr uint8_t FARM_EXIT_X = 3;
static constexpr uint8_t FARM_EXIT_Y = 7;
