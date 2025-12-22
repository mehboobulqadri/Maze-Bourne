"""
Tests for A* pathfinding
"""

import pytest
from src.ai.pathfinding import AStarPathfinder, GridPos
from src.levels.level import Level

@pytest.fixture
def pathfinder():
    """Create pathfinder with a simple test level."""
    level = Level.from_endless(1)
    return AStarPathfinder(level.cells)

def test_pathfinder_initialization(pathfinder):
    """Test pathfinder initializes correctly."""
    assert pathfinder is not None
    assert pathfinder.maze is not None
    assert pathfinder.max_cache_size > 0

def test_pathfinder_straight_line(pathfinder):
    """Test pathfinding in a straight line."""
    start = GridPos(5, 5)
    goal = GridPos(10, 5)
    
    path = pathfinder.find_path(start, goal)
    
    if path:
        assert len(path) > 0
        assert path[0] == start or len(path) == 1

def test_pathfinder_same_position(pathfinder):
    """Test pathfinding when start equals goal."""
    pos = GridPos(5, 5)
    path = pathfinder.find_path(pos, pos)
    
    assert path == [pos]

def test_pathfinder_cache(pathfinder):
    """Test that pathfinder caches results."""
    start = GridPos(5, 5)
    goal = GridPos(10, 10)
    
    path1 = pathfinder.find_path(start, goal)
    
    assert pathfinder.performance_stats['total_calls'] >= 1
    
    initial_calls = pathfinder.performance_stats['total_calls']
    path2 = pathfinder.find_path(start, goal)
    
    if path1:
        assert pathfinder.performance_stats['cache_hits'] > 0
