"""
A* Pathfinding Algorithm for Smart Enemy AI
"""
import heapq
from typing import List, Optional, Tuple, Set
from src.utils.grid import GridPos
from src.levels.maze_generator import CellType

class Node:
    """Node for A* pathfinding algorithm."""
    
    def __init__(self, pos: GridPos, g_cost: float = 0, h_cost: float = 0, parent=None):
        self.pos = pos
        self.g_cost = g_cost  # Distance from start
        self.h_cost = h_cost  # Heuristic distance to goal
        self.f_cost = g_cost + h_cost  # Total cost
        self.parent = parent
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __eq__(self, other):
        return self.pos == other.pos

class AStarPathfinder:
    """A* pathfinding implementation for game entities."""
    
    def __init__(self, maze: dict):
        self.maze = maze
        self.cache = {}  # Simple path cache for performance
        self.max_cache_size = 1000
        self.max_iterations = 2000  # Prevent DoS attacks
        self.performance_stats = {
            'total_calls': 0,
            'cache_hits': 0,
            'timeout_failures': 0
        }
    
    def find_path(self, start: GridPos, goal: GridPos, max_distance: int = 50) -> List[GridPos]:
        """
        Find optimal path from start to goal using A* algorithm.
        
        Args:
            start: Starting position
            goal: Target position
            max_distance: Maximum search distance to prevent infinite loops
            
        Returns:
            List of GridPos representing the path, empty list if no path found
        """
        self.performance_stats['total_calls'] += 1
        
        # Check cache first
        cache_key = (start, goal)
        if cache_key in self.cache:
            self.performance_stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        # Validate inputs
        if not self._is_valid_position(start) or not self._is_valid_position(goal):
            return []
        
        if start == goal:
            return [start]
        
        # Initialize A* structures
        open_set = []
        closed_set: Set[GridPos] = set()
        
        start_node = Node(start, 0, self._heuristic(start, goal))
        heapq.heappush(open_set, start_node)
        
        node_map = {start: start_node}
        iterations = 0
        
        while open_set and iterations < self.max_iterations:
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            
            # Check if we've reached the goal
            if current.pos == goal:
                path = self._reconstruct_path(current)
                
                # Cache the result
                if len(self.cache) < self.max_cache_size:
                    self.cache[cache_key] = path
                
                return path
            
            closed_set.add(current.pos)
            iterations += 1
            
            # Check neighbors
            for neighbor_pos in self._get_neighbors(current.pos):
                if neighbor_pos in closed_set:
                    continue
                
                if not self._is_walkable(neighbor_pos):
                    continue
                
                # Calculate costs
                g_cost = current.g_cost + self._distance(current.pos, neighbor_pos)
                h_cost = self._heuristic(neighbor_pos, goal)
                
                # Skip if this would exceed max distance
                if g_cost > max_distance:
                    continue
                
                # Check if this path to neighbor is better
                if neighbor_pos in node_map:
                    neighbor_node = node_map[neighbor_pos]
                    if g_cost < neighbor_node.g_cost:
                        neighbor_node.g_cost = g_cost
                        neighbor_node.f_cost = g_cost + h_cost
                        neighbor_node.parent = current
                else:
                    neighbor_node = Node(neighbor_pos, g_cost, h_cost, current)
                    node_map[neighbor_pos] = neighbor_node
                    heapq.heappush(open_set, neighbor_node)
        
        # No path found (or timed out)
        if iterations >= self.max_iterations:
            self.performance_stats['timeout_failures'] += 1
            
        return []
    
    def find_path_avoiding_positions(self, start: GridPos, goal: GridPos, 
                                   avoid_positions: Set[GridPos], 
                                   max_distance: int = 50) -> List[GridPos]:
        """
        Find path while avoiding specific positions.
        
        Args:
            start: Starting position
            goal: Target position
            avoid_positions: Set of positions to avoid
            max_distance: Maximum search distance
            
        Returns:
            List of GridPos representing the path
        """
        # Temporarily mark avoid positions as non-walkable
        original_cache = self.cache.copy()
        self.cache.clear()  # Clear cache since we're changing constraints
        
        # Store original maze state
        original_states = {}
        for pos in avoid_positions:
            if pos in self.maze:
                original_states[pos] = self.maze[pos].type
                # Temporarily mark as wall
                self.maze[pos].type = CellType.WALL
        
        try:
            path = self.find_path(start, goal, max_distance)
        finally:
            # Restore original maze state
            for pos, original_type in original_states.items():
                self.maze[pos].type = original_type
            
            # Restore cache
            self.cache = original_cache
        
        return path
    
    def _heuristic(self, pos1: GridPos, pos2: GridPos) -> float:
        """Manhattan distance heuristic."""
        return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y)
    
    def _distance(self, pos1: GridPos, pos2: GridPos) -> float:
        """Actual distance between adjacent positions."""
        dx = abs(pos1.x - pos2.x)
        dy = abs(pos1.y - pos2.y)
        
        # Diagonal movement costs more
        if dx == 1 and dy == 1:
            return 1.414  # sqrt(2)
        else:
            return 1.0
    
    def _get_neighbors(self, pos: GridPos) -> List[GridPos]:
        """Get all valid neighbor positions."""
        neighbors = []
        
        # 4-directional movement (no diagonals for simplicity)
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dx, dy in directions:
            neighbor = GridPos(pos.x + dx, pos.y + dy)
            if self._is_valid_position(neighbor):
                neighbors.append(neighbor)
        
        return neighbors
    
    def _is_valid_position(self, pos: GridPos) -> bool:
        """Check if position is within maze bounds."""
        return pos in self.maze
    
    def _is_walkable(self, pos: GridPos) -> bool:
        """Check if position can be walked through."""
        if not self._is_valid_position(pos):
            return False
        
        cell = self.maze[pos]
        return cell.is_walkable()
    
    def _reconstruct_path(self, end_node: Node) -> List[GridPos]:
        """Reconstruct path from end node back to start."""
        path = []
        current = end_node
        
        while current:
            path.append(current.pos)
            current = current.parent
        
        path.reverse()
        return path
    
    def clear_cache(self):
        """Clear the pathfinding cache."""
        self.cache.clear()

class PathfindingUtils:
    """Utility functions for pathfinding operations."""
    
    @staticmethod
    def simplify_path(path: List[GridPos], max_length: int = 10) -> List[GridPos]:
        """
        Simplify a path by removing unnecessary intermediate points.
        
        Args:
            path: Original path
            max_length: Maximum number of points in simplified path
            
        Returns:
            Simplified path
        """
        if len(path) <= max_length:
            return path
        
        # Take every nth point to reduce path length
        step = len(path) // max_length
        simplified = [path[0]]  # Always include start
        
        for i in range(step, len(path) - 1, step):
            simplified.append(path[i])
        
        simplified.append(path[-1])  # Always include end
        return simplified
    
    @staticmethod
    def get_next_move(current_pos: GridPos, path: List[GridPos]) -> Optional[GridPos]:
        """
        Get the next position to move to from current position.
        
        Args:
            current_pos: Current position
            path: Path to follow
            
        Returns:
            Next position to move to, or None if path is complete
        """
        if not path or current_pos not in path:
            return None
        
        current_index = path.index(current_pos)
        
        if current_index + 1 < len(path):
            return path[current_index + 1]
        
        return None  # Reached end of path