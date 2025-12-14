"""
Maze Bourne - Interactive Game Objects
Keys, Doors, Cameras, Traps, Hiding Spots, Levers, etc.
"""

from enum import Enum, auto
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass, field
import math
import time


class ObjectState(Enum):
    """State for toggleable objects."""
    INACTIVE = auto()
    ACTIVE = auto()
    TRIGGERED = auto()
    DISABLED = auto()


@dataclass
class GameObject:
    """Base class for all interactive game objects."""
    x: int
    y: int
    is_active: bool = True
    
    def update(self, dt: float, game):
        """Update object state."""
        pass
    
    def on_interact(self, player, game) -> bool:
        """Called when player interacts. Returns True if interaction occurred."""
        return False
    
    def on_player_enter(self, player, game):
        """Called when player enters the same cell."""
        pass
    
    def on_player_exit(self, player, game):
        """Called when player leaves the cell."""
        pass


@dataclass
class Key(GameObject):
    """Collectible key for opening doors."""
    key_id: str = "default"
    collected: bool = False
    
    def on_player_enter(self, player, game):
        """Auto-collect key when player walks over it."""
        if not self.collected and self.is_active:
            self.collected = True
            self.is_active = False
            player.keys += 1
            print(f"[Key] Collected key: {self.key_id}")


@dataclass 
class Door(GameObject):
    """Locked door that requires a key to open."""
    is_locked: bool = True
    required_keys: int = 1
    door_id: str = "default"
    linked_lever: Optional[str] = None  # Can be opened by lever instead
    
    def is_walkable(self) -> bool:
        """Check if door can be passed through."""
        return not self.is_locked
    
    def on_interact(self, player, game) -> bool:
        """Try to unlock door with key."""
        if not self.is_locked:
            return False  # Already open
        
        if player.keys >= self.required_keys:
            player.keys -= self.required_keys
            self.is_locked = False
            print(f"[Door] Unlocked door: {self.door_id}")
            return True
        else:
            print(f"[Door] Need {self.required_keys} key(s) to open!")
            return False
    
    def unlock(self):
        """Unlock the door (from lever or other source)."""
        self.is_locked = False
        print(f"[Door] Door {self.door_id} unlocked remotely")


@dataclass
class Lever(GameObject):
    """Lever that toggles connected objects (doors, cameras, traps)."""
    is_on: bool = False
    linked_objects: List[str] = field(default_factory=list)  # IDs of connected objects
    toggle_delay: float = 0.0
    
    def on_interact(self, player, game) -> bool:
        """Toggle the lever."""
        self.is_on = not self.is_on
        print(f"[Lever] Toggled to: {'ON' if self.is_on else 'OFF'}")
        
        # Toggle linked objects
        self._toggle_linked_objects(game)
        return True
    
    def _toggle_linked_objects(self, game):
        """Toggle all linked objects."""
        for obj_id in self.linked_objects:
            for obj in game.game_objects:
                if hasattr(obj, 'door_id') and obj.door_id == obj_id:
                    if isinstance(obj, Door):
                        if self.is_on:
                            obj.unlock()
                        else:
                            obj.is_locked = True
                elif hasattr(obj, 'camera_id') and obj.camera_id == obj_id:
                    if isinstance(obj, SecurityCamera):
                        obj.is_disabled = self.is_on


