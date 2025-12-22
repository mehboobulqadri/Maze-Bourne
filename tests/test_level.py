"""
Tests for Level system
"""

import pytest
import os
import json
import tempfile
from src.levels.level import Level
from src.core.constants import CellType

def test_level_creation():
    """Test basic level creation."""
    level = Level.from_endless(1)
    
    assert level is not None
    assert level.width > 0
    assert level.height > 0
    assert level.spawn_point is not None
    assert level.exit_point is not None

def test_level_walkable():
    """Test walkability checking."""
    level = Level.from_endless(1)
    
    spawn_x, spawn_y = level.spawn_point
    assert level.is_walkable(spawn_x, spawn_y)
    
    assert not level.is_walkable(-1, -1)

def test_level_save_load():
    """Test level save and load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "test_level.json")
        
        original = Level.from_endless(1)
        original.level_name = "Test Level"
        original.save_to_file(save_path)
        
        assert os.path.exists(save_path)
        
        loaded = Level.load_from_file(save_path)
        
        assert loaded.width == original.width
        assert loaded.height == original.height
        assert loaded.level_name == original.level_name

def test_level_key_collection():
    """Test key collection."""
    level = Level.from_endless(1)
    
    if level.key_positions:
        kx, ky = level.key_positions[0]
        assert level.collect_key(kx, ky)
        assert (kx, ky) in level.collected_keys
        
        assert not level.collect_key(kx, ky)
