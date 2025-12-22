"""
Enhanced Enemy Behavior States
Implements sophisticated AI state machine for realistic enemy behaviors.
"""

import random
import time
from src.utils.grid import GridPos
from src.ai.pathfinding import AStarPathfinder

class BehaviorState:
    """Base class for enemy behavior states."""
    
    def __init__(self, name: str):
        self.name = name
        self.enter_time = time.time()
        self.duration = 0.0  # 0 = infinite
        
    def enter(self, enemy):
        """Called when entering this state."""
        self.enter_time = time.time()
        
    def update(self, enemy, player, maze, dt) -> str:
        """Update behavior. Returns next state name or None to stay."""
        return None
        
    def exit(self, enemy):
        """Called when exiting this state."""
        pass
        
    def is_expired(self) -> bool:
        """Check if state duration has expired."""
        if self.duration <= 0:
            return False
        return time.time() - self.enter_time >= self.duration

class PatrolState(BehaviorState):
    """Enemy patrols predefined waypoints."""
    
    def __init__(self):
        super().__init__("PATROL")
        
    def enter(self, enemy):
        super().enter(enemy)
        if not hasattr(enemy, 'patrol_waypoints') or not enemy.patrol_waypoints:
            self._generate_patrol_route(enemy)
        enemy.patrol_index = 0
        enemy.patrol_wait_time = 0
        
    def update(self, enemy, player, maze, dt) -> str:
        # Check for player detection
        if hasattr(enemy, 'vision_system'):
            detection = enemy.vision_system.can_detect_player(
                enemy.pos, player.pos, 
                vision_type="cone" if hasattr(enemy, 'facing_direction') else "omnidirectional",
                facing_direction=getattr(enemy, 'facing_direction', None),
                detection_range=enemy.detection_range
            )
            
            # Apply stealth modifiers to detection
            if detection['detected'] and hasattr(player, 'stealth_mechanics'):
                stealth_modifier = player.stealth_mechanics.get_detection_modifier_for_enemy(enemy, player)
                detection['confidence'] *= stealth_modifier
            
            if detection['detected'] and detection['confidence'] > 0.7:
                enemy.last_known_player_pos = player.pos
                enemy.detection_confidence = detection['confidence']
                return "ALERT"
        
        # Handle patrol movement
        if not enemy.patrol_waypoints:
            return "IDLE"
            
        current_target = enemy.patrol_waypoints[enemy.patrol_index]
        
        # Check if reached current waypoint
        if enemy.pos == current_target:
            enemy.patrol_wait_time += dt
            
            # Wait at waypoint for realistic behavior
            wait_duration = random.uniform(1.0, 3.0)
            if enemy.patrol_wait_time >= wait_duration:
                # Move to next waypoint
                enemy.patrol_index = (enemy.patrol_index + 1) % len(enemy.patrol_waypoints)
                enemy.patrol_wait_time = 0
                
                # Update facing direction for cone vision
                if hasattr(enemy, 'facing_direction') and enemy.patrol_waypoints:
                    next_waypoint = enemy.patrol_waypoints[enemy.patrol_index]
                    direction = GridPos(
                        next_waypoint.x - enemy.pos.x,
                        next_waypoint.y - enemy.pos.y
                    )
                    if direction.x != 0 or direction.y != 0:
                        enemy.facing_direction = direction
        else:
            # Move toward current target
            if hasattr(enemy, 'pathfinder') and enemy.pathfinder:
                path = enemy.pathfinder.find_path(enemy.pos, current_target)
                if len(path) > 1:
                    enemy.pos = path[1]
                    
                    # Update facing direction
                    if hasattr(enemy, 'facing_direction'):
                        direction = GridPos(path[1].x - path[0].x, path[1].y - path[0].y)
                        enemy.facing_direction = direction
        
        return None
        
    def _generate_patrol_route(self, enemy):
        """Generate patrol waypoints around spawn area."""
        enemy.patrol_waypoints = []
        spawn_area_size = 4
        
        # Create waypoints in a pattern around spawn
        for offset in [(0, spawn_area_size), (spawn_area_size, 0), 
                      (0, -spawn_area_size), (-spawn_area_size, 0)]:
            waypoint = GridPos(
                enemy.spawn_pos.x + offset[0],
                enemy.spawn_pos.y + offset[1]
            )
            # Only add if position is walkable
            if hasattr(enemy, 'can_move_to') and enemy.can_move_to(waypoint):
                enemy.patrol_waypoints.append(waypoint)
        
        # Fallback to spawn if no valid waypoints
        if not enemy.patrol_waypoints:
            enemy.patrol_waypoints = [enemy.spawn_pos]

