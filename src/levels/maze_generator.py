"""
Maze Bourne - Enhanced Procedural Maze Generator
BSP, Recursive Backtracking, and Room+Corridor algorithms
"""

import random
from typing import List, Tuple, Optional, Set, Dict
from dataclasses import dataclass
from enum import Enum

from src.core.constants import (
    CellType, LEVEL_SIZES, 
    MIN_ROOMS, MAX_ROOMS, MIN_ROOM_SIZE, MAX_ROOM_SIZE, CORRIDOR_WIDTH
)
from src.core.logger import get_logger


@dataclass
class Room:
    """A rectangular room in the maze."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def intersects(self, other: 'Room', padding: int = 1) -> bool:
        """Check if this room intersects another with optional padding."""
        return (
            self.x - padding < other.x + other.width and
            self.x + self.width + padding > other.x and
            self.y - padding < other.y + other.height and
            self.y + self.height + padding > other.y
        )


@dataclass
class Cell:
    """A single cell in the maze grid."""
    x: int
    y: int
    cell_type: CellType
    is_locked: bool = False
    is_active: bool = False
    object_id: str = ""
    
    def is_walkable(self) -> bool:
        """Check if cell can be walked through."""
        if self.cell_type == CellType.WALL:
            return False
        if self.cell_type == CellType.VOID:
            return False
        if self.cell_type == CellType.DOOR and self.is_locked:
            return False
        if self.cell_type == CellType.PRIVACY_DOOR and self.is_locked:
            return False
        return True


class MazeGenerator:
    """
    Enhanced procedural maze generator with multiple algorithms:
    - BSP (Binary Space Partition) for room-based dungeons
    - Recursive Backtracking for classic mazes
    - Room+Corridor hybrid for mixed layouts
    """
    
    def __init__(self, width: int, height: int, seed: Optional[int] = None):
        self.width = width
        self.height = height
        
        if seed is not None:
            random.seed(seed)
        
        # Grid storage
        self.cells: Dict[Tuple[int, int], Cell] = {}
        self.rooms: List[Room] = []
        
        # Special positions
        self.spawn_point: Tuple[int, int] = (1, 1)
        self.exit_point: Tuple[int, int] = (width - 2, height - 2)
        
        # Object positions
        self.key_positions: List[Tuple[int, int]] = []
        self.door_positions: List[Tuple[int, int]] = []
        self.enemy_spawns: List[Tuple[int, int]] = []
        self.camera_positions: List[Tuple[int, int]] = []
        self.trap_positions: List[Tuple[int, int]] = []
        self.hiding_spot_positions: List[Tuple[int, int]] = []
        self.lever_positions: List[Tuple[int, int]] = []
        self.lever_positions: List[Tuple[int, int]] = []
        self.boss_button_positions: List[Tuple[int, int]] = []
        self.boss_spawn_pos: Tuple[int, int] = (0, 0)
    
    def generate(self, algorithm: str = "bsp") -> 'MazeGenerator':
        """Generate a maze using the specified algorithm."""
        # Initialize all cells as walls
        self._init_walls()

        if algorithm == "boss_arena":
            self._generate_boss_arena()
            return self
        
        if algorithm == "bsp":
            self._generate_bsp()
        elif algorithm == "backtrack":
            self._generate_recursive_backtracking()
        elif algorithm == "rooms":
            self._generate_room_corridor()
        elif algorithm == "endless":
             # Endless mode: Hybrid of Rooms and winding Alleys
             # Start with sparse rooms, fill rest with backtracking
             self._generate_room_corridor(num_rooms=5)  # Fewer rooms, more alleys
        else:
            self._generate_bsp()  # Default
        
        # Place spawn and exit
        self._place_spawn_exit()
        
        # Place interactive objects
        self._place_objects()
        
        # Special Door Logic for Endless: Ensure alleys have privacy
        if algorithm == "endless":
            self._place_endless_doors()
        
        # Ensure solvability
        self._ensure_connectivity()
        
        return self
        
    def _place_endless_doors(self):
        """Place privacy doors at strategic points in corridors for Endless Mode."""
        from src.core.constants import PRIVACY_DOOR_PLACEMENT_RATE
        
        # For 2-tile-wide corridors, we look for:
        # 1. Floor tiles with exactly 1 wall neighbor (corridor edge) 
        # 2. Place doors randomly along corridors at intervals
        
        placed_doors = set()  # Track door positions to avoid clustering
        
        for y in range(2, self.height - 2):
            for x in range(2, self.width - 2):
                cell = self.cells[(x, y)]
                if cell.cell_type != CellType.FLOOR:
                    continue
                
                # Skip if door already placed nearby (within 4 tiles Manhattan distance)
                too_close = any(abs(x - dx) + abs(y - dy) < 4 for dx, dy in placed_doors)
                if too_close:
                    continue
                
                # Check wall neighbors
                left = self.cells.get((x-1, y))
                right = self.cells.get((x+1, y))
                top = self.cells.get((x, y-1))
                bottom = self.cells.get((x, y+1))
                
                left_wall = left and left.cell_type == CellType.WALL
                right_wall = right and right.cell_type == CellType.WALL
                top_wall = top and top.cell_type == CellType.WALL
                bottom_wall = bottom and bottom.cell_type == CellType.WALL
                
                n_walls = sum([left_wall, right_wall, top_wall, bottom_wall])
                
                # Corridor edge: exactly 1 wall neighbor (edge of 2-wide corridor)
                # Place doors at some corridor positions
                if n_walls == 1 and random.random() < PRIVACY_DOOR_PLACEMENT_RATE * 0.3:
                    self.cells[(x, y)].cell_type = CellType.PRIVACY_DOOR
                    self.cells[(x, y)].is_locked = True
                    self.door_positions.append((x, y))
                    placed_doors.add((x, y))
                
                # Also place doors at narrow spots (2 walls on adjacent sides - corner-like)
                elif n_walls == 2 and random.random() < PRIVACY_DOOR_PLACEMENT_RATE * 0.5:
                    # Check if walls are adjacent (corner) not opposite
                    is_corner = ((left_wall and top_wall) or (left_wall and bottom_wall) or
                                 (right_wall and top_wall) or (right_wall and bottom_wall))
                    if not is_corner:  # Walls are opposite - actual chokepoint
                        self.cells[(x, y)].cell_type = CellType.PRIVACY_DOOR
                        self.cells[(x, y)].is_locked = True
                        self.door_positions.append((x, y))
                        placed_doors.add((x, y))
    
    def _init_walls(self):
        """Initialize grid with all walls."""
        for y in range(self.height):
            for x in range(self.width):
                self.cells[(x, y)] = Cell(x, y, CellType.WALL)
    
    # =========================================================================
    # BSP ALGORITHM
    # =========================================================================
    
    def _generate_bsp(self, min_size: int = 6):
        """Generate using Binary Space Partition."""
        
        class BSPNode:
            def __init__(self, x, y, w, h):
                self.x, self.y, self.width, self.height = x, y, w, h
                self.left = None
                self.right = None
                self.room = None
            
            def split(self, min_size):
                if self.left or self.right:
                    return False
                
                # Decide split direction
                if self.width > self.height and self.width / self.height >= 1.25:
                    horizontal = False
                elif self.height > self.width and self.height / self.width >= 1.25:
                    horizontal = True
                else:
                    horizontal = random.random() > 0.5
                
                max_size = (self.height if horizontal else self.width) - min_size
                if max_size <= min_size:
                    return False
                
                split = random.randint(min_size, max_size)
                
                if horizontal:
                    self.left = BSPNode(self.x, self.y, self.width, split)
                    self.right = BSPNode(self.x, self.y + split, self.width, self.height - split)
                else:
                    self.left = BSPNode(self.x, self.y, split, self.height)
                    self.right = BSPNode(self.x + split, self.y, self.width - split, self.height)
                
                return True
            
            def create_rooms(self, generator):
                if self.left or self.right:
                    if self.left:
                        self.left.create_rooms(generator)
                    if self.right:
                        self.right.create_rooms(generator)
                    
                    # Connect sibling rooms
                    if self.left and self.right:
                        generator._connect_rooms(
                            self.left.get_room(),
                            self.right.get_room()
                        )
                else:
                    # Create room
                    room_w = random.randint(MIN_ROOM_SIZE, min(MAX_ROOM_SIZE, self.width - 2))
                    room_h = random.randint(MIN_ROOM_SIZE, min(MAX_ROOM_SIZE, self.height - 2))
                    room_x = self.x + random.randint(1, self.width - room_w - 1)
                    room_y = self.y + random.randint(1, self.height - room_h - 1)
                    
                    self.room = Room(room_x, room_y, room_w, room_h)
                    generator.rooms.append(self.room)
                    generator._carve_room(self.room)
            
            def get_room(self):
                if self.room:
                    return self.room
                if self.left:
                    left_room = self.left.get_room()
                    if left_room:
                        return left_room
                if self.right:
                    return self.right.get_room()
                return None
        
        # Create BSP tree
        root = BSPNode(1, 1, self.width - 2, self.height - 2)
        
        # Split recursively
        nodes = [root]
        while nodes:
            node = nodes.pop(0)
            if node.split(min_size):
                nodes.append(node.left)
                nodes.append(node.right)
        
        # Create rooms
        root.create_rooms(self)
    
    # =========================================================================
    # RECURSIVE BACKTRACKING
    # =========================================================================
    
    def _generate_recursive_backtracking(self):
        """Generate using recursive backtracking (DFS maze)."""
        # Start from a random odd position
        start_x = random.randrange(1, self.width - 1, 2)
        start_y = random.randrange(1, self.height - 1, 2)
        
        stack = [(start_x, start_y)]
        self.cells[(start_x, start_y)].cell_type = CellType.FLOOR
        
        while stack:
            x, y = stack[-1]
            
            # Get unvisited neighbors (2 cells away)
            neighbors = []
            for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
                nx, ny = x + dx, y + dy
                if 1 <= nx < self.width - 1 and 1 <= ny < self.height - 1:
                    if self.cells[(nx, ny)].cell_type == CellType.WALL:
                        neighbors.append((nx, ny, dx // 2, dy // 2))
            
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                # Carve passage
                self.cells[(x + dx, y + dy)].cell_type = CellType.FLOOR
                self.cells[(nx, ny)].cell_type = CellType.FLOOR
                stack.append((nx, ny))
            else:
                stack.pop()
    
    # =========================================================================
    # ROOM + CORRIDOR
    # =========================================================================
    
    def _generate_room_corridor(self, num_rooms: int = None):
        """Generate using random room placement and corridor connection."""
        num_rooms = num_rooms or random.randint(MIN_ROOMS, MAX_ROOMS)
        
        attempts = 0
        max_attempts = num_rooms * 20
        
        while len(self.rooms) < num_rooms and attempts < max_attempts:
            attempts += 1
            
            # Random room size
            room_w = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
            room_h = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
            
            # Random position
            room_x = random.randint(2, self.width - room_w - 2)
            room_y = random.randint(2, self.height - room_h - 2)
            
            new_room = Room(room_x, room_y, room_w, room_h)
            
            # Check overlap
            overlaps = False
            for room in self.rooms:
                if new_room.intersects(room, padding=2):
                    overlaps = True
                    break
            
            if not overlaps:
                self.rooms.append(new_room)
                self._carve_room(new_room)
                
                # Connect to previous room
                if len(self.rooms) > 1:
                    self._connect_rooms(self.rooms[-2], new_room)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _carve_room(self, room: Room):
        """Carve out a room."""
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                if 0 < x < self.width - 1 and 0 < y < self.height - 1:
                    self.cells[(x, y)].cell_type = CellType.FLOOR
    
    def _connect_rooms(self, room1: Room, room2: Room):
        """Connect two rooms with a corridor."""
        x1, y1 = room1.center
        x2, y2 = room2.center
        
        # L-shaped corridor
        if random.random() > 0.5:
            self._carve_h_corridor(x1, x2, y1)
            self._carve_v_corridor(y1, y2, x2)
        else:
            self._carve_v_corridor(y1, y2, x1)
            self._carve_h_corridor(x1, x2, y2)
    
    def _carve_h_corridor(self, x1: int, x2: int, y: int):
        """Carve horizontal corridor (width 2)."""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for dy in range(2):  # Width 2
                cy = y + dy
                if 0 < x < self.width - 1 and 0 < cy < self.height - 1:
                    self.cells[(x, cy)].cell_type = CellType.FLOOR
    
    def _carve_v_corridor(self, y1: int, y2: int, x: int):
        """Carve vertical corridor (width 2)."""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for dx in range(2):  # Width 2
                cx = x + dx
                if 0 < cx < self.width - 1 and 0 < y < self.height - 1:
                    self.cells[(cx, y)].cell_type = CellType.FLOOR
    
    def _place_spawn_exit(self):
        """Place spawn and exit points in distant rooms."""
        if len(self.rooms) >= 2:
            # Spawn in first room
            spawn_room = self.rooms[0]
            self.spawn_point = spawn_room.center
            self.cells[self.spawn_point].cell_type = CellType.SPAWN
            
            # Exit in last room
            exit_room = self.rooms[-1]
            self.exit_point = exit_room.center
            self.cells[self.exit_point].cell_type = CellType.EXIT
        else:
            # Find floor cells
            floor_cells = [pos for pos, cell in self.cells.items() 
                          if cell.cell_type == CellType.FLOOR]
            
            if len(floor_cells) >= 2:
                self.spawn_point = floor_cells[0]
                self.cells[self.spawn_point].cell_type = CellType.SPAWN
                
                # Exit furthest from spawn
                spawn_x, spawn_y = self.spawn_point
                max_dist = 0
                for pos in floor_cells:
                    dist = abs(pos[0] - spawn_x) + abs(pos[1] - spawn_y)
                    if dist > max_dist:
                        max_dist = dist
                        self.exit_point = pos
                
                self.cells[self.exit_point].cell_type = CellType.EXIT
    
    def _place_objects(self):
        """Place keys, doors, enemies, etc."""
        floor_cells = [pos for pos, cell in self.cells.items()
                      if cell.cell_type == CellType.FLOOR]
        
        if not floor_cells:
            return
        
        # Calculate number of objects based on maze size
        area = self.width * self.height
        num_keys = max(1, min(5, area // 150))
        num_enemies = max(2, min(8, area // 100))
        num_traps = max(1, min(4, area // 200))
        num_cameras = max(0, min(3, area // 250))
        num_hiding = max(2, min(6, area // 120))
        
        random.shuffle(floor_cells)
        
        # Place keys
        for i in range(min(num_keys, len(floor_cells))):
            pos = floor_cells.pop()
            self.key_positions.append(pos)
            self.cells[pos].cell_type = CellType.KEY
        
        # Place enemies (in rooms away from spawn)
        spawn_x, spawn_y = self.spawn_point
        distant_cells = sorted(
            floor_cells,
            key=lambda p: abs(p[0] - spawn_x) + abs(p[1] - spawn_y),
            reverse=True
        )
        
        for i in range(min(num_enemies, len(distant_cells))):
            pos = distant_cells[i]
            self.enemy_spawns.append(pos)
            if pos in floor_cells:
                floor_cells.remove(pos)
        
        # Place traps
        for i in range(min(num_traps, len(floor_cells))):
            pos = floor_cells.pop()
            self.trap_positions.append(pos)
            self.cells[pos].cell_type = CellType.TRAP
        
        # Place cameras
        for i in range(min(num_cameras, len(floor_cells))):
            pos = floor_cells.pop()
            self.camera_positions.append(pos)
            self.cells[pos].cell_type = CellType.CAMERA
        
        # Place hiding spots
        for i in range(min(num_hiding, len(floor_cells))):
            pos = floor_cells.pop()
            self.hiding_spot_positions.append(pos)
            self.cells[pos].cell_type = CellType.HIDING_SPOT
        
        # Place doors in corridors (narrow passages)
        self._place_doors()
    
    def _place_doors(self):
        """Place doors in corridor chokepoints."""
        for pos, cell in list(self.cells.items()):
            if cell.cell_type != CellType.FLOOR:
                continue
            
            x, y = pos
            
            # Check if this is a chokepoint (2 walls on opposite sides)
            h_walls = (
                self.cells.get((x - 1, y), Cell(0, 0, CellType.WALL)).cell_type == CellType.WALL and
                self.cells.get((x + 1, y), Cell(0, 0, CellType.WALL)).cell_type == CellType.WALL
            )
            v_walls = (
                self.cells.get((x, y - 1), Cell(0, 0, CellType.WALL)).cell_type == CellType.WALL and
                self.cells.get((x, y + 1), Cell(0, 0, CellType.WALL)).cell_type == CellType.WALL
            )
            
            if (h_walls or v_walls) and random.random() < 0.15:
                self.cells[pos].cell_type = CellType.DOOR
                self.cells[pos].is_locked = True
                self.door_positions.append(pos)
    
    def _ensure_connectivity(self):
        """Ensure all floor cells are reachable from spawn."""
        # BFS from spawn
        if self.spawn_point not in self.cells:
            return
        
        visited = set()
        queue = [self.spawn_point]
        
        while queue:
            pos = queue.pop(0)
            if pos in visited:
                continue
            visited.add(pos)
            
            x, y = pos
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_pos = (x + dx, y + dy)
                cell = self.cells.get(next_pos)
                if cell and cell.is_walkable() and next_pos not in visited:
                    queue.append(next_pos)
        
        # Check if exit is reachable
        if self.exit_point not in visited:
            # Create direct path
            x1, y1 = self.spawn_point
            x2, y2 = self.exit_point
            self._carve_h_corridor(x1, x2, y1)
            self._carve_v_corridor(y1, y2, x2)
    
    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        """Get cell at position."""
        return self.cells.get((x, y))
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable."""
        cell = self.get_cell(x, y)
        return cell is not None and cell.is_walkable()

    def _generate_boss_arena(self):
        """Generate a large open arena for boss battles."""
        # Ensure room is large enough
        w, h = self.width, self.height
        
        # Center room (leave 2 tile border)
        for y in range(2, h - 2):
            for x in range(2, w - 2):
                self.cells[(x, y)].cell_type = CellType.FLOOR
        
        # Spawn point (bottom center)
        self.spawn_point = (w // 2, h - 3)
        
        # Boss buttons in 4 corners (inset by 3)
        button_coords = [
            (3, 3), (w - 4, 3), 
            (3, h - 4), (w - 4, h - 4)
        ]
        
        for bx, by in button_coords:
            self.boss_button_positions.append((bx, by))
            # Optional: Place a pillar/wall near the button for cover
            self.cells[(bx + 1, by + 1)].cell_type = CellType.WALL
        
        # Exit (Top center, initially locked?)
        # For now, just place exit
        self.exit_point = (w // 2, 2)
        self.exit_point = (w // 2, 2)
        self.cells[self.exit_point].cell_type = CellType.EXIT
        
        # Boss spawns in center
        self.boss_spawn_pos = (w // 2, h // 2)
        
        get_logger().debug(f"Generated Boss Arena ({w}x{h})")


def create_level(width: int, height: int, algorithm: str = "bsp", 
                 seed: Optional[int] = None) -> MazeGenerator:
    """Factory function to create a new level."""
    return MazeGenerator(width, height, seed).generate(algorithm)

    



def create_campaign_level(level_num: int) -> MazeGenerator:
    """Create a campaign level based on level number."""
    # Determine size
    if level_num <= 2:
        width, height = 15, 15
        algorithm = "rooms"
    elif level_num <= 5:
        width, height = 20, 20
        algorithm = "bsp"
    elif level_num <= 8:
        width, height = 30, 30
        algorithm = "bsp"
    else:
        width, height = 40, 40
        algorithm = "bsp"
    
    return MazeGenerator(width, height, seed=level_num * 12345).generate(algorithm)


def create_endless_level(floor_num: int) -> MazeGenerator:
    """Create an endless mode level."""
    # Boss level every 10 floors
    if floor_num > 0 and floor_num % 10 == 0:
        size = 20  # Fixed arena size
        return MazeGenerator(size, size).generate("boss_arena")
    
    base_size = 25
    size_increase = min(15, floor_num * 2)
    size = base_size + size_increase
    
    return MazeGenerator(size, size).generate("endless")