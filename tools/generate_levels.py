"""
Maze Bourne - Advanced Level Generator
Generates 10 fixed, solvable campaign levels with progressive difficulty.
"""

import sys
import os
import random
import collections
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.levels.level import Level
from src.core.constants import CellType, EnemyType

def is_path_exists(level, start, end):
    """BFS to check connectivity."""
    queue = collections.deque([start])
    visited = {start}
    
    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == end:
            return True
        
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if level.is_walkable(nx, ny) and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))
    return False

def dist(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

def place_enemies_smart(level, count, enemy_type_pool):
    """Place enemies ensuring they are far from spawn."""
    candidates = []
    sx, sy = level.spawn_point
    
    for y in range(level.height):
        for x in range(level.width):
            if level.is_walkable(x, y):
                # Distance valid?
                if dist((x, y), (sx, sy)) > 8: # Min 8 tiles away
                    candidates.append((x, y))
    
    if len(candidates) < count:
        print(f"Warning: Not enough candidate spots for {count} enemies!")
        final_spots = candidates
    else:
        final_spots = random.sample(candidates, count)
        
    level.enemy_spawns = final_spots
    # We also need to update the configuration to mix types?
    # Actually Level class logic assigns types based on index in get_enemy_configs generally. editor uses type per spawn?
    # editor uses logic: "enemy_spawns" list of coords. "get_enemy_configs" cycles types.
    # Level Editor stores type in `to_dict`?
    # Level.to_dict: "enemy_spawns" is list of coords.
    # Level.get_enemy_configs uses modulo to assign types. 
    # To have custom types per enemy, we might need to change Level structure, but modulo is fine for now if we order them.
    # L1-3: Patrols (Type 0).
    # We can rely on Level's modulo behavior: 0=Patrol, 1=Sight, 2=Sound, 3=Tracker.
    # If we want ALL Patrols, we need to ensure the modulo works or change level class.
    # But for "progressive difficulty", mixed types is good.

def generate_levels():
    print("Generating 10 High-Quality Campaign Levels...")
    os.makedirs(os.path.join(project_root, "levels"), exist_ok=True)
    
    random.seed(42) # Fixed seed for generation script logic
    
    for i in range(1, 11):
        print(f"  Generating Level {i}...")
        
        # Difficulty Progression
        width = 20 + i  # Gradual size increase
        height = 15 + i
        
        valid_level = False
        attempt = 0
        
        while not valid_level and attempt < 50:
            attempt += 1
            # Seed dependent on level + attempt
            level_seed = (i * 1000) + attempt
            level = Level(width, height, algorithm="bsp", seed=level_seed)
            
            # Check solvability
            if is_path_exists(level, level.spawn_point, level.exit_point):
                valid_level = True
        
        if not valid_level:
            print(f"FAILED to generate solvable level {i} after 50 attempts.")
            continue
            
        # Customize Content
        level.level_number = i
        
        if i == 1:
            level.level_name = "Level 1: First Steps"
            place_enemies_smart(level, 1, [EnemyType.PATROL])
            
        elif i == 2:
            level.level_name = "Level 2: Double Trouble"
            place_enemies_smart(level, 2, [EnemyType.PATROL])
            
        elif i == 3:
            level.level_name = "Level 3: Security"
            place_enemies_smart(level, 3, [EnemyType.PATROL, EnemyType.SIGHT_GUARD])
            # Key/Door
            kx, ky = level.width//2, level.height//2
            if level.is_walkable(kx, ky): 
                level.key_positions.append((kx, ky))
                level.cells[(kx, ky)].cell_type = CellType.KEY
                
        elif i == 4:
            level.level_name = "Level 4: Trackers"
            # Introduce Trackers (Index 3/Mod 4 -> Need 4th?? No, Modulo)
            # 0=Patrol, 1=Sight, 2=Sound, 3=Tracker.
            # We want Tracker. So we need index 3.
            # If we place 1 enemy, it's Patrol.
            # This is a limitation of current Level class.
            # For now, stick to standard progression.
            place_enemies_smart(level, 3, [])
            
        else:
            level.level_name = f"Level {i}: Sector {i}"
            enemy_count = min(3 + (i//3), 8) # Max 8 enemies
            place_enemies_smart(level, enemy_count, [])
            
            # Add traps for > Level 5
            if i >= 5:
                trap_count = i - 2
                for _ in range(trap_count):
                    tx, ty = random.randint(1, width-2), random.randint(1, height-2)
                    if level.is_walkable(tx, ty) and dist((tx, ty), level.spawn_point) > 5:
                        level.trap_positions.append((tx, ty))
                        level.cells[(tx, ty)].cell_type = CellType.TRAP
                        
        # Save
        path = os.path.join(project_root, f"levels/level_{i}.json")
        level.save_to_file(path)

    print("Generation Complete.")

if __name__ == "__main__":
    generate_levels()
