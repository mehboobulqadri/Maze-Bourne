import pygame
import os
from src.core.constants import *
from src.levels.level import Level, CellType, Cell
from src.ui.screens import UIButton
from src.ui.theme import UITheme
from src.core.logger import get_logger

class Editor:
    def __init__(self, game):
        self.game = game
        self.level = None
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        
        # Tools
        # Tuple: (Display Name, CellType/Logic)
        self.tools = [
            ("WALL", CellType.WALL),
            ("FLOOR", CellType.FLOOR),
            ("KEY", CellType.KEY),
            ("DOOR", CellType.DOOR),
            ("EXIT", CellType.EXIT),
            ("SPAWN", CellType.SPAWN),
            ("ENEMY", CellType.ENEMY_SPAWN),
            ("TRAP", CellType.TRAP),
            ("HIDE", CellType.HIDING_SPOT)
        ]
        self.selected_tool = self.tools[0][1] # Default Wall
        
        # UI
        self.ui_buttons = []
        self._init_ui()
        
    def _init_ui(self):
        cx = SCREEN_WIDTH - 150
        y = 50
        
        # Helper to bridge action signature
        font = self.game.ui_manager.fonts['small']
        
        # Save Button
        self.ui_buttons.append(UIButton(cx, y, 120, 40, "SAVE", 
                                      self.save_level, font))
        y += 50
        
        # Exit Button
        self.ui_buttons.append(UIButton(cx, y, 120, 40, "EXIT", 
                                      lambda: self.game.change_state(GameState.MENU), font))
        y += 60
        
        # Tool Palette
        for name, tool_type in self.tools:
            # We need to capture tool_type safely in lambda
            # Using default argument for binding
            action = lambda t=tool_type: self.select_tool(t)
            btn = UIButton(cx, y, 120, 35, name, action, font)
            self.ui_buttons.append(btn)
            y += 40
            
    def select_tool(self, tool_type):
        self.selected_tool = tool_type
        if self.game.audio_manager:
            self.game.audio_manager.play_sound("sfx_ui_select", 0.6)

    def enter(self):
        get_logger().info("Entering Drag & Drop Editor")
        # Ensure we have a working level to edit
        if not self.level:
            # Load level 1 or create fresh
            try:
                self.level = Level.from_campaign(1)
            except:
                self.level = Level(25, 20)
        
        # Reset camera
        self.camera_x = 0
        self.camera_y = 0
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
        
    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        right_click = pygame.mouse.get_pressed()[2]
        
        # UI Interaction (if mouse is in side panel)
        if mouse_pos[0] > SCREEN_WIDTH - 200:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            if self.game.audio_manager:
                manager = self.game.audio_manager
            else:
                manager = None
                
            for btn in self.ui_buttons:
                # UIButton update takes (pos, click_bool)
                if btn.update(mouse_pos, mouse_click):
                     # Action handled inside button
                     pass
            return
        
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
        
        # Camera Pan (WASD)
        speed = 500 * dt
        if self.game.is_key_pressed(pygame.K_w): self.camera_y -= speed
        if self.game.is_key_pressed(pygame.K_s): self.camera_y += speed
        if self.game.is_key_pressed(pygame.K_a): self.camera_x -= speed
        if self.game.is_key_pressed(pygame.K_d): self.camera_x += speed
        
        # Paint / Erase
        # Calculate grid pos
        # sx = (grid_x * TILE_SIZE) - camera_x
        # mouse_x = screen_x
        # grid_x = (mouse_x + camera_x) / TILE_SIZE
        
        grid_x = int((mouse_pos[0] + self.camera_x) // TILE_SIZE)
        grid_y = int((mouse_pos[1] + self.camera_y) // TILE_SIZE)
        
        if 0 <= grid_x < self.level.width and 0 <= grid_y < self.level.height:
            if mouse_click:
                self._paint(grid_x, grid_y, self.selected_tool)
            elif right_click:
                self._paint(grid_x, grid_y, CellType.FLOOR) # Eraser

    def _paint(self, x, y, cell_type):
        # Update cell data
        if (x, y) not in self.level.cells:
             self.level.cells[(x, y)] = Cell(x, y, cell_type)
        else:
             self.level.cells[(x, y)].cell_type = cell_type
             
    def save_level(self):
        # Scan cells to update lists (key_positions, etc) for the Level class
        # (The Level.save_to_file usually relies on these lists being correct)
        
        self.level.key_positions = []
        self.level.door_positions = []
        self.level.trap_positions = []
        self.level.enemy_spawns = []
        
        for (x, y), cell in self.level.cells.items():
            ct = cell.cell_type
            if ct == CellType.KEY:
                self.level.key_positions.append((x, y))
            elif ct == CellType.DOOR:
                self.level.door_positions.append((x, y))
            elif ct == CellType.TRAP:
                self.level.trap_positions.append((x, y))
            elif ct == CellType.ENEMY_SPAWN:
                self.level.enemy_spawns.append((x, y))
            elif ct == CellType.SPAWN:
                self.level.spawn_point = (x, y)
            elif ct == CellType.EXIT:
                self.level.exit_point = (x, y)
        
        # Save
        filename = "levels/level_1.json" # Default for now
        self.level.save_to_file(filename)
        if self.game.renderer:
            self.game.renderer.add_notification(f"Saved to {filename}!", COLORS.EXIT)
        if self.game.audio_manager:
            self.game.audio_manager.play_sound("sfx_ui_select", 1.0)
             
    def render(self):
        self.game.screen.fill(COLORS.VOID)
        
        # Draw visible grid
        start_x = int(self.camera_x // TILE_SIZE)
        start_y = int(self.camera_y // TILE_SIZE)
        end_x = start_x + (SCREEN_WIDTH // TILE_SIZE) + 1
        end_y = start_y + (SCREEN_HEIGHT // TILE_SIZE) + 1
        
        # Offset for smooth scrolling
        off_x = -int(self.camera_x % TILE_SIZE)
        off_y = -int(self.camera_y % TILE_SIZE)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # Calculate screen pos
                sx = (x - start_x) * TILE_SIZE + off_x
                sy = (y - start_y) * TILE_SIZE + off_y
                
                # Check valid
                if 0 <= x < self.level.width and 0 <= y < self.level.height:
                    # Draw base grid
                    pygame.draw.rect(self.game.screen, (20, 20, 20), (sx, sy, TILE_SIZE, TILE_SIZE), 1)
                    
                    # Draw Content
                    cell = self.level.get_cell(x, y)
                    if cell:
                        self._draw_cell(sx, sy, cell.cell_type)
    
        # Side Panel
        panel_rect = pygame.Rect(SCREEN_WIDTH - 200, 0, 200, SCREEN_HEIGHT)
        pygame.draw.rect(self.game.screen, COLORS.UI_BG, panel_rect)
        pygame.draw.line(self.game.screen, COLORS.UI_BORDER, (SCREEN_WIDTH - 200, 0), (SCREEN_WIDTH - 200, SCREEN_HEIGHT), 2)
        
        # Title
        title = self.game.font_medium.render("EDITOR", True, COLORS.UI_TEXT)
        self.game.screen.blit(title, (SCREEN_WIDTH - 150, 10))
        
        # Selected Tool
        try:
            # Find name again
            t_name = next(name for name, t in self.tools if t == self.selected_tool)
        except:
            t_name = "UNKNOWN"
            
        sel_text = self.game.font_small.render(f"Tool: {t_name}", True, COLORS.PLAYER)
        self.game.screen.blit(sel_text, (SCREEN_WIDTH - 180, 550))
        
        for btn in self.ui_buttons:
            # Highlight selected tool button
            is_active = False
            for name, t in self.tools:
                if btn.text == name and t == self.selected_tool:
                    is_active = True
                    break
            
            if is_active:
                pygame.draw.rect(self.game.screen, COLORS.PLAYER_DASH, btn.rect.inflate(4, 4), 2, border_radius=6)
            btn.draw(self.game.screen)
            
    def _draw_cell(self, x, y, ctype):
        color = COLORS.FLOOR
        if ctype == CellType.WALL: color = COLORS.WALL
        elif ctype == CellType.KEY: color = COLORS.KEY
        elif ctype == CellType.DOOR: color = COLORS.DOOR_LOCKED
        elif ctype == CellType.EXIT: color = COLORS.EXIT
        elif ctype == CellType.SPAWN: color = COLORS.SPAWN
        elif ctype == CellType.TRAP: color = COLORS.TRAP
        elif ctype == CellType.ENEMY_SPAWN: color = COLORS.ENEMY_PATROL
        elif ctype == CellType.HIDING_SPOT: color = COLORS.HIDING_SPOT
        
        pygame.draw.rect(self.game.screen, color, (x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4))
