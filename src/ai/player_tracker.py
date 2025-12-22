"""
Player Behavior Tracking System for Adaptive AI
Tracks player patterns to inform enemy learning and LLM strategist.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import math
import time


@dataclass
class PlayerBehaviorTracker:
    """
    Tracks player behavior patterns for adaptive enemy AI.
    
    Collected data is used by:
    1. Adaptive enemies to anticipate player tactics
    2. LLM strategist to provide tactical insights
    3. Boss battles to adjust difficulty
    """
    
    # Hiding behavior - tracks which spots player uses and how often
    hiding_spot_usage: Dict[Tuple[int, int], int] = field(default_factory=lambda: defaultdict(int))
    total_hides: int = 0
    time_spent_hiding: float = 0.0
    last_hide_start: float = 0.0
    
    # Movement patterns
    preferred_directions: Dict[str, int] = field(default_factory=lambda: defaultdict(int))  # "N", "S", "E", "W"
    stealth_time: float = 0.0
    normal_time: float = 0.0
    run_time: float = 0.0
    total_distance: float = 0.0
    
    # Death/near-miss locations
    death_locations: List[Tuple[int, int]] = field(default_factory=list)
    near_miss_locations: List[Tuple[int, int]] = field(default_factory=list)  # Spotted but escaped
    damage_locations: List[Tuple[int, int]] = field(default_factory=list)
    
    # Route preferences - visited positions with frequency
    visited_positions: Dict[Tuple[int, int], int] = field(default_factory=lambda: defaultdict(int))
    
    # Door usage
    doors_opened: int = 0
    doors_used_for_escape: int = 0
    
    # Combat behavior (for boss fights)
    successful_parries: int = 0
    failed_parries: int = 0
    dodge_attempts: int = 0
    
    # Floor progression
    floors_completed: int = 0
    average_floor_time: float = 0.0
    total_play_time: float = 0.0
    
    # Tracking state
    _last_position: Optional[Tuple[float, float]] = None
    _last_update_time: float = 0.0
    _is_hidden: bool = False
    _is_stealthed: bool = False
    
    def record_position(self, x: float, y: float, is_stealthed: bool = False, dt: float = 0.0):
        """Record player position and update movement patterns."""
        grid_pos = (int(x), int(y))
        self.visited_positions[grid_pos] += 1
        
        if self._last_position is not None:
            dx = x - self._last_position[0]
            dy = y - self._last_position[1]
            
            # Calculate distance moved
            dist = math.sqrt(dx * dx + dy * dy)
            self.total_distance += dist
            
            # Track direction preferences
            if abs(dx) > 0.1 or abs(dy) > 0.1:
                if abs(dx) > abs(dy):
                    direction = "E" if dx > 0 else "W"
                else:
                    direction = "S" if dy > 0 else "N"
                self.preferred_directions[direction] += 1
        
        self._last_position = (x, y)
        
        # Track stealth usage
        if is_stealthed:
            self.stealth_time += dt
            self._is_stealthed = True
        else:
            self.normal_time += dt
            self._is_stealthed = False
    
    def record_hide(self, pos: Tuple[int, int], is_entering: bool):
        """Record hiding behavior."""
        if is_entering:
            self.hiding_spot_usage[pos] += 1
            self.total_hides += 1
            self.last_hide_start = time.time()
            self._is_hidden = True
        else:
            if self._is_hidden:
                self.time_spent_hiding += time.time() - self.last_hide_start
            self._is_hidden = False
    
    def record_death(self, pos: Tuple[int, int]):
        """Record death location."""
        self.death_locations.append(pos)
    
    def record_damage(self, pos: Tuple[int, int]):
        """Record location where player took damage."""
        self.damage_locations.append(pos)
    
    def record_near_miss(self, pos: Tuple[int, int]):
        """Record location where player was spotted but escaped."""
        self.near_miss_locations.append(pos)
    
    def record_door_used(self, was_escaping: bool = False):
        """Record door usage."""
        self.doors_opened += 1
        if was_escaping:
            self.doors_used_for_escape += 1
    
    def record_floor_complete(self, time_taken: float):
        """Record floor completion."""
        self.floors_completed += 1
        self.total_play_time += time_taken
        self.average_floor_time = self.total_play_time / self.floors_completed
    
    def record_parry(self, success: bool):
        """Record parry attempt result."""
        if success:
            self.successful_parries += 1
        else:
            self.failed_parries += 1
    
    def record_dodge(self):
        """Record dodge attempt."""
        self.dodge_attempts += 1
    
    def get_player_tendencies(self) -> dict:
        """
        Get summary of player tendencies for AI/LLM consumption.
        
        Returns:
            Dict with player behavior patterns
        """
        total_direction = sum(self.preferred_directions.values()) or 1
        total_time = self.stealth_time + self.normal_time or 1
        
        # Calculate hiding preference
        hiding_preference = 0.0
        if self.total_hides > 0 and self.time_spent_hiding > 0:
            hiding_preference = min(1.0, self.time_spent_hiding / (total_time * 0.3))
        
        # Get most used hiding spots
        favorite_hiding_spots = sorted(
            self.hiding_spot_usage.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Get danger zones (where player died or took damage)
        danger_zones = list(set(self.death_locations + self.damage_locations))
        
        return {
            "hiding_preference": hiding_preference,
            "favorite_hiding_spots": favorite_hiding_spots,
            "stealth_ratio": self.stealth_time / total_time,
            "direction_preference": {
                d: count / total_direction 
                for d, count in self.preferred_directions.items()
            },
            "danger_zones": danger_zones[-10:],  # Last 10 danger locations
            "near_miss_zones": self.near_miss_locations[-10:],
            "total_hides": self.total_hides,
            "floors_completed": self.floors_completed,
            "average_floor_time": self.average_floor_time,
            "doors_for_escape_ratio": (
                self.doors_used_for_escape / self.doors_opened 
                if self.doors_opened > 0 else 0
            ),
            "parry_success_rate": (
                self.successful_parries / (self.successful_parries + self.failed_parries)
                if (self.successful_parries + self.failed_parries) > 0 else 0.5
            ),
        }
    
    def get_hot_zones(self, min_visits: int = 3) -> List[Tuple[int, int]]:
        """Get frequently visited positions."""
        return [
            pos for pos, count in self.visited_positions.items() 
            if count >= min_visits
        ]
    
    def get_likely_hiding_spots(self, top_n: int = 3) -> List[Tuple[int, int]]:
        """Get the most likely hiding spots based on past behavior."""
        if not self.hiding_spot_usage:
            return []
        
        sorted_spots = sorted(
            self.hiding_spot_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [pos for pos, _ in sorted_spots[:top_n]]
    
    def reset_for_new_floor(self):
        """Reset per-floor tracking while keeping cross-floor stats."""
        # Keep cumulative stats, reset position tracking
        self.visited_positions.clear()
        self._last_position = None
    
    def to_dict(self) -> dict:
        """Serialize tracker state for saving."""
        return {
            "hiding_spot_usage": dict(self.hiding_spot_usage),
            "total_hides": self.total_hides,
            "time_spent_hiding": self.time_spent_hiding,
            "preferred_directions": dict(self.preferred_directions),
            "stealth_time": self.stealth_time,
            "normal_time": self.normal_time,
            "death_locations": self.death_locations,
            "near_miss_locations": self.near_miss_locations,
            "damage_locations": self.damage_locations,
            "doors_opened": self.doors_opened,
            "doors_used_for_escape": self.doors_used_for_escape,
            "floors_completed": self.floors_completed,
            "average_floor_time": self.average_floor_time,
            "successful_parries": self.successful_parries,
            "failed_parries": self.failed_parries,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlayerBehaviorTracker':
        """Load tracker state from saved data."""
        tracker = cls()
        tracker.hiding_spot_usage = defaultdict(int, {
            tuple(k) if isinstance(k, list) else k: v 
            for k, v in data.get("hiding_spot_usage", {}).items()
        })
        tracker.total_hides = data.get("total_hides", 0)
        tracker.time_spent_hiding = data.get("time_spent_hiding", 0.0)
        tracker.preferred_directions = defaultdict(int, data.get("preferred_directions", {}))
        tracker.stealth_time = data.get("stealth_time", 0.0)
        tracker.normal_time = data.get("normal_time", 0.0)
        tracker.death_locations = [tuple(p) for p in data.get("death_locations", [])]
        tracker.near_miss_locations = [tuple(p) for p in data.get("near_miss_locations", [])]
        tracker.damage_locations = [tuple(p) for p in data.get("damage_locations", [])]
        tracker.doors_opened = data.get("doors_opened", 0)
        tracker.doors_used_for_escape = data.get("doors_used_for_escape", 0)
        tracker.floors_completed = data.get("floors_completed", 0)
        tracker.average_floor_time = data.get("average_floor_time", 0.0)
        tracker.successful_parries = data.get("successful_parries", 0)
        tracker.failed_parries = data.get("failed_parries", 0)
        return tracker
