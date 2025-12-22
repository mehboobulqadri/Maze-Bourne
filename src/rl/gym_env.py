"""
Maze Bourne - Gymnasium RL Environment
Compatible with Stable-Baselines3 for training AI agents
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Optional, Tuple, Dict, Any, List
import math

from src.core.constants import (
    RL_CONFIG, CellType, EnemyType, EnemyState,
    TILE_SIZE, PLAYER_HEALTH, PLAYER_MAX_ENERGY
)
from src.levels.level import Level
from src.entities.enemy import Enemy


class MazeBourneEnv(gym.Env):
    """
    Gymnasium-compatible environment for Maze Bourne.
    
    Observation Space:
    - Player position (normalized x, y)
    - Player state (health, energy, visibility, is_stealthed)
    - Visible enemies (up to N enemies: relative x, y, state, type)
    - Local map view (grid around player)
    
    Action Space:
    - 0: No movement
    - 1: Up
    - 2: Down
    - 3: Left
    - 4: Right
    - 5: Up-Left
    - 6: Up-Right
    - 7: Down-Left
    - 8: Down-Right
    - 9: Toggle stealth
    - 10: Interact
    - 11: Dash
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}
    
    def __init__(self, 
                 render_mode: Optional[str] = None,
                 level_size: Tuple[int, int] = (20, 20),
                 max_steps: int = None,
                 seed: Optional[int] = None):
        super().__init__()
        
        self.render_mode = render_mode
        self.level_width, self.level_height = level_size
        self.max_steps = max_steps or RL_CONFIG["max_steps_per_episode"]
        self._seed = seed
        
        # View settings
        self.view_radius = RL_CONFIG["observation_size"] // 2
        self.view_size = self.view_radius * 2 + 1
        self.max_enemies = RL_CONFIG["max_enemies_observed"]
        
        # Define action space (12 discrete actions)
        self.action_space = spaces.Discrete(12)
        
        # Define observation space
        # Flat observation for simplicity
        obs_size = (
            4 +  # Player: x, y, health, energy
            self.max_enemies * 4 +  # Enemies: rel_x, rel_y, state, type
            self.view_size * self.view_size  # Local map
        )
        
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(obs_size,),
            dtype=np.float32
        )
        
        # Internal state
        self.level: Optional[Level] = None
        self.player_x = 1.0
        self.player_y = 1.0
        self.player_health = PLAYER_HEALTH
        self.player_energy = PLAYER_MAX_ENERGY
        self.player_keys = 0
        self.is_stealthed = False
        self.enemies: List[MockEnemy] = []
        
        self.steps = 0
        self.total_reward = 0.0
        self.episode_count = 0
        
        # Previous state for reward calculation
        self._prev_distance_to_exit = float('inf')
        self._prev_keys = 0
    
    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        """Reset the environment."""
        super().reset(seed=seed)
        
        if seed is not None:
            self._seed = seed
        
        # Create new level
        self.level = Level(
            width=self.level_width, 
            height=self.level_height,
            algorithm="bsp",
            seed=self._seed
        )
        
        # Set player at spawn
        self.player_x, self.player_y = self.level.spawn_point
        self.player_health = PLAYER_HEALTH
        self.player_energy = PLAYER_MAX_ENERGY
        self.player_keys = 0
        self.is_stealthed = False
        
        # Spawn enemies
        self.enemies = []
        for config in self.level.get_enemy_configs():
            enemy = MockEnemy(
                x=config["x"],
                y=config["y"],
                enemy_type=config["type"]
            )
            self.enemies.append(enemy)
        
        # Reset counters
        self.steps = 0
        self.total_reward = 0.0
        self.episode_count += 1
        
        # Initialize previous state
        self._prev_distance_to_exit = self._distance_to_exit()
        self._prev_keys = 0
        
        return self._get_observation(), self._get_info()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """Execute one step in the environment."""
        if isinstance(action, np.ndarray):
            action = int(action.item())
        
        self.steps += 1
        reward = RL_CONFIG["penalty_time"]  # Small time penalty
        terminated = False
        truncated = False
        
        # Execute action
        self._execute_action(action)
        
        # Update enemies
        self._update_enemies()
        
        # Check collision with enemies
        for enemy in self.enemies:
            dist = math.sqrt((self.player_x - enemy.x)**2 + (self.player_y - enemy.y)**2)
            if dist < 0.6:
                self.player_health -= 1
                reward += RL_CONFIG["penalty_damage"]
                if self.player_health <= 0:
                    reward += RL_CONFIG["penalty_death"]
                    terminated = True
        
        # Check for key collection
        self._check_key_collection()
        if self.player_keys > self._prev_keys:
            reward += RL_CONFIG["reward_key_collected"]
        self._prev_keys = self.player_keys
        
        # Check for exit
        exit_x, exit_y = self.level.exit_point
        dist_to_exit = self._distance_to_exit()
        if dist_to_exit < 0.6:
            reward += RL_CONFIG["reward_level_complete"]
            terminated = True
        
        # Progress reward (getting closer to exit)
        if dist_to_exit < self._prev_distance_to_exit:
            reward += RL_CONFIG["reward_progress"]
        self._prev_distance_to_exit = dist_to_exit
        
        # Check for spotted by enemies
        for enemy in self.enemies:
            if enemy.can_see_player(self.player_x, self.player_y, self.level, self.is_stealthed):
                if enemy.state == EnemyState.IDLE or enemy.state == EnemyState.PATROL:
                    reward += RL_CONFIG["penalty_spotted"]
                    enemy.state = EnemyState.CHASE
        
        # Truncate if max steps reached
        if self.steps >= self.max_steps:
            truncated = True
        
        self.total_reward += reward
        
        return self._get_observation(), reward, terminated, truncated, self._get_info()
    
    def _execute_action(self, action: int):
        """Execute the given action."""
        # Movement directions
        directions = {
            0: (0, 0),    # No move
            1: (0, -1),   # Up
            2: (0, 1),    # Down
            3: (-1, 0),   # Left
            4: (1, 0),    # Right
            5: (-1, -1),  # Up-Left
            6: (1, -1),   # Up-Right
            7: (-1, 1),   # Down-Left
            8: (1, 1),    # Down-Right
        }
        
        if action in directions:
            dx, dy = directions[action]
            # Normalize diagonal
            if dx != 0 and dy != 0:
                dx *= 0.707
                dy *= 0.707
            
            speed = 0.3 if self.is_stealthed else 0.5
            new_x = self.player_x + dx * speed
            new_y = self.player_y + dy * speed
            
            # Collision check
            if self.level.is_walkable(int(new_x), int(self.player_y)):
                self.player_x = new_x
            if self.level.is_walkable(int(self.player_x), int(new_y)):
                self.player_y = new_y
        
        elif action == 9:  # Toggle stealth
            self.is_stealthed = not self.is_stealthed
        
        elif action == 10:  # Interact
            self._try_interact()
        
        elif action == 11:  # Dash
            self._try_dash()
    
    def _try_interact(self):
        """Try to interact with nearby objects."""
        # Check for doors
        for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
            check_x = int(self.player_x) + dx
            check_y = int(self.player_y) + dy
            cell = self.level.get_cell(check_x, check_y)
            if cell and cell.cell_type == CellType.DOOR and cell.is_locked:
                if self.player_keys > 0:
                    self.player_keys -= 1
                    self.level.open_door(check_x, check_y)
                    return
    
    def _try_dash(self):
        """Execute dash if possible."""
        if self.player_energy < 25:
            return
        
        self.player_energy -= 25
        # Dash forward (simplified)
        # In a real implementation, this would check for obstacles
    
    def _check_key_collection(self):
        """Check and collect keys at player position."""
        player_cell = self.level.get_cell(int(self.player_x), int(self.player_y))
        if player_cell and player_cell.cell_type == CellType.KEY:
            if self.level.collect_key(int(self.player_x), int(self.player_y)):
                self.player_keys += 1
    
    def _update_enemies(self):
        """Update all enemies."""
        for enemy in self.enemies:
            enemy.update(self.player_x, self.player_y, self.level, self.is_stealthed)
    
    def _distance_to_exit(self) -> float:
        """Calculate distance to exit."""
        exit_x, exit_y = self.level.exit_point
        return math.sqrt((self.player_x - exit_x)**2 + (self.player_y - exit_y)**2)
    
    def _get_observation(self) -> np.ndarray:
        """Build observation array."""
        obs = []
        
        # Player position (normalized)
        obs.append(self.player_x / self.level_width)
        obs.append(self.player_y / self.level_height)
        obs.append(self.player_health / PLAYER_HEALTH)
        obs.append(self.player_energy / PLAYER_MAX_ENERGY)
        
        # Enemies (up to max_enemies)
        for i in range(self.max_enemies):
            if i < len(self.enemies):
                enemy = self.enemies[i]
                rel_x = (enemy.x - self.player_x) / self.level_width
                rel_y = (enemy.y - self.player_y) / self.level_height
                state_normalized = enemy.state.value / len(EnemyState)
                type_normalized = enemy.enemy_type.value / len(EnemyType)
                obs.extend([rel_x, rel_y, state_normalized, type_normalized])
            else:
                obs.extend([0.0, 0.0, 0.0, 0.0])
        
        # Local map view
        for dy in range(-self.view_radius, self.view_radius + 1):
            for dx in range(-self.view_radius, self.view_radius + 1):
                check_x = int(self.player_x) + dx
                check_y = int(self.player_y) + dy
                cell = self.level.get_cell(check_x, check_y)
                if cell is None:
                    obs.append(-1.0)  # Out of bounds
                elif cell.cell_type == CellType.WALL:
                    obs.append(-0.5)
                elif cell.cell_type == CellType.EXIT:
                    obs.append(1.0)
                elif cell.cell_type == CellType.KEY:
                    obs.append(0.8)
                elif cell.cell_type == CellType.DOOR:
                    obs.append(0.5 if cell.is_locked else 0.3)
                else:
                    obs.append(0.0)  # Floor
        
        return np.array(obs, dtype=np.float32)
    
    def _get_info(self) -> dict:
        """Get additional info for debugging."""
        return {
            "steps": self.steps,
            "total_reward": self.total_reward,
            "player_pos": (self.player_x, self.player_y),
            "player_health": self.player_health,
            "player_keys": self.player_keys,
            "distance_to_exit": self._distance_to_exit(),
            "num_enemies": len(self.enemies),
        }
    
    def render(self):
        """Render the environment."""
        if self.render_mode == "human":
            # Console render for debugging
            self._console_render()
        elif self.render_mode == "rgb_array":
            # Return image array for video recording
            return self._get_rgb_array()
    
    def _console_render(self):
        """Simple console render."""
        from src.core.logger import get_logger
        get_logger().debug(f"Step: {self.steps}, Pos: ({self.player_x:.1f}, {self.player_y:.1f}), "
                          f"HP: {self.player_health}, Keys: {self.player_keys}, "
                          f"Reward: {self.total_reward:.2f}")
    
    def _get_rgb_array(self) -> np.ndarray:
        """Get RGB image of game state."""
        # Simplified - return small image
        img = np.zeros((self.level_height * 4, self.level_width * 4, 3), dtype=np.uint8)
        
        for y in range(self.level_height):
            for x in range(self.level_width):
                cell = self.level.get_cell(x, y)
                if cell:
                    if cell.cell_type == CellType.WALL:
                        color = [50, 50, 70]
                    elif cell.cell_type == CellType.FLOOR:
                        color = [30, 35, 50]
                    elif cell.cell_type == CellType.EXIT:
                        color = [100, 255, 150]
                    elif cell.cell_type == CellType.KEY:
                        color = [255, 215, 0]
                    else:
                        color = [30, 35, 50]
                    
                    img[y*4:(y+1)*4, x*4:(x+1)*4] = color
        
        # Draw player
        px, py = int(self.player_x), int(self.player_y)
        img[py*4:(py+1)*4, px*4:(px+1)*4] = [0, 220, 180]
        
        # Draw enemies
        for enemy in self.enemies:
            ex, ey = int(enemy.x), int(enemy.y)
            if 0 <= ex < self.level_width and 0 <= ey < self.level_height:
                img[ey*4:(ey+1)*4, ex*4:(ex+1)*4] = [180, 60, 60]
        
        return img
    
    def close(self):
        """Clean up resources."""
        pass


