"""
Maze Bourne - Main Entry Point
A Stealth Sci-Fi Maze Game with RL AI
"""

import sys
import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.game import Game, main


if __name__ == "__main__":
    main()