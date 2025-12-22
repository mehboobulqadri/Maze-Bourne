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
    
    def __init__(self, x: float = 1, y: float = 1, max_health: int = None):
        # Position (in grid units)
        self.x = float(x)
        self.y = float(y)
        
        # Stats
        if max_health is None:
            max_health = PLAYER_HEALTH
        self.max_health = max_health
        self.health = max_health
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
        
        # Invulnerability
        self.invulnerable_timer = 0.0
        
        # Inventory
        self.keys = 0
        
        # Notification debounce
        self.last_notification_time = 0.0
        
        # Movement input buffer
        self._move_input = (0, 0)
        
        # Parry
        self.is_parrying = False
        self.parry_timer = 0.0
        self.parry_duration = 0.3  # Active parry window
        self.parry_cooldown = 0.0
        self.parry_cooldown_duration = 1.0
        
        # Hiding
        self.is_hidden = False
        self.current_hiding_spot = None
    
    def update(self, dt: float, game):
        """Update player state."""
        # Handle input
        self._handle_input(game)
        
        # Update dash
        self._update_dash(dt, game.level)
        
        # Update parry
        if self.is_parrying:
            self.parry_timer -= dt
            if self.parry_timer <= 0:
                self.is_parrying = False
                self.parry_cooldown = self.parry_cooldown_duration
        
        if self.parry_cooldown > 0:
            self.parry_cooldown -= dt
        
        # Calculate speed
        current_speed = self.speed
        if self.is_stealthed:
            current_speed *= STEALTH_SPEED_MULT
            
        # No movement while parrying (optional, but adds tactical weight)
        if self.is_parrying:
            current_speed *= 0.2
        
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
            
        # Update invulnerability
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
        
        # Update notification debounce timer
        if self.last_notification_time > 0:
            self.last_notification_time -= dt
        
        # Check for interactions
        self._check_interactions(game)

    # ... (collision check remains) ...

    def _update_dash(self, dt: float, level):
        """Update dash movement with collision check."""
        if not self.is_dashing:
            return
        
        self.dash_timer -= dt
        if self.dash_timer <= 0:
            self.is_dashing = False
            return
        
        # Move in dash direction but check collision
        dash_speed = DASH_DISTANCE / DASH_DURATION
        dx = self.dash_direction[0] * dash_speed * dt
        dy = self.dash_direction[1] * dash_speed * dt
        
        # Continuous collision detection (steps)
        # Simple step check: if next pos is wall, stop dash
        steps = 5
        for i in range(steps):
             step_x = dx / steps
             step_y = dy / steps
             
             if self._check_collision(self.x + step_x, self.y + step_y, level):
                 self.x += step_x
                 self.y += step_y
             else:
                 # Hit wall, stop dash
                 self.is_dashing = False
                 self.dash_timer = 0
                 break
    
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
        
        # Disable input if hidden
        if hasattr(self, 'is_hidden') and self.is_hidden:
            self._move_input = (0, 0)
            return

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
                self.dash(game)
                break
        
        # Parry (F key or Right Click)
        if game.is_key_just_pressed(pygame.K_f) or (hasattr(game, 'mouse_buttons') and game.mouse_buttons[2]):
             if not self.is_parrying and self.parry_cooldown <= 0:
                 self.parry(game)

    
    
    def dash(self, game):
        """Attempt to dash."""
        if self.dash_cooldown_timer > 0:
            return
        if self.energy < DASH_ENERGY_COST:
            return
        if self._move_input == (0, 0):
            return  # Need to be moving to dash
        
        # Check if dash path is immediately blocked (Don't waste energy on walls)
        dx, dy = self._move_input
        check_dist = 0.5 # Check half a tile ahead
        if not self._check_collision(self.x + dx * check_dist, self.y + dy * check_dist, game.level):
            # Blocked
            if hasattr(game, 'audio_manager'):
                game.audio_manager.play_sound("sfx_ui_hover") 
            return

        self.is_dashing = True
        self.dash_timer = DASH_DURATION
        self.dash_direction = self._move_input
        self.energy -= DASH_ENERGY_COST
        self.dash_cooldown_timer = DASH_COOLDOWN
        
        # Play sound
        if hasattr(game, 'audio_manager'):
            game.audio_manager.play_sound("sfx_dash")
    
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
            
            if hasattr(game, 'audio_manager'):
                game.audio_manager.play_sound("sfx_ui_select", 1.2)
                

        # Check for exit
        if cell.cell_type == CellType.EXIT:
            from src.core.constants import GameState
            
            if self.keys > 0:
                # Record level completion
                if hasattr(game, 'stats_tracker'):
                    level_num = getattr(game, 'current_level_num', 1)
                    stars, is_new_best_time, is_new_best_stars = game.stats_tracker.complete_level(level_num)
                    
                    # Check for new achievements
                    if hasattr(game, 'achievement_manager'):
                        stats_dict = game.stats_tracker.get_stats_dict()
                        new_achievements = game.achievement_manager.check_all(stats_dict)
                        game._new_achievements = new_achievements
                        
                        if new_achievements:
                            game.achievement_manager.save()
                    
                    # Store stats for victory screen
                    import time
                    completion_time = time.time() - game.stats_tracker.current_level_start_time
                    game._victory_stats = (stars, completion_time, is_new_best_time)
                
                if game.renderer:
                    game.renderer.add_notification("Level Complete!", COLORS.EXIT)
                if hasattr(game, 'audio_manager'):
                    game.audio_manager.play_sound("sfx_ui_select", 1.5)
                game.change_state(GameState.VICTORY)
            else:
                if self.last_notification_time <= 0:
                    if game.renderer:
                        game.renderer.add_notification("Locked! Find the Key", COLORS.UI_TEXT_DIM)
                    if hasattr(game, 'audio_manager'):
                        game.audio_manager.play_sound("sfx_ui_hover", 1.0)
                    self.last_notification_time = 2.0  # Debounce for 2 seconds
        
        # Check for trap damage
        if cell.cell_type == CellType.TRAP:
            self.take_damage(1, game)

    def parry(self, game):
        """Perform a parry action."""
        self.is_parrying = True
        self.parry_timer = self.parry_duration
        self.parry_cooldown = self.parry_cooldown_duration
        
        # Play parry sound
        if hasattr(game, 'audio_manager') and game.audio_manager:
            game.audio_manager.play_sound('parry')
    
    def enter_hiding_spot(self, hiding_spot):
        """Enter a hiding spot and become invisible to enemies."""
        if not self.is_hidden:
            self.is_hidden = True
            self.current_hiding_spot = hiding_spot
            return True
        return False
    
    def exit_hiding_spot(self):
        """Exit hiding spot and become visible again."""
        if self.is_hidden:
            self.is_hidden = False
            self.current_hiding_spot = None
            return True
        return False
    
    def take_damage(self, amount: int, game):
        """Take damage and check for death."""
        if self.invulnerable_timer > 0:
            return
        
        # Can't take damage while hidden
        if self.is_hidden:
            return
            
        self.health -= amount
        self.invulnerable_timer = 0.5  # Reduced i-frames
        
        # Record damage in stats
        if hasattr(game, 'stats_tracker'):
            game.stats_tracker.record_damage()
        
        # Record damage location for behavior tracker (endless mode)
        if hasattr(game, 'behavior_tracker') and game.behavior_tracker:
            game.behavior_tracker.record_damage((int(self.x), int(self.y)))
        
        if game.renderer:
            from src.core.constants import COLORS
            game.renderer.add_notification("Damage Taken!", COLORS.TRAP)
            game.renderer.camera.add_shake(10.0)
        
        if hasattr(game, 'audio_manager'):
            game.audio_manager.play_sound("sfx_alert", 1.0)
            
        if self.health <= 0:
            # Record death
            if hasattr(game, 'stats_tracker'):
                game.stats_tracker.record_death()
            
            # Record death location for behavior tracker (endless mode)
            if hasattr(game, 'behavior_tracker') and game.behavior_tracker:
                game.behavior_tracker.record_death((int(self.x), int(self.y)))
            
            from src.core.constants import GameState
            game.change_state(GameState.GAME_OVER)
    
    def interact(self, game):
        """Interact with nearby objects (doors, levers, hiding spots)."""
        if not game.level:
            return
        
        # First check for game object interactions
        if hasattr(game, 'game_object_manager') and game.game_object_manager:
            if game.game_object_manager.handle_interact(self, game):
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
            
            # Handle Privacy Door - no key required
            if cell.cell_type == CellType.PRIVACY_DOOR:
                if cell.is_locked:
                    # Open the privacy door
                    cell.is_locked = False
                    game.level.opened_doors.add((tx, ty))
                    if game.renderer:
                        game.renderer.add_notification("Door Opened", COLORS.DOOR_UNLOCKED)
                    if hasattr(game, 'audio_manager'):
                        game.audio_manager.play_sound("sfx_ui_select", 0.8)
                else:
                    # Close the privacy door (optional - can toggle)
                    cell.is_locked = True
                    if (tx, ty) in game.level.opened_doors:
                        game.level.opened_doors.remove((tx, ty))
                    if game.renderer:
                        game.renderer.add_notification("Door Closed", COLORS.DOOR_LOCKED)
                return
            
            # Unlock door if we have keys (regular locked doors)
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