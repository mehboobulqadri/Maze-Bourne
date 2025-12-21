"""
Maze Bourne - Statistics and Leaderboard System
Tracks player performance, times, and rankings
"""

import json
import os
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class LevelStats:
    """Statistics for a single level completion."""
    level_num: int
    completion_time: float
    stars: int
    damage_taken: int
    times_spotted: int
    stealth_percentage: float
    date_completed: float
    
    def to_dict(self) -> dict:
        return {
            "level_num": self.level_num,
            "completion_time": self.completion_time,
            "stars": self.stars,
            "damage_taken": self.damage_taken,
            "times_spotted": self.times_spotted,
            "stealth_percentage": self.stealth_percentage,
            "date_completed": self.date_completed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LevelStats':
        return cls(**data)


class StatsTracker:
    """Tracks all player statistics and performance."""
    
    def __init__(self):
        self.save_path = "stats.json"
        
        # Current run stats
        self.current_level_start_time = 0.0
        self.current_level_num = 0
        self.current_damage_taken = 0
        self.current_times_spotted = 0
        self.current_stealth_time = 0.0
        self.current_total_time = 0.0
        
        # Overall stats
        self.total_playtime = 0.0
        self.total_deaths = 0
        self.total_levels_completed = 0
        self.levels_completed: set = set()
        
        # Best times per level
        self.level_best_times: Dict[int, float] = {}
        self.level_best_stars: Dict[int, int] = {}
        
        # Leaderboard (per level)
        self.level_leaderboards: Dict[int, List[LevelStats]] = {}
        
        # Special achievements tracking
        self.no_damage_levels: set = set()
        self.stealth_perfect_levels: set = set()
        self.three_star_levels: set = set()
        
        self.load()
    
    def start_level(self, level_num: int):
        """Start tracking a new level attempt."""
        self.current_level_num = level_num
        self.current_level_start_time = time.time()
        self.current_damage_taken = 0
        self.current_times_spotted = 0
        self.current_time_in_hiding = 0.0
        self.current_stationary_time = 0.0
        self.current_distance_traveled = 0.0
    
    def update(self, dt: float, is_stealthed: bool = False, 
               is_hiding: bool = False, is_moving: bool = False):
        """Update ongoing level stats."""
        self.current_total_time += dt
        
        if is_stealthed:
            self.current_stealth_time += dt
        
        if is_hiding:
            self.current_time_in_hiding += dt
            
        if not is_moving:
            self.current_stationary_time += dt
            
    def record_movement(self, distance: float):
        """Record distance moved."""
        self.current_distance_traveled += distance
    
    def record_damage(self):
        """Record player taking damage."""
        self.current_damage_taken += 1
    
    def record_spotted(self):
        """Record player being spotted by enemy."""
        self.current_times_spotted += 1
    
    def record_death(self):
        """Record player death."""
        self.total_deaths += 1
    
    def complete_level(self, level_num: int) -> Tuple[int, bool, bool]:
        """
        Record level completion and calculate performance.
        Returns: (stars, is_new_best_time, is_new_best_stars)
        """
        # Use accumulated actual gameplay time (dt sum) instead of wall clock
        # This correctly handles pauses
        completion_time = self.current_total_time
        stealth_percentage = (self.current_stealth_time / max(0.01, self.current_total_time)) * 100
        
        # Calculate star rating based on time
        stars = self._calculate_stars(level_num, completion_time)
        
        # Track special achievements
        if self.current_damage_taken == 0:
            self.no_damage_levels.add(level_num)
        
        if self.current_times_spotted == 0:
            self.stealth_perfect_levels.add(level_num)
        
        if stars == 3:
            self.three_star_levels.add(level_num)
        
        # Update level completion tracking
        if level_num not in self.levels_completed:
            self.levels_completed.add(level_num)
            self.total_levels_completed += 1
        
        # Check for new best time
        is_new_best_time = False
        if level_num not in self.level_best_times or completion_time < self.level_best_times[level_num]:
            self.level_best_times[level_num] = completion_time
            is_new_best_time = True
        
        # Check for new best stars
        is_new_best_stars = False
        if level_num not in self.level_best_stars or stars > self.level_best_stars[level_num]:
            self.level_best_stars[level_num] = stars
            is_new_best_stars = True
        
        # Add to leaderboard
        level_stat = LevelStats(
            level_num=level_num,
            completion_time=completion_time,
            stars=stars,
            damage_taken=self.current_damage_taken,
            times_spotted=self.current_times_spotted,
            stealth_percentage=stealth_percentage,
            date_completed=time.time()
        )
        
        if level_num not in self.level_leaderboards:
            self.level_leaderboards[level_num] = []
        
        self.level_leaderboards[level_num].append(level_stat)
        self.level_leaderboards[level_num].sort(key=lambda x: x.completion_time)
        # Keep only top 10 runs per level
        self.level_leaderboards[level_num] = self.level_leaderboards[level_num][:10]
        
        self.save()
        
        return (stars, is_new_best_time, is_new_best_stars)
    
    def _calculate_stars(self, level_num: int, completion_time: float) -> int:
        """
        Calculate star rating (1-3) based on completion time.
        Thresholds scale with level difficulty.
        """
        # Base time thresholds (seconds)
        base_three_star = 30.0
        base_two_star = 60.0
        base_one_star = 120.0
        
        # Scale with level number
        level_multiplier = 1.0 + (level_num - 1) * 0.3
        
        three_star_time = base_three_star * level_multiplier
        two_star_time = base_two_star * level_multiplier
        one_star_time = base_one_star * level_multiplier
        
        if completion_time <= three_star_time:
            return 3
        elif completion_time <= two_star_time:
            return 2
        elif completion_time <= one_star_time:
            return 1
        else:
            return 1  # Minimum 1 star for completion
    
    def get_star_thresholds(self, level_num: int) -> Tuple[float, float, float]:
        """Get the time thresholds for each star rating."""
        base_three_star = 30.0
        base_two_star = 60.0
        base_one_star = 120.0
        
        level_multiplier = 1.0 + (level_num - 1) * 0.3
        
        return (
            base_three_star * level_multiplier,
            base_two_star * level_multiplier,
            base_one_star * level_multiplier
        )
    
    def get_leaderboard(self, level_num: int, limit: int = 10) -> List[LevelStats]:
        """Get top runs for a specific level."""
        return self.level_leaderboards.get(level_num, [])[:limit]
    
    def get_best_time(self, level_num: int) -> float:
        """Get best time for a specific level."""
        return self.level_best_times.get(level_num, float('inf'))
    
    def get_best_stars(self, level_num: int) -> int:
        """Get best star rating for a specific level."""
        return self.level_best_stars.get(level_num, 0)
    
    def get_stats_dict(self) -> dict:
        """Get stats as dictionary for achievement checking."""
        return {
            "levels_completed": self.levels_completed,
            "level_best_times": self.level_best_times,
            "no_damage_levels": self.no_damage_levels,
            "stealth_perfect_levels": self.stealth_perfect_levels,
            "total_deaths": self.total_deaths,
            "three_star_levels": self.three_star_levels,
            "current_time": time.time()
        }
    
    def save(self):
        """Save stats to file."""
        data = {
            "total_playtime": self.total_playtime,
            "total_deaths": self.total_deaths,
            "total_levels_completed": self.total_levels_completed,
            "levels_completed": list(self.levels_completed),
            "level_best_times": {str(k): v for k, v in self.level_best_times.items()},
            "level_best_stars": {str(k): v for k, v in self.level_best_stars.items()},
            "no_damage_levels": list(self.no_damage_levels),
            "stealth_perfect_levels": list(self.stealth_perfect_levels),
            "three_star_levels": list(self.three_star_levels),
            "leaderboards": {
                str(level_num): [stat.to_dict() for stat in stats]
                for level_num, stats in self.level_leaderboards.items()
            }
        }
        
        with open(self.save_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self):
        """Load stats from file."""
        if not os.path.exists(self.save_path):
            return
        
        try:
            with open(self.save_path, 'r') as f:
                data = json.load(f)
            
            self.total_playtime = data.get("total_playtime", 0.0)
            self.total_deaths = data.get("total_deaths", 0)
            self.total_levels_completed = data.get("total_levels_completed", 0)
            self.levels_completed = set(data.get("levels_completed", []))
            
            self.level_best_times = {int(k): v for k, v in data.get("level_best_times", {}).items()}
            self.level_best_stars = {int(k): v for k, v in data.get("level_best_stars", {}).items()}
            
            self.no_damage_levels = set(data.get("no_damage_levels", []))
            self.stealth_perfect_levels = set(data.get("stealth_perfect_levels", []))
            self.three_star_levels = set(data.get("three_star_levels", []))
            
            leaderboards_data = data.get("leaderboards", {})
            self.level_leaderboards = {
                int(level_num): [LevelStats.from_dict(stat_dict) for stat_dict in stats]
                for level_num, stats in leaderboards_data.items()
            }
            
        except Exception as e:
            print(f"[StatsTracker] Error loading stats: {e}")
