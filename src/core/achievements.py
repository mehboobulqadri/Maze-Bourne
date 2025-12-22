"""
Maze Bourne - Achievement System
Tracks player progress and unlocks badges
"""

import json
import os
from typing import Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from src.core.logger import get_logger


class AchievementType(Enum):
    """Types of achievements."""
    STORY = auto()
    SPEED = auto()
    STEALTH = auto()
    SURVIVAL = auto()
    MASTERY = auto()


@dataclass
class Achievement:
    """Individual achievement definition."""
    id: str
    name: str
    description: str
    achievement_type: AchievementType
    icon_color: tuple = (255, 215, 0)
    unlocked: bool = False
    unlock_time: float = 0.0
    hidden: bool = False
    requirement: dict = field(default_factory=dict)
    
    def check_unlock(self, stats: dict) -> bool:
        """Check if this achievement should be unlocked based on stats."""
        if self.unlocked:
            return False
        
        req_type = self.requirement.get("type")
        
        if req_type == "level_complete":
            level_num = self.requirement.get("level")
            return stats.get("levels_completed", set()).__contains__(level_num)
        
        elif req_type == "all_levels":
            total = self.requirement.get("count", 10)
            return len(stats.get("levels_completed", set())) >= total
        
        elif req_type == "speed_run":
            level_num = self.requirement.get("level")
            target_time = self.requirement.get("time")
            best_time = stats.get("level_best_times", {}).get(level_num, float('inf'))
            return best_time <= target_time
        
        elif req_type == "no_damage":
            level_num = self.requirement.get("level")
            return stats.get("no_damage_levels", set()).__contains__(level_num)
        
        elif req_type == "perfect_stealth":
            level_num = self.requirement.get("level")
            return stats.get("stealth_perfect_levels", set()).__contains__(level_num)
        
        elif req_type == "total_deaths":
            return stats.get("total_deaths", 0) >= self.requirement.get("count", 1)
        
        return False


class AchievementManager:
    """Manages all achievements and progress."""
    
    def __init__(self):
        self.achievements: Dict[str, Achievement] = {}
        self.unlocked_achievements: Set[str] = set()
        self.save_path = "achievements.json"
        
        self._define_achievements()
        self.load()
    
    def _define_achievements(self):
        """Define all achievements in the game."""
        achievements = [
            # Story Progression
            Achievement("first_escape", "First Escape", "Complete Level 1", 
                       AchievementType.STORY, (100, 255, 150),
                       requirement={"type": "level_complete", "level": 1}),
            
            Achievement("halfway_there", "Halfway There", "Complete Level 5",
                       AchievementType.STORY, (100, 200, 255),
                       requirement={"type": "level_complete", "level": 5}),
            
            Achievement("master_escapist", "Master Escapist", "Complete all 10 levels",
                       AchievementType.STORY, (255, 215, 0),
                       requirement={"type": "all_levels", "count": 10}),
            
            # Speed Running
            Achievement("speed_demon_1", "Speed Demon I", "Complete Level 1 in under 60 seconds",
                       AchievementType.SPEED, (255, 180, 50),
                       requirement={"type": "speed_run", "level": 1, "time": 60.0}),
            
            Achievement("speed_demon_5", "Speed Demon V", "Complete Level 5 in under 120 seconds",
                       AchievementType.SPEED, (255, 180, 50),
                       requirement={"type": "speed_run", "level": 5, "time": 120.0}),
            
            Achievement("ultimate_speedrunner", "Ultimate Speedrunner", "Complete Level 10 in under 180 seconds",
                       AchievementType.SPEED, (255, 100, 100),
                       requirement={"type": "speed_run", "level": 10, "time": 180.0}),
            
            # Stealth
            Achievement("ghost", "Ghost", "Complete a level without being spotted",
                       AchievementType.STEALTH, (150, 150, 255),
                       requirement={"type": "perfect_stealth", "level": 1}),
            
            Achievement("phantom", "Phantom", "Complete 5 levels without being spotted",
                       AchievementType.STEALTH, (180, 150, 255),
                       hidden=True,
                       requirement={"type": "perfect_stealth_count", "count": 5}),
            
            # Survival
            Achievement("untouchable", "Untouchable", "Complete a level without taking damage",
                       AchievementType.SURVIVAL, (255, 100, 200),
                       requirement={"type": "no_damage", "level": 1}),
            
            Achievement("iron_will", "Iron Will", "Die 10 times and keep trying",
                       AchievementType.SURVIVAL, (200, 200, 200),
                       requirement={"type": "total_deaths", "count": 10}),
            
            Achievement("persistent", "Persistent", "Die 50 times total",
                       AchievementType.SURVIVAL, (150, 150, 150),
                       hidden=True,
                       requirement={"type": "total_deaths", "count": 50}),
            
            # Mastery
            Achievement("three_star_master", "Three Star Master", "Get 3 stars on 5 different levels",
                       AchievementType.MASTERY, (255, 215, 0),
                       hidden=True,
                       requirement={"type": "three_star_count", "count": 5}),
            
            Achievement("flawless_victory", "Flawless Victory", "Complete Level 10 with 3 stars and no damage",
                       AchievementType.MASTERY, (255, 255, 100),
                       hidden=True,
                       requirement={"type": "flawless_level", "level": 10}),
        ]
        
        for achievement in achievements:
            self.achievements[achievement.id] = achievement
    
    def check_all(self, stats: dict) -> List[Achievement]:
        """Check all achievements and return newly unlocked ones."""
        newly_unlocked = []
        
        for achievement in self.achievements.values():
            if achievement.check_unlock(stats):
                achievement.unlocked = True
                achievement.unlock_time = stats.get("current_time", 0.0)
                self.unlocked_achievements.add(achievement.id)
                newly_unlocked.append(achievement)
        
        return newly_unlocked
    
    def get_achievement(self, achievement_id: str) -> Achievement:
        """Get achievement by ID."""
        return self.achievements.get(achievement_id)
    
    def get_all_unlocked(self) -> List[Achievement]:
        """Get all unlocked achievements."""
        return [ach for ach in self.achievements.values() if ach.unlocked]
    
    def get_all_visible(self) -> List[Achievement]:
        """Get all visible achievements (unlocked or not hidden)."""
        return [ach for ach in self.achievements.values() 
                if ach.unlocked or not ach.hidden]
    
    def get_progress(self) -> tuple:
        """Get overall achievement progress (unlocked, total)."""
        total = len(self.achievements)
        unlocked = len(self.unlocked_achievements)
        return (unlocked, total)
    
    def save(self):
        """Save achievement progress to file."""
        data = {
            "unlocked": list(self.unlocked_achievements),
            "achievements": {
                aid: {
                    "unlocked": ach.unlocked,
                    "unlock_time": ach.unlock_time
                }
                for aid, ach in self.achievements.items()
            }
        }
        
        with open(self.save_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self):
        """Load achievement progress from file."""
        if not os.path.exists(self.save_path):
            return
        
        try:
            with open(self.save_path, 'r') as f:
                data = json.load(f)
            
            self.unlocked_achievements = set(data.get("unlocked", []))
            
            for aid, ach_data in data.get("achievements", {}).items():
                if aid in self.achievements:
                    self.achievements[aid].unlocked = ach_data.get("unlocked", False)
                    self.achievements[aid].unlock_time = ach_data.get("unlock_time", 0.0)
        except Exception as e:
            get_logger().error(f"Error loading achievements: {e}", exc_info=True)