class MockEnemy:
    """Simplified enemy for RL environment."""
    
    def __init__(self, x: float, y: float, enemy_type: EnemyType):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.state = EnemyState.PATROL
        self.vision_range = 5.0
        self.move_timer = 0.0
    
    def update(self, player_x: float, player_y: float, level: Level, is_stealthed: bool):
        """Update enemy behavior."""
        self.move_timer += 0.1
        
        if self.can_see_player(player_x, player_y, level, is_stealthed):
            self.state = EnemyState.CHASE
            # Move toward player
            if self.move_timer > 0.3:
                self.move_timer = 0
                dx = player_x - self.x
                dy = player_y - self.y
                if abs(dx) > abs(dy):
                    step_x = 1 if dx > 0 else -1
                    if level.is_walkable(int(self.x + step_x), int(self.y)):
                        self.x += step_x * 0.4
                else:
                    step_y = 1 if dy > 0 else -1
                    if level.is_walkable(int(self.x), int(self.y + step_y)):
                        self.y += step_y * 0.4
        else:
            if self.state == EnemyState.CHASE:
                self.state = EnemyState.PATROL
    
    def can_see_player(self, player_x: float, player_y: float, 
                       level: Level, is_stealthed: bool) -> bool:
        """Check if can see player."""
        dist = math.sqrt((self.x - player_x)**2 + (self.y - player_y)**2)
        effective_range = self.vision_range * (0.5 if is_stealthed else 1.0)
        return dist <= effective_range


# Factory function for environment registration
def make_env(level_size: Tuple[int, int] = (20, 20), seed: int = None):
    """Create environment instance."""
    return MazeBourneEnv(level_size=level_size, seed=seed)
