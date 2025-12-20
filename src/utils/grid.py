"""
Grid utilities for position and pathfinding
"""

import math
from typing import Tuple


class GridPos:
    """Represents a position on the game grid."""
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def __eq__(self, other):
        if not isinstance(other, GridPos):
            return False
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((int(self.x), int(self.y)))
    
    def __repr__(self):
        return f"GridPos({self.x}, {self.y})"
    
    def distance_to(self, other: 'GridPos') -> float:
        """Calculate Euclidean distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def manhattan_distance(self, other: 'GridPos') -> float:
        """Calculate Manhattan distance to another position."""
        return abs(self.x - other.x) + abs(self.y - other.y)
    
    def to_tuple(self) -> Tuple[int, int]:
        """Convert to integer tuple."""
        return (int(self.x), int(self.y))
    
    def copy(self) -> 'GridPos':
        """Create a copy of this position."""
        return GridPos(self.x, self.y)
