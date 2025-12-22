"""
Maze Bourne - Level System
Manages level loading, creation, and state
"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

from src.core.constants import CellType, EnemyType
from src.core.logger import get_logger
from src.levels.maze_generator import MazeGenerator, Cell, create_campaign_level, create_endless_level
import json
import os


class Level:
    """
    Represents a game level with maze, objects, and entities.
    Wraps the MazeGenerator for in-game use.
    """
    
    def __init__(self, width: int = 20, height: int = 15, 
                 algorithm: str = "bsp", seed: Optional[int] = None):
        """Create a new procedurally generated level."""
        # Generate maze
        self.generator = MazeGenerator(width, height, seed).generate(algorithm)
        
        # Copy properties from generator
        self.width = width
        self.height = height
        self.cells = self.generator.cells
        self.rooms = self.generator.rooms
        
        # Special positions
        self.spawn_point = self.generator.spawn_point
        self.exit_point = self.generator.exit_point
        
        # Object positions (from generator)
        self.key_positions = self.generator.key_positions
        self.door_positions = self.generator.door_positions
        self.enemy_spawns = self.generator.enemy_spawns
        self.camera_positions = self.generator.camera_positions
        self.trap_positions = self.generator.trap_positions
        self.hiding_spot_positions = self.generator.hiding_spot_positions
        self.lever_positions = getattr(self.generator, 'lever_positions', [])
        
        # Level metadata
        self.level_number = 1
        self.level_name = "Unnamed Level"
        self.is_completed = False
        
        # Collected/modified state
        self.collected_keys: set = set()
        self.opened_doors: set = set()
    
    @classmethod
    def load_from_file(cls, path: str) -> 'Level':
        """Load level from JSON file."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            get_logger().error(f"Level file not found: {path}")
            raise
        except json.JSONDecodeError as e:
            get_logger().error(f"Invalid JSON in level file {path}: {e}")
            raise
        except Exception as e:
            get_logger().error(f"Failed to load level from {path}: {e}", exc_info=True)
            raise
        
        width = data.get("width", 25)
        height = data.get("height", 20)
        
        # Create blank generator/cells
        generator = MazeGenerator(width, height)
        # We need to manually populate cells
        generator._init_walls() 
        
        # Load cells
        for cell_data in data.get("cells", []):
            x, y = cell_data["x"], cell_data["y"]
            cell_type_name = cell_data["type"]
            # Convert string to Enum
            cell_type = getattr(CellType, cell_type_name, CellType.WALL)
            
            if 0 <= x < width and 0 <= y < height:
                generator.cells[(x, y)] = Cell(x, y, cell_type)
                if cell_data.get("is_locked"):
                    generator.cells[(x, y)].is_locked = True
        
        # Load objects
        objects = data.get("objects", {})
        generator.spawn_point = tuple(objects.get("spawn_point", (1, 1)))
        generator.exit_point = tuple(objects.get("exit_point", (width-2, height-2)))
        generator.key_positions = [tuple(p) for p in objects.get("key_positions", [])]
        generator.door_positions = [tuple(p) for p in objects.get("door_positions", [])]
        generator.enemy_spawns = [tuple(p) for p in objects.get("enemy_spawns", [])]
        generator.camera_positions = [tuple(p) for p in objects.get("camera_positions", [])]
        generator.trap_positions = [tuple(p) for p in objects.get("trap_positions", [])]
        generator.hiding_spot_positions = [tuple(p) for p in objects.get("hiding_spot_positions", [])]
        generator.lever_positions = [tuple(p) for p in objects.get("lever_positions", [])]
        
        level = cls.__new__(cls)
        level.generator = generator
        level.width = width
        level.height = height
        level.cells = generator.cells
        level.rooms = [] # Custom levels might not use rooms concept
        
        level.spawn_point = generator.spawn_point
        level.exit_point = generator.exit_point
        level.key_positions = generator.key_positions
        level.door_positions = generator.door_positions
        level.enemy_spawns = generator.enemy_spawns
        level.camera_positions = generator.camera_positions
        level.trap_positions = generator.trap_positions
        level.hiding_spot_positions = generator.hiding_spot_positions
        level.lever_positions = getattr(generator, 'lever_positions', [])
        
        level.level_number = data.get("level_number", 0)
        level.level_name = data.get("level_name", "Custom Level")
        level.is_completed = False
        level.collected_keys = set()
        level.opened_doors = set()
        
        return level

    @classmethod
    def from_campaign(cls, level_number: int) -> 'Level':
        """Create a campaign level (try JSON first)."""
        # Try finding custom file
        filename = f"levels/level_{level_number}.json"
        # Check absolute path relative to CWD
        if os.path.exists(filename):
            get_logger().info(f"Loading custom file: {filename}")
            return cls.load_from_file(filename)
            
        generator = create_campaign_level(level_number)
        
        level = cls.__new__(cls)
        level.generator = generator
        level.width = generator.width
        level.height = generator.height
        level.cells = generator.cells
        level.rooms = generator.rooms
        level.spawn_point = generator.spawn_point
        level.exit_point = generator.exit_point
        level.key_positions = generator.key_positions
        level.door_positions = generator.door_positions
        level.enemy_spawns = generator.enemy_spawns
        level.camera_positions = generator.camera_positions
        level.trap_positions = generator.trap_positions
        level.hiding_spot_positions = generator.hiding_spot_positions
        level.level_number = level_number
        level.level_name = f"Level {level_number}"
        level.is_completed = False
        level.collected_keys = set()
        level.opened_doors = set()
        
        return level
    
    @classmethod
    def from_endless(cls, floor_number: int) -> 'Level':
        """Create an endless mode level."""
        generator = create_endless_level(floor_number)
        
        level = cls.__new__(cls)
        level.generator = generator
        level.width = generator.width
        level.height = generator.height
        level.cells = generator.cells
        level.rooms = generator.rooms
        level.spawn_point = generator.spawn_point
        level.exit_point = generator.exit_point
        level.key_positions = generator.key_positions
        level.door_positions = generator.door_positions
        level.enemy_spawns = generator.enemy_spawns
        level.camera_positions = generator.camera_positions
        level.trap_positions = generator.trap_positions
        level.hiding_spot_positions = generator.hiding_spot_positions
        level.hiding_spot_positions = generator.hiding_spot_positions
        level.boss_button_positions = generator.boss_button_positions
        
        # Determine boss spawn (center of arena)
        # MazeGenerator._generate_boss_arena sets spawn_point to center
        # But for boss level, player spawns at entrance, boss at center/end?
        # Let's assume generator.boss_spawn_pos exists or we use center
        level.boss_spawn_pos = getattr(generator, 'boss_spawn_pos', (generator.width/2, generator.height/2))
        
        level.level_number = floor_number
        level.level_name = f"Floor {floor_number}"
        level.is_completed = False
        level.collected_keys = set()
        level.opened_doors = set()
        
        return level
    
    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        """Get cell at position."""
        return self.cells.get((x, y))
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable."""
        cell = self.get_cell(x, y)
        if cell is None:
            return False
        
        # Check if it's a door
        if cell.cell_type == CellType.DOOR:
            # Door is only walkable if it has been explicitly opened
            # (added to opened_doors set via interaction)
            return (x, y) in self.opened_doors
        
        return cell.is_walkable()
    
    def collect_key(self, x: int, y: int) -> bool:
        """Mark a key as collected."""
        pos = (x, y)
        if pos in self.key_positions and pos not in self.collected_keys:
            self.collected_keys.add(pos)
            # Change cell type
            if pos in self.cells:
                self.cells[pos].cell_type = CellType.FLOOR
            return True
        return False
    
    def open_door(self, x: int, y: int) -> bool:
        """Mark a door as opened."""
        pos = (x, y)
        if pos in self.door_positions and pos not in self.opened_doors:
            self.opened_doors.add(pos)
            if pos in self.cells:
                self.cells[pos].is_locked = False
            return True
        return False
    
    def get_enemy_configs(self) -> List[Dict]:
        """Get enemy spawn configurations for this level."""
        configs = []
        
        for i, pos in enumerate(self.enemy_spawns):
            # Assign enemy types based on index
            enemy_type = [
                EnemyType.PATROL,
                EnemyType.SIGHT_GUARD,
                EnemyType.SOUND_HUNTER,
                EnemyType.TRACKER
            ][i % 4]
            
            configs.append({
                "x": pos[0],
                "y": pos[1],
                "type": enemy_type
            })
        
        return configs
    
    def to_dict(self) -> dict:
        """Serialize level to dictionary."""
        cell_data = []
        for pos, cell in self.cells.items():
            # Only save non-walls to save space? Or save everything for correctness.
            # Editor might assume defaults.
            # Let's save all cells that are not strictly default WALL unless generator assumes WALL.
            # Generator._init_walls sets all to WALL.
            # So saving differences is better but saving all is safer.
            c = {
                "x": pos[0], "y": pos[1], 
                "type": cell.cell_type.name
            }
            if cell.is_locked:
                c["is_locked"] = True
            cell_data.append(c)
            
        return {
            "width": self.width,
            "height": self.height,
            "level_number": self.level_number,
            "level_name": self.level_name,
            "cells": cell_data,
            "objects": {
                "spawn_point": self.spawn_point,
                "exit_point": self.exit_point,
                "key_positions": self.key_positions,
                "door_positions": self.door_positions,
                "enemy_spawns": self.enemy_spawns,
                "camera_positions": self.camera_positions,
                "trap_positions": self.trap_positions,
                "hiding_spot_positions": self.hiding_spot_positions
            }
        }
    
    def save_to_file(self, path: str):
        """Save level to JSON file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            
            data = self.to_dict()
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            get_logger().info(f"Saved to {path}")
        except OSError as e:
            get_logger().error(f"Failed to create directory or write file {path}: {e}", exc_info=True)
            raise
        except Exception as e:
            get_logger().error(f"Failed to save level to {path}: {e}", exc_info=True)
            raise
    
    def __str__(self) -> str:
        """String representation for debugging."""
        lines = [f"Level: {self.level_name} ({self.width}x{self.height})"]
        lines.append(f"Spawn: {self.spawn_point}, Exit: {self.exit_point}")
        lines.append(f"Keys: {len(self.key_positions)}, Doors: {len(self.door_positions)}")
        lines.append(f"Enemies: {len(self.enemy_spawns)}")
        return "\n".join(lines)