class AlertState(BehaviorState):
    """Enemy is suspicious and investigating."""
    
    def __init__(self):
        super().__init__("ALERT")
        self.duration = 5.0  # 5 seconds of alert
        
    def enter(self, enemy):
        super().enter(enemy)
        enemy.move_speed_multiplier = 1.3  # Move faster when alert
        
    def update(self, enemy, player, maze, dt) -> str:
        # Check for direct player sight
        if hasattr(enemy, 'vision_system'):
            detection = enemy.vision_system.can_detect_player(
                enemy.pos, player.pos,
                detection_range=enemy.detection_range * 1.5  # Extended alert range
            )
            
            # Apply stealth modifiers
            if detection['detected'] and hasattr(player, 'stealth_mechanics'):
                stealth_modifier = player.stealth_mechanics.get_detection_modifier_for_enemy(enemy, player)
                detection['confidence'] *= stealth_modifier
            
            if detection['detected'] and detection['confidence'] > 0.8:
                enemy.last_known_player_pos = player.pos
                return "CHASE"
        
        # Check if this is a sound investigation (for Sound Hunters)
        investigation_target = None
        if (hasattr(enemy, 'last_heard_sound_pos') and 
            enemy.last_heard_sound_pos and
            hasattr(enemy, 'sound_investigation_timer') and
            enemy.sound_investigation_timer > 0):
            investigation_target = enemy.last_heard_sound_pos
        elif hasattr(enemy, 'last_known_player_pos') and enemy.last_known_player_pos:
            investigation_target = enemy.last_known_player_pos
        
        # Move toward investigation target
        if investigation_target:
            if enemy.pos == investigation_target:
                # Reached investigation spot, start searching
                return "SEARCH"
            else:
                # Move toward investigation target
                if hasattr(enemy, 'pathfinder') and enemy.pathfinder:
                    path = enemy.pathfinder.find_path(enemy.pos, investigation_target)
                    if len(path) > 1:
                        enemy.pos = path[1]
        
        # Return to patrol if alert time expired
        if self.is_expired():
            return "PATROL"
        
        return None
        
    def exit(self, enemy):
        enemy.move_speed_multiplier = 1.0  # Reset speed

class SearchState(BehaviorState):
    """Enemy searches area for hidden player."""
    
    def __init__(self):
        super().__init__("SEARCH")
        self.duration = 8.0  # 8 seconds of searching
        
    def enter(self, enemy):
        super().enter(enemy)
        enemy.search_positions = self._generate_search_positions(enemy)
        enemy.search_index = 0
        
    def update(self, enemy, player, maze, dt) -> str:
        # Check for player detection during search
        if hasattr(enemy, 'vision_system'):
            detection = enemy.vision_system.can_detect_player(
                enemy.pos, player.pos,
                detection_range=enemy.detection_range * 0.8  # Slightly reduced while searching
            )
            
            if detection['detected'] and detection['confidence'] > 0.9:
                enemy.last_known_player_pos = player.pos
                return "CHASE"
        
        # Enhanced sound detection during search
        if hasattr(player, 'get_recent_sounds'):
            recent_sounds = player.get_recent_sounds(max_age=5.0)
            for sound in recent_sounds:
                distance = enemy.pos.distance_to(sound.pos)
                if distance <= enemy.sound_detection_range:
                    sound_intensity = sound.get_intensity_at_distance(distance)
                    if sound_intensity > 10:  # Lower threshold during search
                        enemy.last_heard_sound_pos = sound.pos
                        # Move towards sound instead of continuing search pattern
                        if hasattr(enemy, 'pathfinder') and enemy.pathfinder:
                            path = enemy.pathfinder.find_path(enemy.pos, sound.pos)
                            if len(path) > 1:
                                next_pos = path[1]
                                if enemy.can_move_to(next_pos, maze):
                                    enemy.pos = next_pos
                                    enemy.facing_direction = GridPos(
                                        next_pos.x - enemy.pos.x, 
                                        next_pos.y - enemy.pos.y
                                    )
                        return None  # Stay in search but move towards sound
        
        # Search behavior - check multiple positions
        if hasattr(enemy, 'search_positions') and enemy.search_positions:
            if enemy.search_index < len(enemy.search_positions):
                target = enemy.search_positions[enemy.search_index]
                
                if enemy.pos == target:
                    # Brief pause at search position instead of sleep
                    enemy.search_index += 1
                else:
                    # Move to search position
                    if hasattr(enemy, 'pathfinder') and enemy.pathfinder:
                        path = enemy.pathfinder.find_path(enemy.pos, target)
                        if len(path) > 1:
                            next_pos = path[1]
                            if enemy.can_move_to(next_pos, maze):
                                enemy.pos = next_pos
        
        # Give up searching after duration
        if self.is_expired():
            return "PATROL"
        
        return None
        
    def _generate_search_positions(self, enemy):
        """Generate positions to search around last known player location."""
        search_positions = []
        if not hasattr(enemy, 'last_known_player_pos') or enemy.last_known_player_pos is None:
            # Use current position as fallback
            center = enemy.pos
        else:
            center = enemy.last_known_player_pos
        search_radius = 3
        
        # Create search pattern around last known position
        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                if dx == 0 and dy == 0:
                    continue
                    
                pos = GridPos(center.x + dx, center.y + dy)
                if (hasattr(enemy, 'can_move_to') and 
                    enemy.can_move_to(pos) and 
                    pos != enemy.pos):
                    search_positions.append(pos)
        
        # Randomize search order for more natural behavior
        random.shuffle(search_positions)
        return search_positions[:6]  # Limit to 6 search positions