@dataclass
class SecurityCamera(GameObject):
    """Security camera that detects player and triggers alarms."""
    camera_id: str = "default"
    vision_range: float = 6.0
    vision_angle: float = 90.0  # Degrees
    facing_direction: Tuple[float, float] = (0, 1)  # Down by default
    rotation_speed: float = 45.0  # Degrees per second
    rotation_pattern: List[Tuple[float, float]] = field(default_factory=list)  # Rotation targets
    rotation_index: int = 0
    rotation_wait: float = 2.0
    rotation_timer: float = 0.0
    
    is_disabled: bool = False
    alert_triggered: bool = False
    detection_timer: float = 0.0
    detection_threshold: float = 1.5  # Seconds to trigger alarm
    
    def update(self, dt: float, game):
        """Update camera rotation and detection."""
        if self.is_disabled:
            return
        
        # Rotate camera
        self._update_rotation(dt)
        
        # Check for player detection
        if game.player:
            if self._can_see_player(game.player, game.level):
                self.detection_timer += dt
                if self.detection_timer >= self.detection_threshold:
                    self._trigger_alarm(game)
            else:
                # Slowly lose detection
                self.detection_timer = max(0, self.detection_timer - dt * 0.5)
    
    def _update_rotation(self, dt: float):
        """Rotate camera through pattern."""
        if not self.rotation_pattern:
            return
        
        self.rotation_timer += dt
        if self.rotation_timer >= self.rotation_wait:
            self.rotation_timer = 0.0
            self.rotation_index = (self.rotation_index + 1) % len(self.rotation_pattern)
            self.facing_direction = self.rotation_pattern[self.rotation_index]
    
    def _can_see_player(self, player, level) -> bool:
        """Check if camera can see the player."""
        if self.is_disabled:
            return False
        
        # Distance check
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > self.vision_range:
            return False
        
        # Stealth check
        if getattr(player, 'is_stealthed', False):
            if distance > self.vision_range * 0.4:
                return False
        
        # Hiding spot check
        if getattr(player, 'is_hidden', False):
            return False
        
        # Angle check
        angle_to_player = math.degrees(math.atan2(dy, dx))
        facing_angle = math.degrees(math.atan2(
            self.facing_direction[1], 
            self.facing_direction[0]
        ))
        
        angle_diff = abs(angle_to_player - facing_angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        if angle_diff > self.vision_angle / 2:
            return False
        
        # Line of sight (simplified)
        if level:
            steps = max(1, int(distance))
            for i in range(1, steps):
                t = i / steps
                check_x = int(self.x + dx * t)
                check_y = int(self.y + dy * t)
                if not level.is_walkable(check_x, check_y):
                    return False
        
        return True
    
    def _trigger_alarm(self, game):
        """Trigger alarm - alert all enemies."""
        if self.alert_triggered:
            return
        
        self.alert_triggered = True
        print(f"[Camera] ALARM TRIGGERED! Camera: {self.camera_id}")
        
        # Import here to avoid circular imports
        from src.core.constants import EnemyState
        
        # Alert all enemies
        for enemy in game.enemies:
            if hasattr(enemy, '_change_state'):
                enemy.last_known_player_pos = type(enemy.pos)(game.player.x, game.player.y)
                enemy._change_state(EnemyState.ALERT)
    
    def reset_alarm(self):
        """Reset the alarm state."""
        self.alert_triggered = False
        self.detection_timer = 0.0


@dataclass
class Trap(GameObject):
    """Trap that damages the player."""
    trap_id: str = "default"
    damage: int = 1
    is_hidden: bool = False  # Hidden traps are invisible until triggered
    is_triggered: bool = False
    reset_time: float = 3.0  # Seconds before trap resets
    reset_timer: float = 0.0
    cooldown: float = 1.0  # Damage cooldown
    last_damage_time: float = 0.0
    
    def update(self, dt: float, game):
        """Update trap state."""
        if self.is_triggered:
            self.reset_timer += dt
            if self.reset_timer >= self.reset_time:
                self.is_triggered = False
                self.reset_timer = 0.0
    
    def on_player_enter(self, player, game):
        """Trigger trap when player steps on it."""
        current_time = time.time()
        
        if current_time - self.last_damage_time < self.cooldown:
            return
        
        self.is_triggered = True
        self.is_hidden = False  # Reveal if hidden
        self.last_damage_time = current_time
        
        print(f"[Trap] Player triggered trap! Damage: {self.damage}")
        if hasattr(player, 'take_damage'):
            player.take_damage(self.damage, game)


@dataclass
class HidingSpot(GameObject):
    """Place where player can hide from enemies."""
    spot_id: str = "default"
    capacity: int = 1  # How many can hide here
    currently_hiding: int = 0
    visibility_reduction: float = 0.9  # 90% reduction in visibility
    
    def on_interact(self, player, game) -> bool:
        """Toggle hiding in this spot."""
        if getattr(player, 'is_hidden', False) and getattr(player, 'hiding_spot', None) == self:
            # Exit hiding
            player.is_hidden = False
            player.hiding_spot = None
            self.currently_hiding -= 1
            print(f"[HidingSpot] Player left hiding spot")
            return True
        elif self.currently_hiding < self.capacity:
            # Enter hiding
            player.is_hidden = True
            player.hiding_spot = self
            self.currently_hiding += 1
            print(f"[HidingSpot] Player is now hiding")
            return True
        
        return False


@dataclass
class Teleporter(GameObject):
    """Teleports player to linked teleporter."""
    teleporter_id: str = "default"
    linked_teleporter_id: str = ""
    cooldown: float = 1.0
    last_use_time: float = 0.0
    
    def on_player_enter(self, player, game):
        """Teleport player when they step on."""
        current_time = time.time()
        
        if current_time - self.last_use_time < self.cooldown:
            return
        
        # Find linked teleporter
        for obj in game.game_objects:
            if isinstance(obj, Teleporter) and obj.teleporter_id == self.linked_teleporter_id:
                player.x = float(obj.x)
                player.y = float(obj.y)
                obj.last_use_time = current_time
                self.last_use_time = current_time
                print(f"[Teleporter] Teleported to {self.linked_teleporter_id}")
                break


@dataclass
class Collectible(GameObject):
    """Generic collectible item."""
    collectible_id: str = "default"
    collectible_type: str = "coin"  # coin, lore, upgrade
    value: int = 1
    collected: bool = False
    
    def on_player_enter(self, player, game):
        """Collect item when player walks over it."""
        if not self.collected and self.is_active:
            self.collected = True
            self.is_active = False
            
            if self.collectible_type == "coin":
                player.coins = getattr(player, 'coins', 0) + self.value
            elif self.collectible_type == "health":
                player.health = min(player.max_health, player.health + self.value)
            elif self.collectible_type == "energy":
                player.energy = min(player.max_energy, player.energy + self.value * 10)
            
            print(f"[Collectible] Picked up {self.collectible_type}: +{self.value}")


class GameObjectManager:
    """Manages all game objects in a level."""
    
    def __init__(self):
        self.objects: List[GameObject] = []
        self._objects_by_cell: dict = {}  # (x, y) -> list of objects
    
    def add(self, obj: GameObject):
        """Add a game object."""
        self.objects.append(obj)
        key = (obj.x, obj.y)
        if key not in self._objects_by_cell:
            self._objects_by_cell[key] = []
        self._objects_by_cell[key].append(obj)
    
    def remove(self, obj: GameObject):
        """Remove a game object."""
        if obj in self.objects:
            self.objects.remove(obj)
            key = (obj.x, obj.y)
            if key in self._objects_by_cell:
                self._objects_by_cell[key].remove(obj)
    
    def get_at(self, x: int, y: int) -> List[GameObject]:
        """Get all objects at a position."""
        return self._objects_by_cell.get((x, y), [])
    
    def update(self, dt: float, game):
        """Update all objects."""
        for obj in self.objects:
            if obj.is_active:
                obj.update(dt, game)
    
    def check_player_collision(self, player, game):
        """Check if player is on any object and trigger interactions."""
        player_pos = (int(player.x), int(player.y))
        objects_at_player = self.get_at(*player_pos)
        
        for obj in objects_at_player:
            if obj.is_active:
                obj.on_player_enter(player, game)
    
    def handle_interact(self, player, game) -> bool:
        """Handle player interaction with nearby objects."""
        # Check current cell and adjacent cells
        positions = [
            (int(player.x), int(player.y)),
            (int(player.x) + 1, int(player.y)),
            (int(player.x) - 1, int(player.y)),
            (int(player.x), int(player.y) + 1),
            (int(player.x), int(player.y) - 1),
        ]
        
        for pos in positions:
            for obj in self.get_at(*pos):
                if obj.is_active and obj.on_interact(player, game):
                    return True
        
        return False
    
    def clear(self):
        """Clear all objects."""
        self.objects.clear()
        self._objects_by_cell.clear()