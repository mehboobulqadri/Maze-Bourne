"""
Maze Bourne - AI Director (Adaptive Difficulty System)
Analyzes player behavior and adjusts enemy AI strategies.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum

class AIModifier(Enum):
    NONE = "none"
    CHECK_HIDING_SPOTS = "check_spots"  # Enemies check closets
    GROUP_PATROL = "group_patrol"       # Enemies move in pairs
    FAST_FLANK = "fast_flank"           # Enemies move faster to cut off runners
    SENSITIVE_HEARING = "sensitive"     # Enemies hear from further away
    PREDICTIVE_PATHING = "predictive"   # Enemies move to where you're going

@dataclass
class PlayerProfile:
    """Persistent player behavior profile."""
    hider_score: float = 0.0      # 0.0 to 1.0 (Caps at 1.0)
    runner_score: float = 0.0     # High movement
    camper_score: float = 0.0     # High stationary time outside hiding
    aggro_score: float = 0.0      # Number of alerts triggered
    
    def decay(self, rate=0.1):
        """Slowly forget old habits."""
        self.hider_score = max(0, self.hider_score - rate)
        self.runner_score = max(0, self.runner_score - rate)
        self.camper_score = max(0, self.camper_score - rate)
        self.aggro_score = max(0, self.aggro_score - rate)

class AIDirector:
    """
    The Director observes the player and issues commands to the AI.
    It runs analysis at the end of each level (or floor).
    """
    
    def __init__(self):
        self.profile = PlayerProfile()
        self.active_modifiers: Set[AIModifier] = set()
        self.difficulty_level = 1.0
    
    def analyze_level_stats(self, stats_tracker):
        """Analyze a completed level's stats and update profile."""
        
        # Calculate localized scores for this run
        total_time = max(1.0, stats_tracker.current_total_time)
        
        # Hiding Ratio
        hiding_ratio = stats_tracker.current_time_in_hiding / total_time
        if hiding_ratio > 0.3: # Spent >30% time in closets
            self.profile.hider_score += 0.4
        else:
            self.profile.hider_score -= 0.1
            
        # Stationary Ratio (Camping corners)
        stationary_ratio = stats_tracker.current_stationary_time / total_time
        if stationary_ratio > 0.4:
            self.profile.camper_score += 0.3
        else:
            self.profile.camper_score -= 0.1
            
        # Runner (Distance / Time)
        # Avg speed. If traversing a lot
        avg_speed = stats_tracker.current_distance_traveled / total_time
        if avg_speed > 3.0: # Very fast pace
            self.profile.runner_score += 0.3
        else:
            self.profile.runner_score -= 0.1
            
        # Aggro
        if stats_tracker.current_times_spotted > 2:
            self.profile.aggro_score += 0.3
        else:
            self.profile.aggro_score -= 0.1
            
        # Clamp scores
        self.profile.hider_score = self._clamp(self.profile.hider_score)
        self.profile.camper_score = self._clamp(self.profile.camper_score)
        self.profile.runner_score = self._clamp(self.profile.runner_score)
        self.profile.aggro_score = self._clamp(self.profile.aggro_score)
        
        self._update_modifiers()
        
    def _clamp(self, val):
        return max(0.0, min(1.0, val))
        
    def _update_modifiers(self):
        """Decide on active modifiers based on profile."""
        self.active_modifiers.clear()
        
        if self.profile.hider_score > 0.6:
            self.active_modifiers.add(AIModifier.CHECK_HIDING_SPOTS)
            
        if self.profile.camper_score > 0.6:
            self.active_modifiers.add(AIModifier.GROUP_PATROL) # Flush them out
            self.active_modifiers.add(AIModifier.SENSITIVE_HEARING)
            
        if self.profile.runner_score > 0.6:
            self.active_modifiers.add(AIModifier.FAST_FLANK)
            self.active_modifiers.add(AIModifier.PREDICTIVE_PATHING)
            
        # Difficulty scaling
        self.difficulty_level += 0.1
        
    def get_enemy_config_modifiers(self) -> Dict:
        """Return distinct property overrides for enemies."""
        mods = {}
        
        if AIModifier.FAST_FLANK in self.active_modifiers:
            mods["speed_mult"] = 1.3
            
        if AIModifier.SENSITIVE_HEARING in self.active_modifiers:
            mods["hearing_mult"] = 1.5
            
        return mods

    def get_behavior_instruction(self) -> str:
        """Return a text summary of the Director's Orders (for debug/UI)."""
        if not self.active_modifiers:
            return "Maintaing Standard Patrols."
            
        orders = []
        if AIModifier.CHECK_HIDING_SPOTS in self.active_modifiers:
            orders.append("Search all Closets.")
        if AIModifier.GROUP_PATROL in self.active_modifiers:
            orders.append("Form Patrol Squads.")
        if AIModifier.FAST_FLANK in self.active_modifiers:
            orders.append("Intercept Hostile.")
            
        return " | ".join(orders)
