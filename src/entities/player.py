"""
Basic Player implementation for testing
"""

from dataclasses import dataclass, field
from typing import Tuple
import time

from src.core.constants import (
    PLAYER_SPEED, PLAYER_HEALTH, PLAYER_MAX_ENERGY,
    STEALTH_SPEED_MULT, DASH_DISTANCE, DASH_DURATION, DASH_COOLDOWN, DASH_ENERGY_COST,
    CONTROLS
)


class Player:
    """
    Player character with movement, stealth, and dash abilities.
    """
    
    def __init__(self, x: float = 1, y: float = 1):
        # Position (in grid units)
        self.x = float(x)
        self.y = float(y)
        
        # Stats
        self.health = PLAYER_HEALTH
        self.max_health = PLAYER_HEALTH
        self.energy = PLAYER_MAX_ENERGY
        self.max_energy = PLAYER_MAX_ENERGY
        
        # Movement
        self.speed = PLAYER_SPEED
        self.facing = (0, 1)  # Direction facing (x, y)
        self.velocity = (0.0, 0.0)
        
        # Stealth
        self.is_stealthed = False
        
        # Dash
        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_cooldown_timer = 0.0
        self.dash_direction = (0, 0)
        
        # Inventory
        self.keys = 0
        
        # Movement input buffer
        self._move_input = (0, 0)
    
    def update(self, dt: float, game):
        """Update player state."""
        # Handle input
        self._handle_input(game)
        
        # Update dash
        self._update_dash(dt)
        
        # Calculate speed
        current_speed = self.speed
        if self.is_stealthed:
            current_speed *= STEALTH_SPEED_MULT
        
        # Apply movement with AABB collision
        if not self.is_dashing:
            move_x, move_y = self._move_input
            if move_x != 0 or move_y != 0:
                # Normalize diagonal movement
                if move_x != 0 and move_y != 0:
                    move_x *= 0.707
                    move_y *= 0.707
                
                # Try X movement
                new_x = self.x + move_x * current_speed * dt
                if self._check_collision(new_x, self.y, game.level):
                    self.x = new_x
                
                # Try Y movement
                new_y = self.y + move_y * current_speed * dt
                if self._check_collision(self.x, new_y, game.level):
                    self.y = new_y
                
                # Update facing direction
                if move_x != 0 or move_y != 0:
                    self.facing = (move_x, move_y)
        
        # Regenerate energy
        if self.energy < self.max_energy:
            self.energy = min(self.max_energy, self.energy + 10.0 * dt)
        
        # Update dash cooldown
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= dt
        
        # Check for interactions
        self._check_interactions(game)

    def _check_collision(self, x: float, y: float, level) -> bool:
        """
        Check if the player's bounding box at (x, y) is valid.
        Player size is approx 0.6x0.6 tiles.
        """
        if not level:
            return True
            
        # Player bounding box (relative to position x,y)
        # Position x,y is the top-left of the tile if we treated it as integer,
        # but here it's continuous.
        # Let's assume (x,y) is the top-left of the player sprite.
        # Actually in renderer: player drawn at x*TILE_SIZE + padding.
        # So (x,y) is top-left of the tile unit.
        # Let's define the collision box relative to (x,y).
        
        margin = 0.2
        size = 0.6
        
        # Check 4 corners
        corners = [
            (x + margin, y + margin),           # Top-Left
            (x + margin + size, y + margin),    # Top-Right
            (x + margin, y + margin + size),    # Bottom-Left
            (x + margin + size, y + margin + size) # Bottom-Right
        ]
        
        for cx, cy in corners:
            # Get tile coordinate
            tx, ty = int(cx), int(cy)
            if not level.is_walkable(tx, ty):
                return False
        
        return True

    def _handle_input(self, game):
        """Process input for movement and abilities."""
        import pygame
        
        # Movement
        move_x = 0
        move_y = 0
        
        for key in CONTROLS["move_up"]:
            if game.is_key_pressed(key):
                move_y = -1
                break
        for key in CONTROLS["move_down"]:
            if game.is_key_pressed(key):
                move_y = 1
                break
        for key in CONTROLS["move_left"]:
            if game.is_key_pressed(key):
                move_x = -1
                break
        for key in CONTROLS["move_right"]:
            if game.is_key_pressed(key):
                move_x = 1
                break
        
        self._move_input = (move_x, move_y)
        
        # Stealth toggle
        stealth_held = False
        for key in CONTROLS["stealth"]:
            if game.is_key_pressed(key):
                stealth_held = True
                break
        self.is_stealthed = stealth_held
        
        # Dash
        for key in CONTROLS["dash"]:
            if game.is_key_just_pressed(key):
                self._try_dash()
                break

    
    def _try_dash(self):
        """Attempt to dash."""
        if self.dash_cooldown_timer > 0:
            return
        if self.energy < DASH_ENERGY_COST:
            return
        if self._move_input == (0, 0):
            return  # Need to be moving to dash
        
        self.is_dashing = True
        self.dash_timer = DASH_DURATION
        self.dash_direction = self._move_input
        self.energy -= DASH_ENERGY_COST
        self.dash_cooldown_timer = DASH_COOLDOWN
    
    def _update_dash(self, dt: float):
        """Update dash movement."""
        if not self.is_dashing:
            return
        
        self.dash_timer -= dt
        if self.dash_timer <= 0:
            self.is_dashing = False
            return
        
        # Move in dash direction
        dash_speed = DASH_DISTANCE / DASH_DURATION
        self.x += self.dash_direction[0] * dash_speed * dt
        self.y += self.dash_direction[1] * dash_speed * dt
    
    def _check_interactions(self, game):
        """Check for and handle interactions with objects."""
        if not game.level:
            return
        
        # Check current cell (center of player)
        cx, cy = int(self.x + 0.3), int(self.y + 0.3)
        cell = game.level.get_cell(cx, cy)
        
        if not cell:
            return
        
        from src.core.constants import CellType, COLORS
        
        # Auto-pickup keys
        if cell.cell_type == CellType.KEY:
            self.keys += 1
            game.level.collect_key(cx, cy)
            if game.renderer:
                game.renderer.add_notification("Key Collected!", COLORS.KEY)
        
        # Check for exit
        if cell.cell_type == CellType.EXIT:
            from src.core.constants import GameState
            if game.renderer:
                game.renderer.add_notification("Level Complete!", COLORS.EXIT)
            game.change_state(GameState.VICTORY)
        
        # Check for trap damage
        if cell.cell_type == CellType.TRAP:
            self.take_damage(1, game)
    
    def take_damage(self, amount: int, game):
        """Take damage and check for death."""
        self.health -= amount
        if game.renderer:
            from src.core.constants import COLORS
            game.renderer.add_notification("Damage Taken!", COLORS.TRAP)
            game.renderer.camera.add_shake(10.0)
            
        if self.health <= 0:
            from src.core.constants import GameState
            game.change_state(GameState.GAME_OVER)
    
    def interact(self, game):
        """Interact with nearby objects (doors, levers)."""
        if not game.level:
            return
        
        # Check adjacent cells
        cx, cy = int(self.x + 0.3), int(self.y + 0.3)
        for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
            # Check interaction target
            tx, ty = cx + dx, cy + dy
            cell = game.level.get_cell(tx, ty)
            
            if not cell:
                continue
            
            from src.core.constants import CellType, COLORS
            
            # Unlock door if we have keys
            if cell.cell_type == CellType.DOOR:
                if cell.is_locked:
                    if self.keys > 0:
                        self.keys -= 1
                        game.level.open_door(tx, ty)
                        if game.renderer:
                            game.renderer.add_notification("Door Unlocked", COLORS.DOOR_UNLOCKED)
                    else:
                        if game.renderer:
                            game.renderer.add_notification("Locked! Need Key", COLORS.UI_TEXT_DIM)
                else:
                    # Maybe toggle door open/close?
                    pass
                return