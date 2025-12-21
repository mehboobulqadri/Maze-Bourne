"""
Maze Bourne - Enemy AI System
Implements 4 enemy types with behavior state machines
"""

import random
import math
import time
from enum import Enum, auto
from typing import Optional, Tuple, List
from dataclasses import dataclass

from src.core.constants import (
    EnemyType, EnemyState, ENEMY_CONFIG, TILE_SIZE,
    ENEMY_PATROL_WAIT, ENEMY_ALERT_DURATION, ENEMY_SEARCH_DURATION, ENEMY_CHASE_TIMEOUT,
    CellType
)
from src.utils.grid import GridPos


class Enemy:
    """
    Base enemy class with behavior state machine.
    
    Enemy Types:
    - PATROL: Fixed route patrol, predictable
    - TRACKER: Follows player trails/footprints
    - SOUND_HUNTER: Excellent hearing, poor vision
    - SIGHT_GUARD: Long vision cone, slow
    """
    
    def __init__(self, x: float, y: float, enemy_type: EnemyType = EnemyType.PATROL, config_overrides: Optional[dict] = None):
        # Position
        self.pos = GridPos(x, y)
        self.spawn_pos = GridPos(x, y)
        
        # Type and config
        self.enemy_type = enemy_type
        self.config = ENEMY_CONFIG.get(enemy_type, ENEMY_CONFIG[EnemyType.PATROL])
        
        # Apply Config Overrides (from Director)
        if config_overrides:
            # We don't overwrite self.config directly to keep defaults pure, 
            # but we update the instance stats
            pass

        # Stats from config (with overrides)
        self.speed = config_overrides.get("speed_mult", 1.0) * self.config["speed"] if config_overrides else self.config["speed"]
        self.vision_range = self.config["vision_range"]
        self.vision_angle = self.config["vision_angle"]
        self.hearing_range = config_overrides.get("hearing_mult", 1.0) * self.config["hearing_range"] if config_overrides else self.config["hearing_range"]
        self.color = self.config["color"]
        
        # Active AI Modifiers (Behavioral flags)
        self.ai_modifiers = set()
        if config_overrides and "modifiers" in config_overrides:
             self.ai_modifiers = config_overrides["modifiers"]
        
        # State machine
        self.state = EnemyState.IDLE
        self.state_timer = 0.0
        self.state_duration = 0.0
        
        # Movement
        self.facing_direction = GridPos(0, 1)
        self.move_timer = 0.0
        self.move_cooldown = 0.3
        
        # Patrol
        self.patrol_points: List[GridPos] = []
        self.patrol_index = 0
        self.patrol_wait_timer = 0.0
        
        # Detection
        self.last_known_player_pos: Optional[GridPos] = None
        self.detection_level = 0.0
        self.lost_player_timer = 0.0
        self.attack_cooldown = 0.0
        
        # For sound hunters
        self.last_heard_sound_pos: Optional[GridPos] = None
        
        # Status
        self.is_alive = True
        self.health = 1
        
        # Pathfinding
        self.pathfinder = None
        self.current_path: List[GridPos] = []
        self.path_update_timer = 0.0
        self.path_update_interval = 0.5
        
        # Generate initial patrol route
        self._generate_patrol_route()
        
        # Adaptive AI (for endless mode) - initialized lazily
        self._adaptive_initialized = False
        self.checked_hiding_spots = set()
        self.assigned_search_zone = None
    
    # ... (existing methods)

    def update(self, dt: float, game):
        """Update enemy state."""
        if not self.is_alive:
            return
        
        player = game.player
        level = game.level
        
         # Timers
        self.move_timer += dt
        self.state_timer += dt
        self.attack_cooldown = max(0, self.attack_cooldown - dt)
        self.path_update_timer += dt
        
        # Get dynamic settings
        speed_mult = 1.0
        vision_mult = 1.0
        smartness = 1.0
        
        if hasattr(game, 'settings_manager'):
            speed_mult = game.settings_manager.get("gameplay", "enemy_speed_multiplier") or 1.0
            smartness = game.settings_manager.get("gameplay", "enemy_smartness") or 1.0
            
        # Apply multipliers
        self.current_speed = self.speed * speed_mult
        self.current_vision_range = self.vision_range * vision_mult
        self.current_smartness = smartness

    
    def _generate_patrol_route(self):
        """Generate patrol waypoints around spawn position."""
        # This will be called again in update once we have level access
        # For now just set the spawn as the single point
        self.patrol_points = [self.spawn_pos]
        self._patrol_generated = False
        
    def _generate_valid_patrol(self, level):
        """Find valid floor tiles for patrol."""
        valid_points = []
        start_x, start_y = int(self.spawn_pos.x), int(self.spawn_pos.y)
        
        # Check area around spawn
        radius = 4
        for y in range(start_y - radius, start_y + radius + 1):
            for x in range(start_x - radius, start_x + radius + 1):
                if level.is_walkable(x, y):
                    # Ensure reachable (line of sight check for simple patrol)
                    # Or just simple distance
                    valid_points.append(GridPos(x, y))
        
        import random
        if len(valid_points) > 3:
            self.patrol_points = random.sample(valid_points, min(4, len(valid_points)))
        else:
            self.patrol_points = valid_points
        
        self.patrol_index = 0
        self._patrol_generated = True
    
    def update(self, dt: float, game):
        """Update enemy AI."""
        if not self.is_alive:
            return
        
        # Update state timer
        self.state_timer += dt
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        
        # Update movement timer
        self.move_timer += dt
        
        # Get player reference
        player = game.player
        level = game.level
        
        if not player or not level:
            return
        
        # Generate patrol route if needed
        if not getattr(self, '_patrol_generated', False):
            self._generate_valid_patrol(level)
        
        # Initialize pathfinder if needed
        if self.pathfinder is None and level:
            from src.ai.pathfinding import AStarPathfinder
            self.pathfinder = AStarPathfinder(level.cells)
            
        # Store game reference for later use
        self._game = game
        
        # Update path timer
        self.path_update_timer += dt
        
        # Get dynamic settings
        speed_mult = 1.0
        vision_mult = 1.0
        smartness = 1.0
        
        if hasattr(game, 'settings_manager'):
            speed_mult = game.settings_manager.get("gameplay", "enemy_speed_multiplier") or 1.0
            # Vision multiplier - maybe not expose directly but derive from difficulty?
            # For now stick to speed and smartness as primary toggles
            smartness = game.settings_manager.get("gameplay", "enemy_smartness") or 1.0
            
        # Apply multipliers
        self.current_speed = self.speed * speed_mult
        self.current_vision_range = self.vision_range * vision_mult
        self.current_smartness = smartness
        
        # Update move cooldown based on speed (tiles per second -> seconds per tile)
        self.move_cooldown = 1.0 / max(0.1, self.current_speed)
        
        # Run behavior based on current state
        if self.state == EnemyState.IDLE:
            self._update_idle(dt, player, level)
        elif self.state == EnemyState.PATROL:
            self._update_patrol(dt, player, level)
        elif self.state == EnemyState.SUSPICIOUS:
            self._update_suspicious(dt, player, level)
        elif self.state == EnemyState.ALERT:
            self._update_alert(dt, player, level)
        elif self.state == EnemyState.SEARCH:
            self._update_search(dt, player, level)
        elif self.state == EnemyState.CHASE:
            self._update_chase(dt, player, level)
        elif self.state == EnemyState.RETURN:
            self._update_return(dt, player, level)
    
    def _change_state(self, new_state: EnemyState, duration: float = 0.0):
        """Change to a new behavior state."""
        self.state = new_state
        self.state_timer = 0.0
        
        # Smartness affects duration
        # Smarter enemies search longer, alert quicker (though alert duration is fixed transition usually)
        if new_state == EnemyState.SEARCH:
            # Base duration * smartness
            smartness = getattr(self, 'current_smartness', 1.0)
            duration *= smartness
            
        self.state_duration = duration
    
    def _can_move(self) -> bool:
        """Check if movement cooldown has passed."""
        return self.move_timer >= self.move_cooldown
    
    def _reset_move_timer(self):
        """Reset movement cooldown."""
        self.move_timer = 0.0
    
    def _move_toward(self, target: GridPos, level) -> bool:
        """Move one step toward target position. Returns True if moved."""
        if not self._can_move():
            return False
        
        dx = target.x - self.pos.x
        dy = target.y - self.pos.y
        
        # Normalize to single step
        step_x = 0
        step_y = 0
        if abs(dx) > 0.1:
            step_x = 1 if dx > 0 else -1
        if abs(dy) > 0.1:
            step_y = 1 if dy > 0 else -1
        
        # Try to move
        new_x = self.pos.x + step_x
        new_y = self.pos.y + step_y
        
        # Check walkability (and avoid HIDING SPOTS)
        cell = level.get_cell(int(new_x), int(new_y))
        
        can_move_diag = True
        if step_x != 0 and step_y != 0:
            # Prevent corner cutting: Require at least one cardinal neighbor to be walkable
            c1 = level.is_walkable(int(self.pos.x + step_x), int(self.pos.y))
            c2 = level.is_walkable(int(self.pos.x), int(self.pos.y + step_y))
            if not c1 and not c2:
                can_move_diag = False

        if can_move_diag and level.is_walkable(int(new_x), int(new_y)) and (not cell or cell.cell_type != CellType.HIDING_SPOT):
            self.pos.x = new_x
            self.pos.y = new_y
            self.facing_direction = GridPos(step_x, step_y)
            self._reset_move_timer()
            return True
        
        # Try horizontal only
        cell_x = level.get_cell(int(self.pos.x + step_x), int(self.pos.y))
        if step_x != 0 and level.is_walkable(int(self.pos.x + step_x), int(self.pos.y)) and (not cell_x or cell_x.cell_type != CellType.HIDING_SPOT):
            self.pos.x += step_x
            self.facing_direction = GridPos(step_x, 0)
            self._reset_move_timer()
            return True
        
        # Try vertical only
        cell_y = level.get_cell(int(self.pos.x), int(self.pos.y + step_y))
        if step_y != 0 and level.is_walkable(int(self.pos.x), int(self.pos.y + step_y)) and (not cell_y or cell_y.cell_type != CellType.HIDING_SPOT):
            self.pos.y += step_y
            self.facing_direction = GridPos(0, step_y)
            self._reset_move_timer()
            return True
        
        return False
    
    def _move_along_path(self, level) -> bool:
        """Move along precalculated A* path. Returns True if moved."""
        if not self._can_move() or not self.current_path:
            return False
        
        # Find next waypoint in path
        current_grid_pos = GridPos(int(self.pos.x), int(self.pos.y))
        
        # Check if we've reached current target
        if self.current_path and current_grid_pos == self.current_path[0]:
            self.current_path.pop(0)
        
        if not self.current_path:
            return False
        
        # Move toward next point in path
        next_pos = self.current_path[0]
        return self._move_toward(next_pos, level)
    
    def _update_pathfinding(self, target: GridPos, use_pathfinding: bool = True):
        """Update A* path to target if needed."""
        if not use_pathfinding or not self.pathfinder:
            self.current_path = []
            return
        
        # Check if we need to recalculate
        if self.path_update_timer < self.path_update_interval:
            return
        
        self.path_update_timer = 0.0
        
        # Calculate new path
        start = GridPos(int(self.pos.x), int(self.pos.y))
        goal = GridPos(int(target.x), int(target.y))
        
        self.current_path = self.pathfinder.find_path(start, goal, max_distance=30)
    
    def _can_see_player(self, player, level) -> bool:
        """Check if enemy can see the player."""
        # Hidden players are invisible
        if getattr(player, 'is_hidden', False):
            return False
        
        player_pos = GridPos(player.x, player.y)
        distance = self.pos.distance_to(player_pos)
        
        # Check range
        if distance > self.vision_range:
            return False
        
        # Check if player is stealthed (reduces visibility)
        if getattr(player, 'is_stealthed', False):
            if distance > self.vision_range * 0.5:
                return False
        
        # Check vision angle (for non-360 vision)
        if self.vision_angle < 360:
            # Calculate angle to player
            dx = player.x - self.pos.x
            dy = player.y - self.pos.y
            angle_to_player = math.degrees(math.atan2(dy, dx))
            
            # Calculate facing angle
            facing_angle = math.degrees(math.atan2(
                self.facing_direction.y, 
                self.facing_direction.x
            ))
            
            # Check if within vision cone
            angle_diff = abs(angle_to_player - facing_angle)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            if angle_diff > self.vision_angle / 2:
                return False
        
        # Line of sight check (High resolution raycast)
        # Check every 0.2 tiles to ensure we don't skip corners
        steps = max(1, int(distance * 5))
        for i in range(1, steps):
            t = i / steps
            check_x = self.pos.x + (player.x - self.pos.x) * t
            check_y = self.pos.y + (player.y - self.pos.y) * t
            
            # Check the tile this point is in
            if not level.is_walkable(int(check_x), int(check_y)):
                return False
        
        return True
    
    def _can_hear_player(self, player) -> bool:
        """Check if enemy can hear the player (for sound hunters)."""
        player_pos = GridPos(player.x, player.y)
        distance = self.pos.distance_to(player_pos)
        
        # Check hearing range
        if distance > self.hearing_range:
            return False
        
        # Stealth reduces noise
        if getattr(player, 'is_stealthed', False):
            if distance > self.hearing_range * 0.3:
                return False
        
        # Moving players make more noise
        move_input = getattr(player, '_move_input', (0, 0))
        if move_input == (0, 0):
            # Stationary player is very quiet
            if distance > self.hearing_range * 0.2:
                return False
        
        return True
    
    # =========================================================================
    # STATE UPDATE METHODS
    # =========================================================================
    
    def _update_idle(self, dt: float, player, level):
        """Idle state - standing still, checking for player."""
        # Check for player detection
        if self._can_see_player(player, level):
            self.last_known_player_pos = GridPos(player.x, player.y)
            self._change_state(EnemyState.ALERT, ENEMY_ALERT_DURATION)
            return
        
        # Sound hunters check for sounds
        if self.enemy_type == EnemyType.SOUND_HUNTER:
            if self._can_hear_player(player):
                self.last_heard_sound_pos = GridPos(player.x, player.y)
                self._change_state(EnemyState.SUSPICIOUS, 2.0)
                return
        
        # Transition to patrol after a moment
        if self.state_timer > 1.0:
            self._change_state(EnemyState.PATROL)
    
    def _update_patrol(self, dt: float, player, level):
        """Patrol state - follow waypoints."""
        # Check for player
        if self._can_see_player(player, level):
            self.last_known_player_pos = GridPos(player.x, player.y)
            self._change_state(EnemyState.CHASE)
            return
        
        # Sound hunters
        if self.enemy_type == EnemyType.SOUND_HUNTER:
            if self._can_hear_player(player):
                self.last_heard_sound_pos = GridPos(player.x, player.y)
                self._change_state(EnemyState.SUSPICIOUS, 2.0)
                return
        
        # Handle patrol wait
        if self.patrol_wait_timer > 0:
            self.patrol_wait_timer -= dt
            return
        
        # Get current waypoint
        if not self.patrol_points:
            return
        
        target = self.patrol_points[self.patrol_index]
        
        # Check if reached waypoint
        if self.pos.distance_to(target) < 0.5:
            # Move to next waypoint
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            self.patrol_wait_timer = ENEMY_PATROL_WAIT
            return
        
        # Move toward waypoint
        self._move_toward(target, level)
    
    def _update_suspicious(self, dt: float, player, level):
        """Suspicious state - investigating a sound or partial sighting."""
        # Check for full detection
        if self._can_see_player(player, level):
            self.last_known_player_pos = GridPos(player.x, player.y)
            self._change_state(EnemyState.CHASE)
            return
        
        # Move toward suspicious location
        target = self.last_heard_sound_pos or self.last_known_player_pos
        if target:
            if self.pos.distance_to(target) > 0.5:
                self._move_toward(target, level)
            else:
                # Reached location, look around
                if self.state_timer > self.state_duration:
                    self._change_state(EnemyState.PATROL)
        else:
            # No target, return to patrol
            self._change_state(EnemyState.PATROL)
    
    def _update_alert(self, dt: float, player, level):
        """Alert state - player spotted, preparing to chase."""
        # Immediate transition to chase
        if self._can_see_player(player, level):
            self.last_known_player_pos = GridPos(player.x, player.y)
        
        # Short alert then chase
        # Reaction time based on smartness (Default 0.5s)
        # Smartness 2.0 -> 0.25s
        # Smartness 0.5 -> 1.0s
        reaction_time = 0.5 / max(0.1, getattr(self, 'current_smartness', 1.0))
        
        if self.state_timer > reaction_time:
            self._change_state(EnemyState.CHASE)
    
    def _update_search(self, dt: float, player, level):
        """Search state - looking for player at last known location."""
        # Check for player
        if self._can_see_player(player, level):
            self.last_known_player_pos = GridPos(player.x, player.y)
            self._change_state(EnemyState.CHASE)
            return
        
        # Get game reference for adaptive behaviors
        game = getattr(self, '_game', None)
        
        # In endless mode, use adaptive search if available
        if game and game.game_mode == "endless" and hasattr(game, 'behavior_tracker') and game.behavior_tracker:
            adaptive_target = self._get_adaptive_search_target(game)
            if adaptive_target:
                target_pos = GridPos(adaptive_target[0], adaptive_target[1])
                if self.pos.distance_to(target_pos) > 0.5:
                    self._update_pathfinding(target_pos, use_pathfinding=True)
                    if self.current_path:
                        self._move_along_path(level)
                    else:
                        self._move_toward(target_pos, level)
                    return
        
        # Move toward last known position
        if self.last_known_player_pos:
            if self.pos.distance_to(self.last_known_player_pos) > 0.5:
                # Use pathfinding for search if smart enough
                smartness = getattr(self, 'current_smartness', 1.0)
                use_pathfinding = (self.enemy_type == EnemyType.TRACKER or smartness >= 1.5)
                
                if use_pathfinding and self.pathfinder:
                    self._update_pathfinding(self.last_known_player_pos, use_pathfinding=True)
                    if self.current_path:
                        self._move_along_path(level)
                    else:
                        self._move_toward(self.last_known_player_pos, level)
                else:
                    self._move_toward(self.last_known_player_pos, level)
            else:
                # At location, search around
                if self.state_timer > self.state_duration:
                    self._change_state(EnemyState.RETURN)
        else:
            self._change_state(EnemyState.RETURN)
    
    def _get_adaptive_search_target(self, game):
        """
        Get next search target based on player behavior patterns.
        Checks favorite hiding spots first, then hot zones.
        """
        if not hasattr(game, 'behavior_tracker') or not game.behavior_tracker:
            return None
        
        tracker = game.behavior_tracker
        current_pos = (int(self.pos.x), int(self.pos.y))
        
        # Get likely hiding spots
        hiding_spots = tracker.get_likely_hiding_spots(top_n=5)
        unchecked_spots = [s for s in hiding_spots if s not in self.checked_hiding_spots]
        
        if unchecked_spots and random.random() < 0.7:  # 70% chance to check hiding spots
            # Prioritize closest unchecked spot
            target = min(unchecked_spots, 
                        key=lambda s: abs(s[0] - current_pos[0]) + abs(s[1] - current_pos[1]))
            self.checked_hiding_spots.add(target)
            return target
        
        # Get hot zones (frequently visited)
        hot_zones = tracker.get_hot_zones(min_visits=3)
        if hot_zones:
            # Pick random hot zone weighted by proximity
            target = random.choice(hot_zones)
            return target
        
        return None
    
    def reset_adaptive_search(self):
        """Reset adaptive search state for new search."""
        self.checked_hiding_spots.clear()
        self.assigned_search_zone = None
    
    def _update_chase(self, dt: float, player, level):
        """Chase state - actively pursuing player."""
        # Update last known position if can see
        if self._can_see_player(player, level):
            self.last_known_player_pos = GridPos(player.x, player.y)
            self.lost_player_timer = 0.0
        else:
            self.lost_player_timer += dt
            
            # Lost player for too long
            if self.lost_player_timer > ENEMY_CHASE_TIMEOUT:
                self._change_state(EnemyState.SEARCH, ENEMY_SEARCH_DURATION)
                return
        
        # Chase toward player
        target = GridPos(player.x, player.y)
        
        # Use A* pathfinding for ALL enemies to avoid getting stuck on walls
        # The performance cost is worth it for correct movement
        use_pathfinding = True
        
        if use_pathfinding and self.pathfinder:
            self._update_pathfinding(target, use_pathfinding=True)
            if self.current_path:
                self._move_along_path(level)
            else:
                self._move_toward(target, level)
        else:
            self._move_toward(target, level)
        
        # Check for catch
        # Reduced hitbox: only damage if actually touching (0.2 tiles) - Very tight!
        if self.pos.distance_to(target) < 0.2:
            self._catch_player(player)
    
    def _update_return(self, dt: float, player, level):
        """Return state - going back to patrol route."""
        # Check for player on the way back
        if self._can_see_player(player, level):
            self.last_known_player_pos = GridPos(player.x, player.y)
            self._change_state(EnemyState.CHASE)
            return
        
        # Move toward spawn
        if self.pos.distance_to(self.spawn_pos) > 0.5:
            self._move_toward(self.spawn_pos, level)
        else:
            # Back at spawn, resume patrol
            self.patrol_index = 0
            self._change_state(EnemyState.PATROL)
    
    def _catch_player(self, player):
        """Handle catching the player."""
        if self.attack_cooldown > 0:
            return
            
        # Deal damage
        if hasattr(player, 'take_damage'):
            game = getattr(self, '_game', None)
            player.take_damage(1, game)
            self.attack_cooldown = 1.0  # 1 second cooldown between attacks
    
    def get_render_color(self) -> Tuple[int, int, int]:
        """Get the render color based on type and state."""
        if self.state in [EnemyState.ALERT, EnemyState.CHASE]:
            from src.core.constants import COLORS
            return COLORS.ENEMY_ALERT
        return self.color
    
    def set_patrol_points(self, points: List[Tuple[float, float]]):
        """Set custom patrol waypoints."""
        self.patrol_points = [GridPos(x, y) for x, y in points]
        self.patrol_index = 0


def create_enemy(x: float, y: float, enemy_type: EnemyType) -> Enemy:
    """Factory function to create enemies."""
    return Enemy(x, y, enemy_type)


def create_patrol_enemy(x: float, y: float, patrol_points: List[Tuple[float, float]]) -> Enemy:
    """Create a patrol enemy with specific waypoints."""
    enemy = Enemy(x, y, EnemyType.PATROL)
    enemy.set_patrol_points(patrol_points)
    return enemy