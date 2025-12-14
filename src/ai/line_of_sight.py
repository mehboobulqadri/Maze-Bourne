"""
Line of Sight Detection System
Implements raycasting for realistic enemy vision with obstacle blocking.
"""

from src.utils.grid import GridPos
from src.levels.maze_generator import CellType
import math

class LineOfSight:
    """Handles line of sight calculations with raycasting."""
    
    def __init__(self, maze):
        self.maze = maze
    
    def has_clear_sight(self, start: GridPos, target: GridPos, max_distance: float = 8.0) -> bool:
        """
        Check if there's a clear line of sight between two positions.
        
        Args:
            start: Starting position (enemy)
            target: Target position (player)
            max_distance: Maximum sight distance
            
        Returns:
            True if clear line of sight exists
        """
        distance = start.distance_to(target)
        if distance > max_distance:
            return False
        
        # Use Bresenham's line algorithm for raycasting
        return self._raycast(start, target)
    
    def _raycast(self, start: GridPos, end: GridPos) -> bool:
        """
        Cast a ray from start to end, checking for obstacles.
        
        Args:
            start: Starting position
            end: End position
            
        Returns:
            True if ray reaches end without hitting walls
        """
        x0, y0 = start.x, start.y
        x1, y1 = end.x, end.y
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        
        err = dx - dy
        x, y = x0, y0
        
        while True:
            pos = GridPos(x, y)
            
            # Check if current position blocks sight
            if self._blocks_sight(pos):
                return False
            
            # Reached target
            if x == x1 and y == y1:
                return True
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def _blocks_sight(self, pos: GridPos) -> bool:
        """
        Check if a position blocks line of sight.
        
        Args:
            pos: Position to check
            
        Returns:
            True if position blocks sight
        """
        if pos not in self.maze:
            return True  # Outside maze blocks sight
        
        cell = self.maze[pos]
        
        # Walls and doors block sight
        return cell.type in [CellType.WALL, CellType.DOOR]
    
    def get_vision_cone_positions(self, start: GridPos, direction: GridPos, 
                                cone_angle: float = 90.0, max_distance: float = 6.0) -> list:
        """
        Get all positions within a vision cone.
        
        Args:
            start: Starting position
            direction: Direction vector (normalized)
            cone_angle: Cone angle in degrees
            max_distance: Maximum vision distance
            
        Returns:
            List of GridPos within vision cone
        """
        visible_positions = []
        cone_rad = math.radians(cone_angle / 2)
        
        # Calculate direction angle
        dir_angle = math.atan2(direction.y, direction.x)
        
        # Check positions in a square around the start
        radius = int(max_distance) + 1
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                
                check_pos = GridPos(start.x + dx, start.y + dy)
                distance = start.distance_to(check_pos)
                
                if distance > max_distance:
                    continue
                
                # Check if position is within cone angle
                pos_angle = math.atan2(dy, dx)
                angle_diff = abs(pos_angle - dir_angle)
                
                # Handle angle wrapping
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                
                if angle_diff <= cone_rad:
                    # Check if position has clear sight
                    if self.has_clear_sight(start, check_pos, max_distance):
                        visible_positions.append(check_pos)
        
        return visible_positions

class VisionSystem:
    """Enhanced vision system with different vision types."""
    
    def __init__(self, maze):
        self.line_of_sight = LineOfSight(maze)
        
    def can_detect_player(self, enemy_pos: GridPos, player_pos: GridPos, 
                         vision_type: str = "omnidirectional", 
                         facing_direction: GridPos = None,
                         detection_range: float = 6.0) -> dict:
        """
        Comprehensive player detection system.
        
        Args:
            enemy_pos: Enemy position
            player_pos: Player position
            vision_type: Type of vision ("omnidirectional", "cone", "limited")
            facing_direction: Direction enemy is facing (for cone vision)
            detection_range: Maximum detection range
            
        Returns:
            Dict with detection info: {'detected': bool, 'confidence': float, 'type': str}
        """
        distance = enemy_pos.distance_to(player_pos)
        
        # Base detection check
        if distance > detection_range:
            return {'detected': False, 'confidence': 0.0, 'type': 'out_of_range'}
        
        has_sight = self.line_of_sight.has_clear_sight(enemy_pos, player_pos, detection_range)
        
        if not has_sight:
            return {'detected': False, 'confidence': 0.0, 'type': 'blocked'}
        
        # Vision type specific checks
        if vision_type == "omnidirectional":
            confidence = 1.0 - (distance / detection_range)
            return {'detected': True, 'confidence': confidence, 'type': 'omnidirectional'}
            
        elif vision_type == "cone" and facing_direction:
            # Check if player is in vision cone
            visible_positions = self.line_of_sight.get_vision_cone_positions(
                enemy_pos, facing_direction, cone_angle=90.0, max_distance=detection_range
            )
            
            if player_pos in visible_positions:
                confidence = 1.0 - (distance / detection_range)
                return {'detected': True, 'confidence': confidence, 'type': 'cone'}
            else:
                return {'detected': False, 'confidence': 0.0, 'type': 'outside_cone'}
                
        elif vision_type == "limited":
            # Reduced detection range and confidence
            limited_range = detection_range * 0.7
            if distance <= limited_range:
                confidence = 0.8 * (1.0 - (distance / limited_range))
                return {'detected': True, 'confidence': confidence, 'type': 'limited'}
            else:
                return {'detected': False, 'confidence': 0.0, 'type': 'limited_range'}
        
        # Default fallback
        confidence = 1.0 - (distance / detection_range)
        return {'detected': has_sight, 'confidence': confidence, 'type': 'default'}