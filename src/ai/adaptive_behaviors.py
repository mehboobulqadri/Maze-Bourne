"""
Adaptive Enemy AI Behaviors
Enemies learn from player behavior patterns tracked by PlayerBehaviorTracker.
"""

import random
import time
import math
from typing import List, Tuple, Optional, Dict

from src.utils.grid import GridPos
from src.core.logger import get_logger


class AdaptiveMixin:
    """
    Mixin that adds adaptive learning capabilities to enemies.
    
    Uses PlayerBehaviorTracker data to:
    1. Check favorite hiding spots when searching
    2. Plan patrols around danger zones where player died/took damage
    3. Coordinate with other enemies to form groups
    4. Adjust search patterns based on player movement tendencies
    """
    
    # Adaptive learning parameters
    HIDING_CHECK_PRIORITY = 0.7  # 70% chance to check known hiding spots
    DANGER_ZONE_ATTRACTION = 0.5  # How much to prioritize patrolling danger zones
    GROUP_DISTANCE = 5.0  # Distance to consider for group formation
    ADAPTATION_MEMORY = 10  # How many past data points to consider
    
    def __init__(self):
        # Adaptive state
        self.checked_hiding_spots: set = set()  # Already checked this search
        self.coordinating_with: Optional[int] = None  # Enemy ID we're coordinating with
        self.assigned_search_zone: Optional[Tuple[int, int]] = None
        self.last_adaptation_time = 0.0
        self.adaptation_cooldown = 2.0  # Seconds between adaptation updates
        
    def get_player_tendencies(self, game) -> dict:
        """Get player behavior data from tracker."""
        if hasattr(game, 'behavior_tracker') and game.behavior_tracker:
            return game.behavior_tracker.get_player_tendencies()
        return {}
    
    def get_likely_hiding_spots(self, game, top_n: int = 3) -> List[Tuple[int, int]]:
        """Get the most likely hiding spots based on player behavior."""
        if hasattr(game, 'behavior_tracker') and game.behavior_tracker:
            return game.behavior_tracker.get_likely_hiding_spots(top_n)
        return []
    
    def get_danger_zones(self, game) -> List[Tuple[int, int]]:
        """Get locations where player has died or taken damage."""
        tendencies = self.get_player_tendencies(game)
        return tendencies.get('danger_zones', [])
    
    def get_hot_zones(self, game, min_visits: int = 3) -> List[Tuple[int, int]]:
        """Get frequently visited positions."""
        if hasattr(game, 'behavior_tracker') and game.behavior_tracker:
            return game.behavior_tracker.get_hot_zones(min_visits)
        return []
    
    def should_check_hiding_spot(self) -> bool:
        """Decide whether to prioritize checking a hiding spot."""
        return random.random() < self.HIDING_CHECK_PRIORITY
    
    def get_next_adaptive_search_target(self, game, current_pos: GridPos) -> Optional[Tuple[int, int]]:
        """
        Get the next position to search based on player behavior patterns.
        
        Priority order:
        1. Unchecked favorite hiding spots (if player uses them often)
        2. Hot zones (frequently visited areas)
        3. Danger zones (where player has died/taken damage)
        """
        # Get hiding spots
        hiding_spots = self.get_likely_hiding_spots(game)
        unchecked_spots = [s for s in hiding_spots if s not in self.checked_hiding_spots]
        
        if unchecked_spots and self.should_check_hiding_spot():
            # Prioritize closest unchecked hiding spot
            target = min(unchecked_spots, 
                        key=lambda s: abs(s[0] - current_pos[0]) + abs(s[1] - current_pos[1]))
            self.checked_hiding_spots.add(target)
            return target
        
        # Check hot zones next
        hot_zones = self.get_hot_zones(game)
        if hot_zones:
            # Pick a random hot zone weighted by proximity
            weights = [1.0 / (1 + abs(z[0] - current_pos[0]) + abs(z[1] - current_pos[1])) 
                      for z in hot_zones]
            total = sum(weights)
            if total > 0:
                r = random.random() * total
                cumsum = 0
                for i, w in enumerate(weights):
                    cumsum += w
                    if r <= cumsum:
                        return hot_zones[i]
        
        return None
    
    def get_adaptive_patrol_waypoint(self, game, current_pos: GridPos, 
                                     existing_waypoints: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """
        Generate patrol waypoint that covers danger zones.
        Enemies should patrol areas where player tends to die.
        """
        danger_zones = self.get_danger_zones(game)
        
        if danger_zones and random.random() < self.DANGER_ZONE_ATTRACTION:
            # Add a danger zone to patrol
            zone = random.choice(danger_zones)
            # Check if far enough from existing waypoints
            min_dist = float('inf')
            for wp in existing_waypoints:
                dist = abs(wp[0] - zone[0]) + abs(wp[1] - zone[1])
                min_dist = min(min_dist, dist)
            
            if min_dist > 3:  # Not too close to existing waypoints
                return (float(zone[0]) + 0.5, float(zone[1]) + 0.5)
        
        return None
    
    def find_nearby_allies(self, game, max_distance: float = None) -> List:
        """Find nearby enemy allies for coordination."""
        if max_distance is None:
            max_distance = self.GROUP_DISTANCE
            
        allies = []
        for enemy in game.enemies:
            if enemy is self:
                continue
            if not enemy.is_alive:
                continue
            
            dist = math.sqrt((enemy.x - self.x) ** 2 + (enemy.y - self.y) ** 2)
            if dist <= max_distance:
                allies.append(enemy)
        
        return allies
    
    def coordinate_search(self, game, target_pos: Tuple[int, int]) -> Tuple[int, int]:
        """
        Coordinate search with nearby allies to cover different areas.
        Returns adjusted target position.
        """
        allies = self.find_nearby_allies(game)
        
        if not allies:
            return target_pos
        
        # Spread out - each enemy takes a different direction from target
        offsets = [(0, -3), (3, 0), (0, 3), (-3, 0)]  # N, E, S, W
        
        # Find which allies are already assigned directions
        taken_offsets = set()
        for ally in allies:
            if hasattr(ally, 'assigned_search_zone') and ally.assigned_search_zone:
                dx = ally.assigned_search_zone[0] - target_pos[0]
                dy = ally.assigned_search_zone[1] - target_pos[1]
                # Normalize to nearest offset
                for ox, oy in offsets:
                    if (dx > 0 and ox > 0) or (dx < 0 and ox < 0):
                        taken_offsets.add((ox, oy))
                    elif (dy > 0 and oy > 0) or (dy < 0 and oy < 0):
                        taken_offsets.add((ox, oy))
        
        # Take first available offset
        for ox, oy in offsets:
            if (ox, oy) not in taken_offsets:
                adjusted = (target_pos[0] + ox, target_pos[1] + oy)
                self.assigned_search_zone = adjusted
                return adjusted
        
        return target_pos
    
    def reset_search_memory(self):
        """Reset adaptive search state for new search."""
        self.checked_hiding_spots.clear()
        self.assigned_search_zone = None
    
    def get_player_stealth_tendency(self, game) -> float:
        """Get how often player uses stealth (0.0 to 1.0)."""
        tendencies = self.get_player_tendencies(game)
        return tendencies.get('stealth_ratio', 0.5)
    
    def should_listen_carefully(self, game) -> bool:
        """
        Check if enemy should be extra attentive to sounds.
        If player rarely uses stealth, focus more on vision.
        """
        stealth_ratio = self.get_player_stealth_tendency(game)
        # If player uses stealth a lot, be more attentive
        return stealth_ratio > 0.4


class AdaptiveSearchState:
    """
    Enhanced search state that uses player behavior data.
    Replaces or extends the basic SearchState.
    """
    
    def __init__(self):
        self.name = "ADAPTIVE_SEARCH"
        self.enter_time = time.time()
        self.duration = 10.0  # Longer search time for adaptive behavior
        self.search_targets: List[Tuple[int, int]] = []
        self.current_target_idx = 0
        
    def enter(self, enemy):
        """Initialize adaptive search."""
        self.enter_time = time.time()
        self.search_targets = []
        self.current_target_idx = 0
        
        # Reset adaptive memory
        if hasattr(enemy, 'reset_search_memory'):
            enemy.reset_search_memory()
        
        get_logger().debug("Enemy entering adaptive search mode")
    
    def update(self, enemy, player, maze, dt, game=None) -> Optional[str]:
        """
        Update adaptive search behavior.
        
        Returns next state name or None to stay in current state.
        """
        from src.core.constants import EnemyState
        
        # Check for direct player visibility
        if enemy._can_see_player(player, maze):
            return "CHASE"
        
        # Check for sounds
        if hasattr(enemy, '_can_hear_player') and enemy._can_hear_player(player):
            enemy.last_known_player_pos = (int(player.x), int(player.y))
            return "ALERT"
        
        # Check timer expiry
        if time.time() - self.enter_time > self.duration:
            return "PATROL"
        
        current_pos = (int(enemy.x), int(enemy.y))
        
        # Get adaptive search target if we have game reference
        if game and hasattr(enemy, 'get_next_adaptive_search_target'):
            adaptive_target = enemy.get_next_adaptive_search_target(game, current_pos)
            
            if adaptive_target:
                # Coordinate with allies
                if hasattr(enemy, 'coordinate_search'):
                    adaptive_target = enemy.coordinate_search(game, adaptive_target)
                
                # Move toward adaptive target
                enemy._update_pathfinding(adaptive_target, use_pathfinding=True)
                enemy._move_along_path(maze)
                return None
        
        # Fall back to random search in area
        if not self.search_targets:
            self._generate_search_targets(enemy)
        
        if self.search_targets:
            target = self.search_targets[self.current_target_idx]
            
            # Check if reached target
            dist = abs(current_pos[0] - target[0]) + abs(current_pos[1] - target[1])
            if dist < 1.5:
                self.current_target_idx = (self.current_target_idx + 1) % len(self.search_targets)
            else:
                enemy._update_pathfinding(target, use_pathfinding=True)
                enemy._move_along_path(maze)
        
        return None
    
    def _generate_search_targets(self, enemy):
        """Generate search positions around last known player location."""
        if not hasattr(enemy, 'last_known_player_pos') or not enemy.last_known_player_pos:
            return
        
        lx, ly = enemy.last_known_player_pos
        offsets = [(0, 0), (2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, -2)]
        
        for ox, oy in offsets:
            target = (lx + ox, ly + oy)
            self.search_targets.append(target)
        
        random.shuffle(self.search_targets)
    
    def exit(self, enemy):
        """Clean up on exit."""
        if hasattr(enemy, 'reset_search_memory'):
            enemy.reset_search_memory()
    
    def is_expired(self) -> bool:
        """Check if search duration expired."""
        return time.time() - self.enter_time > self.duration


def apply_adaptive_mixin(enemy_class):
    """
    Decorator/function to add AdaptiveMixin to an enemy class.
    
    Usage:
        AdaptiveEnemy = apply_adaptive_mixin(Enemy)
        enemy = AdaptiveEnemy(x, y, enemy_type)
    """
    class AdaptiveEnemy(AdaptiveMixin, enemy_class):
        def __init__(self, *args, **kwargs):
            enemy_class.__init__(self, *args, **kwargs)
            AdaptiveMixin.__init__(self)
    
    return AdaptiveEnemy
