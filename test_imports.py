#!/usr/bin/env python
"""Test imports"""

try:
    from src.core.game import Game
    print("[OK] Game imported successfully")
    
    from src.core.achievements import AchievementManager
    print("[OK] AchievementManager imported successfully")
    
    from src.core.stats_tracker import StatsTracker
    print("[OK] StatsTracker imported successfully")
    
    from src.utils.grid import GridPos
    print("[OK] GridPos imported successfully")
    
    print("\n[SUCCESS] All imports working!")
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()