class ChaseState(BehaviorState):
    """Enemy actively pursues player."""
    
    def __init__(self):
        super().__init__("CHASE")
        
    def enter(self, enemy):
        super().enter(enemy)
        enemy.move_speed_multiplier = 1.5  # Faster during chase
        enemy.chase_start_time = time.time()
        
    def update(self, enemy, player, maze, dt) -> str:
        chase_duration = time.time() - enemy.chase_start_time
        
        # Check for continued sight of player
        if hasattr(enemy, 'vision_system'):
            detection = enemy.vision_system.can_detect_player(
                enemy.pos, player.pos,
                detection_range=enemy.detection_range * 1.2
            )
            
            if detection['detected']:
                enemy.last_known_player_pos = player.pos
                enemy.chase_start_time = time.time()  # Reset chase timer
            elif chase_duration > 3.0:  # Lost sight for 3 seconds
                return "SEARCH"
        
        # Chase movement with pathfinding
        target = getattr(enemy, 'last_known_player_pos', player.pos)
        if hasattr(enemy, 'pathfinder') and enemy.pathfinder:
            path = enemy.pathfinder.find_path(enemy.pos, target)
            if len(path) > 1:
                enemy.pos = path[1]
            elif len(path) == 1:
                # Reached player position, start search
                return "SEARCH"
        
        # Give up chase after extended time
        if chase_duration > 15.0:
            return "PATROL"
        
        return None
        
    def exit(self, enemy):
        enemy.move_speed_multiplier = 1.0  # Reset speed

class IdleState(BehaviorState):
    """Default idle behavior."""
    
    def __init__(self):
        super().__init__("IDLE")
        
    def update(self, enemy, player, maze, dt) -> str:
        # Check for player detection
        if hasattr(enemy, 'vision_system'):
            detection = enemy.vision_system.can_detect_player(
                enemy.pos, player.pos,
                detection_range=enemy.detection_range
            )
            
            if detection['detected'] and detection['confidence'] > 0.6:
                enemy.last_known_player_pos = player.pos
                return "ALERT"
        
        # Random idle movement
        if random.random() < 0.4:  # 40% chance each update
            directions = [GridPos(0, 1), GridPos(1, 0), GridPos(0, -1), GridPos(-1, 0)]
            direction = random.choice(directions)
            new_pos = enemy.pos + direction
            
            if (hasattr(enemy, 'can_move_to') and
                enemy.can_move_to(new_pos)):
                enemy.pos = new_pos
        
        return None

class BehaviorStateMachine:
    """Manages enemy behavior state transitions."""
    
    def __init__(self):
        self.states = {
            "IDLE": IdleState(),
            "PATROL": PatrolState(), 
            "ALERT": AlertState(),
            "SEARCH": SearchState(),
            "CHASE": ChaseState()
        }
        self.current_state = "IDLE"
        
    def update(self, enemy, player, maze, dt):
        """Update current state and handle transitions."""
        current_state_obj = self.states[self.current_state]
        next_state = current_state_obj.update(enemy, player, maze, dt)
        
        if next_state and next_state in self.states:
            self.transition_to(enemy, next_state)
    
    def transition_to(self, enemy, new_state: str):
        """Transition to a new state."""
        if new_state not in self.states:
            return
            
        # Exit current state
        self.states[self.current_state].exit(enemy)
        
        # Enter new state
        self.current_state = new_state
        self.states[self.current_state].enter(enemy)
        
        # Update enemy state property
        enemy.state = self.current_state
    
    def get_current_state(self) -> str:
        """Get current state name."""
        return self.current_state