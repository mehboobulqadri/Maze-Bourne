from src.levels.level import Level
from src.core.constants import CellType

def regenerate_level_1():
    print("Regenerating Level 1...")
    # Create with decent size
    level = Level(25, 20, algorithm="bsp")
    
    # Init was done by __init__, but we can force re-gen if we want specific params
    # Level init calls: self.generator = MazeGenerator(width, height, seed).generate(algorithm)
    # So `level` is already a generated maze! 
    # But level.generator is the MazeGenerator instance returned by .generate() (which returns self)
    
    # We just need to save it. 
    # But let's ensure it has content we want.
    
    # Adding some extras if needed, but the generator usually handles everything.
    
    level.level_number = 1
    level.level_name = "The Escape"
    
    level.save_to_file("levels/level_1.json")
    print("Level 1 Regenerated successfully.")

if __name__ == "__main__":
    regenerate_level_1()
