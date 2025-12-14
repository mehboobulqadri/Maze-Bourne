"""
Maze Bourne - Level Editor
Allows creating and editing custom levels.
"""

import pygame
import os
from enum import Enum, auto
from typing import Optional, Tuple

from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, COLORS, CellType
)
from src.levels.level import Level

class EditorTool(Enum):
    WALL = auto()
    FLOOR = auto()
    SPAWN = auto()
    EXIT = auto()
    KEY = auto()
    DOOR = auto()
    ENEMY_PATROL = auto()
    ENEMY_GUARD = auto()
    ENEMY_HUNTER = auto()
    TRAP = auto()

class Editor:
    """
    Level Editor state handler.
    """
    
    def __init__(self, game):
        self.game = game
        self.grid_width = 25
        self.grid_height = 20
        self.camera_offset = [0, 0]
        
        # Tools
        self.current_tool = EditorTool.WALL
        self.tools = list(EditorTool)
        self.tool_index = 0
        
        # UI
        self.font = game.font_small
        self.font_tiny = game.font_tiny
        
        # Current Level being edited
        self.level = None
        self.current_filename = "levels/level_1.json"
    
    def enter(self):
        """Enter editor state."""
        print("[Editor] Entering Editor Mode")
        # Try to load existing or create new
        if os.path.exists(self.current_filename):
            try:
                self.level = Level.load_from_file(self.current_filename)
                print(f"[Editor] Loaded {self.current_filename}")
            except Exception as e:
                print(f"[Editor] Error loading {self.current_filename}: {e}")
                self.level = Level(self.grid_width, self.grid_height)
        else:
            self.level = Level(self.grid_width, self.grid_height)
            # Clear maze to empty floor or walls? Walls is safer/standard
            self.level.generator._init_walls()
            # Set default spawn/exit
            self.level.cells[(1,1)].cell_type = CellType.FLOOR # Ensure spawn is floor
            
        # Ensure game renderer knows about this level
        if self.game.renderer:
            self.game.renderer.setup_for_level(self.level)
    
    def update(self, dt: float):
        """Update editor state."""
        self._handle_input(dt)
        
    def _handle_input(self, dt: float):
        """Handle mouse and keyboard interaction."""
        # Tool Selection (Scroll or Number keys)
        # 1-9 keys
        keys = pygame.key.get_pressed()
        if keys[pygame.K_1]: self.current_tool = EditorTool.WALL
        if keys[pygame.K_2]: self.current_tool = EditorTool.FLOOR
        if keys[pygame.K_3]: self.current_tool = EditorTool.SPAWN
        if keys[pygame.K_4]: self.current_tool = EditorTool.EXIT
        if keys[pygame.K_5]: self.current_tool = EditorTool.KEY
        if keys[pygame.K_6]: self.current_tool = EditorTool.DOOR
        if keys[pygame.K_7]: self.current_tool = EditorTool.ENEMY_PATROL
        if keys[pygame.K_8]: self.current_tool = EditorTool.TRAP
        
        # Mouse Interaction
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        
        # Convert screen to grid
        # Assuming no camera pan for MVP (25x20 fits 800x600 with 32px tiles? 25*32=800. Fits width perfectly. Height 20*32=640. Screen is 600? might be cut off)
        # Constants say TILE_SIZE=32? check constants. Assuming 32.
        
        gx = int(mouse_pos[0] // TILE_SIZE)
        gy = int(mouse_pos[1] // TILE_SIZE)
        
        if 0 <= gx < self.level.width and 0 <= gy < self.level.height:
            if mouse_buttons[0]: # Left Click = Place
                self._place_tile(gx, gy)
            elif mouse_buttons[2]: # Right Click = Erase (Wall)
                self._place_tile(gx, gy, is_erase=True)
                
        # Save
        if self.game.is_key_just_pressed(pygame.K_s):
            self.level.save_to_file(self.current_filename)
            if self.game.renderer:
                self.game.renderer.add_notification("Level Saved!", COLORS.UI_HEALTH)
                
        # Play Test
        if self.game.is_key_just_pressed(pygame.K_p):
            # Save then play
            self.level.save_to_file(self.current_filename)
            self.game.current_level_num = 1 # Assuming file is level_1
            self.game.reset_level_requested = True
            from src.core.constants import GameState
            self.game.change_state(GameState.PLAYING)
            
        # Return to Menu
        if self.game.is_key_just_pressed(pygame.K_ESCAPE):
            self.level.save_to_file(self.current_filename) # Auto save
            from src.core.constants import GameState
            self.game.change_state(GameState.MENU)

    def _place_tile(self, x: int, y: int, is_erase: bool = False):
        """Place current tool object at pos."""
        from src.core.constants import CellType, EnemyType
        
        cell = self.level.cells.get((x, y))
        if not cell:
            return

        if is_erase:
            cell.cell_type = CellType.WALL
            # Remove objects
            self._remove_objects_at(x, y)
            return

        # Place based on tool
        if self.current_tool == EditorTool.WALL:
            cell.cell_type = CellType.WALL
            self._remove_objects_at(x, y)
            
        elif self.current_tool == EditorTool.FLOOR:
            cell.cell_type = CellType.FLOOR
            self._remove_objects_at(x, y)
            
        elif self.current_tool == EditorTool.SPAWN:
            cell.cell_type = CellType.SPAWN
            self.level.spawn_point = (x, y)
            self.level.generator.spawn_point = (x, y)
            
        elif self.current_tool == EditorTool.EXIT:
            cell.cell_type = CellType.EXIT
            self.level.exit_point = (x, y)
            self.level.generator.exit_point = (x, y)
            
        elif self.current_tool == EditorTool.KEY:
            cell.cell_type = CellType.KEY
            if (x, y) not in self.level.key_positions:
                self.level.key_positions.append((x, y))
                
        elif self.current_tool == EditorTool.DOOR:
            cell.cell_type = CellType.DOOR
            cell.is_locked = True
            if (x, y) not in self.level.door_positions:
                self.level.door_positions.append((x, y))
                
        elif self.current_tool == EditorTool.TRAP:
            cell.cell_type = CellType.TRAP
            if (x, y) not in self.level.trap_positions:
                self.level.trap_positions.append((x, y))
                
        elif self.current_tool == EditorTool.ENEMY_PATROL:
            cell.cell_type = CellType.FLOOR
            # Add enemy spawn
            if (x, y) not in self.level.enemy_spawns:
                self.level.enemy_spawns.append((x, y))

    def _remove_objects_at(self, x, y):
        """Clear dynamic objects from cell."""
        pos = (x, y)
        if pos in self.level.key_positions: self.level.key_positions.remove(pos)
        if pos in self.level.door_positions: self.level.door_positions.remove(pos)
        if pos in self.level.trap_positions: self.level.trap_positions.remove(pos)
        if pos in self.level.enemy_spawns: self.level.enemy_spawns.remove(pos)
        
    def render(self):
        """Render editor state."""
        # Draw game world (reuse renderer)
        if self.game.renderer:
            # Force update visible tiles to see updates immediately
            if self.level:
                self.game.renderer.level = self.level
            self.game.renderer.render(self.game.screen)
        
        # UI Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, 40))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        self.game.screen.blit(overlay, (0, SCREEN_HEIGHT - 40))
        
        # Tool Text
        text = f"Tool: {self.current_tool.name} | [1-8] Tools | [Left] Place | [Right] Erase | [S]ave | [P]lay"
        surf = self.font_tiny.render(text, True, COLORS.UI_TEXT)
        self.game.screen.blit(surf, (10, SCREEN_HEIGHT - 30))
