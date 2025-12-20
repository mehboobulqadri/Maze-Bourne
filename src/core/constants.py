"""
Maze Bourne - Game Constants and Configuration
A Stealth Sci-Fi Maze Game with RL AI
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Tuple

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================
# Native Resolution - Game runs at 1280x720
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Internal Game Resolution (same as window now)
GAME_WIDTH = 1280
GAME_HEIGHT = 720

# Logic uses Game Resolution
SCREEN_WIDTH = GAME_WIDTH
SCREEN_HEIGHT = GAME_HEIGHT
TARGET_FPS = 144
WINDOW_TITLE = "Maze Bourne"

# Tile/Grid Settings
TILE_SIZE = 40  # Optimized for 720p (32x18 tiles fit)
GRID_LINE_WIDTH = 1

# Camera
CAMERA_LERP_SPEED = 8.0  # Smooth camera follow speed

# =============================================================================
# COLOR PALETTE - Sci-Fi Theme
# =============================================================================
@dataclass(frozen=True)
class Colors:
    # Background
    VOID = (10, 10, 15)
    BACKGROUND = (15, 20, 30)
    
    # Walls and Floor
    WALL = (40, 50, 70)
    WALL_HIGHLIGHT = (60, 75, 100)
    FLOOR = (25, 30, 45)
    FLOOR_PATTERN = (30, 35, 50)
    
    # Player
    PLAYER = (0, 220, 180)  # Cyan
    PLAYER_STEALTH = (0, 150, 120)  # Darker cyan when stealth
    PLAYER_DASH = (100, 255, 220)  # Bright when dashing
    
    # Enemies by type
    ENEMY_PATROL = (180, 60, 60)      # Red - patrol drones
    ENEMY_TRACKER = (200, 100, 50)     # Orange - tracker bots
    ENEMY_SOUND = (200, 180, 50)       # Yellow - sound hunters
    ENEMY_SIGHT = (150, 50, 180)       # Purple - sight guards
    ENEMY_GUARD = (150, 50, 180)       # Purple - Guard (Same as Sight)
    ENEMY_HUNTER = (200, 180, 50)      # Yellow - Hunter (Same as Sound)
    ENEMY_ALERT = (255, 100, 100)      # Bright red when alerted
    
    # Interactive Objects
    KEY = (255, 215, 0)           # Gold
    DOOR_LOCKED = (100, 80, 60)   # Brown/locked
    DOOR_UNLOCKED = (60, 120, 80) # Green/unlocked
    LEVER_OFF = (80, 80, 90)      # Gray
    LEVER_ON = (80, 200, 120)     # Green
    CAMERA_INACTIVE = (60, 70, 80)
    CAMERA_ACTIVE = (255, 80, 80)
    TRAP = (200, 50, 50)
    HIDING_SPOT = (40, 60, 80)
    EXIT = (100, 255, 150)        # Bright green
    SPAWN = (100, 200, 255)       # Light blue
    
    # UI Colors
    UI_BG = (20, 25, 35)
    UI_BORDER = (60, 80, 100)
    UI_TEXT = (220, 230, 240)
    UI_TEXT_DIM = (120, 130, 140)
    UI_HEALTH = (220, 60, 80)
    UI_ENERGY = (60, 180, 220)
    UI_STEALTH = (80, 200, 150)
    
    # Effects
    VISION_CONE = (255, 200, 100, 30)  # Semi-transparent orange
    DETECTION_FLASH = (255, 100, 100, 100)
    PARTICLE_DUST = (100, 110, 130)
    
    # Debug
    DEBUG_PATH = (0, 255, 0, 100)
    DEBUG_GRID = (50, 60, 80)

COLORS = Colors()

# =============================================================================
# PLAYER SETTINGS
# =============================================================================
PLAYER_SPEED = 5.0  # Tiles per second
PLAYER_HEALTH = 3
PLAYER_MAX_ENERGY = 100.0
PLAYER_ENERGY_REGEN = 5.0  # Slower regen (was 10.0)

# Stealth
STEALTH_VISIBILITY_MULT = 0.3  # 70% less visible
STEALTH_NOISE_MULT = 0.2       # 80% less noise
STEALTH_SPEED_MULT = 0.6       # 40% slower

# Dash ability
DASH_DISTANCE = 3  # Tiles
DASH_DURATION = 0.15  # Seconds
DASH_COOLDOWN = 2.0  # Seconds
DASH_ENERGY_COST = 40.0  # Higher cost (was 25.0)

# Noise generation
NOISE_WALK = 30
NOISE_RUN = 60
NOISE_DASH = 80
NOISE_INTERACT = 40

# =============================================================================
# ENEMY SETTINGS
# =============================================================================
class EnemyType(Enum):
    PATROL = auto()      # Fixed route patrol
    TRACKER = auto()     # Follows player trails
    SOUND_HUNTER = auto() # Responds to noise
    SIGHT_GUARD = auto()  # Vision cone detection
    RL_ADAPTIVE = auto()  # RL-powered enemy (future)

# Enemy base stats (can be overridden per enemy)
ENEMY_BASE_SPEED = 3.0
ENEMY_DETECTION_RANGE = 6.0  # Tiles
ENEMY_VISION_ANGLE = 90      # Degrees (for cone-based)
ENEMY_VISION_RANGE = 8.0     # Tiles
ENEMY_HEARING_RANGE = 10.0   # Tiles

# Behavior timing
ENEMY_PATROL_WAIT = 1.5      # Seconds at waypoints
ENEMY_ALERT_DURATION = 3.0   # Seconds
ENEMY_SEARCH_DURATION = 8.0  # Seconds
ENEMY_CHASE_TIMEOUT = 5.0    # Lose interest after X seconds

# Per-type configuration
ENEMY_CONFIG = {
    EnemyType.PATROL: {
        "speed": 2.5,
        "vision_range": 5.0,
        "vision_angle": 120,
        "hearing_range": 4.0,
        "color": COLORS.ENEMY_PATROL,
    },
    EnemyType.TRACKER: {
        "speed": 4.0,
        "vision_range": 6.0,
        "vision_angle": 360,
        "hearing_range": 6.0,
        "color": COLORS.ENEMY_TRACKER,
    },
    EnemyType.SOUND_HUNTER: {
        "speed": 3.5,
        "vision_range": 3.0,
        "vision_angle": 90,
        "hearing_range": 15.0,
        "color": COLORS.ENEMY_SOUND,
    },
    EnemyType.SIGHT_GUARD: {
        "speed": 2.0,
        "vision_range": 10.0,
        "vision_angle": 60,
        "hearing_range": 5.0,
        "color": COLORS.ENEMY_SIGHT,
    },
}

# Behavior states
class EnemyState(Enum):
    IDLE = auto()
    PATROL = auto()
    SUSPICIOUS = auto()
    ALERT = auto()
    SEARCH = auto()
    CHASE = auto()
    RETURN = auto()

# =============================================================================
# LEVEL SETTINGS
# =============================================================================
class CellType(Enum):
    VOID = 0
    WALL = 1
    FLOOR = 2
    SPAWN = 3
    EXIT = 4
    KEY = 5
    DOOR = 6
    LEVER = 7
    CAMERA = 8
    TRAP = 9
    HIDING_SPOT = 10
    ENEMY_SPAWN = 11

# Maze sizes per level difficulty
LEVEL_SIZES = {
    "tutorial": (15, 15),
    "small": (20, 20),
    "medium": (30, 30),
    "large": (40, 40),
    "endless": (25, 25),
}

# Default maze size
MAZE_WIDTH = 25
MAZE_HEIGHT = 25

# Level generation
MIN_ROOMS = 4
MAX_ROOMS = 8
MIN_ROOM_SIZE = 4
MAX_ROOM_SIZE = 8
CORRIDOR_WIDTH = 2

# =============================================================================
# GAME STATES
# =============================================================================
class GameState(Enum):
    MENU = auto()
    LEVEL_SELECT = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    LEVEL_COMPLETE = auto()
    EDITOR = auto()
    SETTINGS = auto()
    HELP = auto()
    CREDITS = auto()
    ACHIEVEMENTS = auto()

# =============================================================================
# INPUT MAPPINGS (can be customized later)
# =============================================================================
import pygame

CONTROLS = {
    "move_up": [pygame.K_w, pygame.K_UP],
    "move_down": [pygame.K_s, pygame.K_DOWN],
    "move_left": [pygame.K_a, pygame.K_LEFT],
    "move_right": [pygame.K_d, pygame.K_RIGHT],
    "stealth": [pygame.K_LSHIFT, pygame.K_RSHIFT],
    "dash": [pygame.K_SPACE],
    "interact": [pygame.K_e],
    "pause": [pygame.K_ESCAPE],
    "debug": [pygame.K_F3],
}

# =============================================================================
# REINFORCEMENT LEARNING SETTINGS
# =============================================================================
RL_CONFIG = {
    "observation_size": 11,  # Player visible radius in tiles
    "max_enemies_observed": 10,
    "max_objects_observed": 20,
    
    # Rewards
    "reward_level_complete": 100.0,
    "reward_key_collected": 5.0,
    "reward_door_opened": 3.0,
    "reward_progress": 0.1,
    "penalty_spotted": -5.0,
    "penalty_damage": -20.0,
    "penalty_death": -100.0,
    "penalty_time": -0.01,  # Per step
    
    # Training
    "max_steps_per_episode": 2000,
    "training_timesteps": 500_000,
}

# =============================================================================
# AUDIO SETTINGS (placeholders for now)
# =============================================================================
AUDIO_ENABLED = True
MASTER_VOLUME = 0.7
MUSIC_VOLUME = 0.5
SFX_VOLUME = 0.8

# =============================================================================
# DEBUG SETTINGS
# =============================================================================
DEBUG_MODE = False
SHOW_FPS = True
SHOW_GRID = False
SHOW_PATHFINDING = False
SHOW_VISION_CONES = False
SHOW_ENEMY_STATE = True