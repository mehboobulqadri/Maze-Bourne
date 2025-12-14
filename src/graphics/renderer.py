"""
Maze Bourne - Enhanced Rendering Engine
Premium visual effects, smooth animations, and polished UI
"""

import pygame
import math
import time
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, COLORS,
    CAMERA_LERP_SPEED, CellType, EnemyType, EnemyState
)


@dataclass
class Camera:
    """Smooth camera with shake effects."""
    x: float = 0.0
    y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    view_width: int = SCREEN_WIDTH
    view_height: int = SCREEN_HEIGHT
    world_width: int = 0
    world_height: int = 0
    
    # Shake effect
    shake_amount: float = 0.0
    shake_decay: float = 5.0
    
    def update(self, dt: float, lerp_speed: float = CAMERA_LERP_SPEED):
        """Smoothly move camera toward target with shake."""
        self.x += (self.target_x - self.x) * lerp_speed * dt
        self.y += (self.target_y - self.y) * lerp_speed * dt
        
        # Apply shake
        if self.shake_amount > 0:
            self.shake_amount = max(0, self.shake_amount - self.shake_decay * dt)
        
        # Clamp to bounds
        if self.world_width > 0:
            self.x = max(0, min(self.world_width - self.view_width, self.x))
        if self.world_height > 0:
            self.y = max(0, min(self.world_height - self.view_height, self.y))
    
    def set_target(self, x: float, y: float):
        self.target_x = x - self.view_width // 2
        self.target_y = y - self.view_height // 2
    
    def add_shake(self, amount: float):
        self.shake_amount = min(20.0, self.shake_amount + amount)
    
    def get_shake_offset(self) -> Tuple[float, float]:
        if self.shake_amount <= 0:
            return (0, 0)
        import random
        return (
            random.uniform(-self.shake_amount, self.shake_amount),
            random.uniform(-self.shake_amount, self.shake_amount)
        )
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        shake_x, shake_y = self.get_shake_offset()
        return (int(world_x - self.x + shake_x), int(world_y - self.y + shake_y))
    
    def is_visible(self, world_x: float, world_y: float, 
                   width: float = TILE_SIZE, height: float = TILE_SIZE) -> bool:
        return (world_x + width > self.x and world_x < self.x + self.view_width and
                world_y + height > self.y and world_y < self.y + self.view_height)


class Particle:
    """Simple particle for visual effects."""
    def __init__(self, x: float, y: float, vx: float, vy: float, 
                 color: Tuple, size: float, lifetime: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.alive = True
    
    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
    
    def get_alpha(self) -> int:
        return int(255 * (self.lifetime / self.max_lifetime))


class ParticleSystem:
    """Manages particle effects."""
    def __init__(self, max_particles: int = 200):
        self.particles: List[Particle] = []
        self.max_particles = max_particles
    
    def spawn(self, x: float, y: float, color: Tuple, count: int = 5,
              speed: float = 50, size: float = 3, lifetime: float = 0.5):
        import random
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(speed * 0.5, speed)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * spd, math.sin(angle) * spd,
                color, random.uniform(size * 0.5, size), lifetime
            ))
        # Limit particles
        if len(self.particles) > self.max_particles:
            self.particles = self.particles[-self.max_particles:]
    
    def update(self, dt: float):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update(dt)
    
    def draw(self, surface: pygame.Surface, camera: Camera):
        for p in self.particles:
            screen_x, screen_y = camera.world_to_screen(p.x, p.y)
            alpha = p.get_alpha()
            if alpha > 0:
                color = (*p.color[:3], alpha) if len(p.color) == 3 else p.color
                pygame.draw.circle(surface, p.color[:3], 
                                 (int(screen_x), int(screen_y)), int(p.size))


class Renderer:
    """Enhanced rendering engine with visual polish."""
    
    def __init__(self, game):
        self.game = game
        self.camera = Camera()
        self.particles = ParticleSystem()
        
        # Animation timers
        self.time = 0.0
        self.pulse_time = 0.0
        
        # Notifications: list of (text, time_remaining, color)
        self.notifications = []
        
        # Pre-create surfaces for effects
        self.glow_surface = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2), pygame.SRCALPHA)
    
    def add_notification(self, text: str, color: Tuple = COLORS.UI_TEXT, duration: float = 2.0):
        """Add a floating notification."""
        self.notifications.append([text, duration, color])
        
    def setup_for_level(self, level):
        self.camera.world_width = level.width * TILE_SIZE
        self.camera.world_height = level.height * TILE_SIZE
        # Clear particles and notifications on new level
        self.particles.particles.clear()
        self.notifications.clear()
    
    def update(self, dt: float):
        self.time += dt
        self.pulse_time += dt * 3  # Pulse speed
        
        # Update camera
        if self.game.player:
            player_x = self.game.player.x * TILE_SIZE + TILE_SIZE // 2
            player_y = self.game.player.y * TILE_SIZE + TILE_SIZE // 2
            self.camera.set_target(player_x, player_y)
        
        self.camera.update(dt)
        self.particles.update(dt)
        
        # Update notifications
        for notif in self.notifications:
            notif[1] -= dt
        self.notifications = [n for n in self.notifications if n[1] > 0]
        
        # Spawn dash particles
        if self.game.player and getattr(self.game.player, 'is_dashing', False):
            px = self.game.player.x * TILE_SIZE + TILE_SIZE // 2
            py = self.game.player.y * TILE_SIZE + TILE_SIZE // 2
            self.particles.spawn(px, py, COLORS.PLAYER_DASH, count=3, speed=30, lifetime=0.3)
    
    def render(self, screen: pygame.Surface):
        # Clear with gradient background
        self._draw_background(screen)
        
        # Draw level
        self._render_floor(screen)
        self._render_walls(screen)
        self._render_objects(screen)
        
        # Draw enemies with glow
        self._render_enemies(screen)
        
        # Draw player with effects
        self._render_player(screen)
        
        # Draw particles
        self.particles.draw(screen, self.camera)
        
        # Draw interaction prompts
        self._render_interaction_prompts(screen)
        
        # Draw UI
        self._render_ui(screen)
        self._render_notifications(screen)
        
        # Debug overlay
        if self.game.debug_mode:
            self._render_debug(screen)

    def _render_interaction_prompts(self, screen: pygame.Surface):
        """Draw 'E' prompt near interactable objects."""
        if not self.game.player or not self.game.level:
            return
            
        px, py = self.game.player.x, self.game.player.y
        
        # Check adjacent cells
        for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
            tx, ty = int(px + dx), int(py + dy)
            cell = self.game.level.get_cell(tx, ty)
            if not cell:
                continue
                
            should_prompt = False
            if cell.cell_type == CellType.DOOR and cell.is_locked:
                should_prompt = True
            elif cell.cell_type == CellType.LEVER:
                should_prompt = True
            
            if should_prompt:
                world_x = tx * TILE_SIZE + TILE_SIZE // 2
                world_y = ty * TILE_SIZE - 10
                sx, sy = self.camera.world_to_screen(world_x, world_y)
                
                # Bobbing motion
                sy += math.sin(self.time * 5) * 3
                
                # Draw prompt
                prompt_text = self.game.font_small.render("[E]", True, COLORS.UI_TEXT)
                prompt_rect = prompt_text.get_rect(center=(sx, sy))
                
                # Background
                bg_rect = prompt_rect.inflate(8, 4)
                pygame.draw.rect(screen, (0, 0, 0, 200), bg_rect, border_radius=4)
                pygame.draw.rect(screen, COLORS.UI_BORDER, bg_rect, 1, border_radius=4)
                screen.blit(prompt_text, prompt_rect)

    def _render_notifications(self, screen: pygame.Surface):
        """Draw active notifications stacking up."""
        x = SCREEN_WIDTH // 2
        y = SCREEN_HEIGHT - 100
        
        for text, time_left, color in reversed(self.notifications):
            # Fade out
            alpha = min(255, int(time_left * 255))
            if time_left > 1.0: alpha = 255
            
            surf = self.game.font_medium.render(text, True, color)
            surf.set_alpha(alpha)
            rect = surf.get_rect(center=(x, y))
            
            # Shadow
            shadow = self.game.font_medium.render(text, True, (0, 0, 0))
            shadow.set_alpha(alpha)
            shadow_rect = shadow.get_rect(center=(x + 2, y + 2))
            
            screen.blit(shadow, shadow_rect)
            screen.blit(surf, rect)
            
            y -= 40
    
    def _draw_background(self, screen: pygame.Surface):
        """Draw gradient background."""
        screen.fill(COLORS.VOID)
    
    def _render_floor(self, screen: pygame.Surface):
        level = self.game.level
        if not level:
            return
        
        # Calculate visible tile range
        start_x = max(0, int(self.camera.x // TILE_SIZE) - 1)
        start_y = max(0, int(self.camera.y // TILE_SIZE) - 1)
        end_x = min(level.width, int((self.camera.x + SCREEN_WIDTH) // TILE_SIZE) + 2)
        end_y = min(level.height, int((self.camera.y + SCREEN_HEIGHT) // TILE_SIZE) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                cell = level.get_cell(x, y)
                if cell is None or cell.cell_type == CellType.WALL:
                    continue
                
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                
                # Draw floor with pattern
                self._draw_floor_tile(screen, screen_x, screen_y, x, y)
    
    def _draw_floor_tile(self, surface: pygame.Surface, x: int, y: int, 
                         grid_x: int, grid_y: int):
        """Draw stylized floor tile."""
        # Base color with slight variation
        brightness = 1.0 + math.sin((grid_x + grid_y) * 0.5) * 0.05
        base_color = tuple(int(c * brightness) for c in COLORS.FLOOR)
        
        pygame.draw.rect(surface, base_color, (x, y, TILE_SIZE, TILE_SIZE))
        
        # Subtle grid lines
        pygame.draw.rect(surface, COLORS.FLOOR_PATTERN, (x, y, TILE_SIZE, TILE_SIZE), 1)
        
        # Tech panel detail on some tiles
        if (grid_x + grid_y) % 5 == 0:
            pygame.draw.rect(surface, COLORS.WALL_HIGHLIGHT, 
                           (x + 4, y + 4, 6, 6), 1)
        if (grid_x * 3 + grid_y * 2) % 7 == 0:
            pygame.draw.line(surface, COLORS.FLOOR_PATTERN,
                           (x + 8, y + TILE_SIZE // 2), 
                           (x + TILE_SIZE - 8, y + TILE_SIZE // 2), 1)
    
    def _render_walls(self, screen: pygame.Surface):
        level = self.game.level
        if not level:
            return
        
        start_x = max(0, int(self.camera.x // TILE_SIZE) - 1)
        start_y = max(0, int(self.camera.y // TILE_SIZE) - 1)
        end_x = min(level.width, int((self.camera.x + SCREEN_WIDTH) // TILE_SIZE) + 2)
        end_y = min(level.height, int((self.camera.y + SCREEN_HEIGHT) // TILE_SIZE) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                cell = level.get_cell(x, y)
                if cell is None or cell.cell_type != CellType.WALL:
                    continue
                
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                
                self._draw_wall(screen, screen_x, screen_y, x, y)
    
    def _draw_wall(self, surface: pygame.Surface, x: int, y: int,
                   grid_x: int, grid_y: int):
        """Draw stylized 3D wall."""
        # Main wall
        pygame.draw.rect(surface, COLORS.WALL, (x, y, TILE_SIZE, TILE_SIZE))
        
        # Top highlight
        pygame.draw.line(surface, COLORS.WALL_HIGHLIGHT, 
                        (x, y), (x + TILE_SIZE, y), 2)
        pygame.draw.line(surface, COLORS.WALL_HIGHLIGHT, 
                        (x, y), (x, y + TILE_SIZE // 3), 2)
        
        # Bottom shadow
        shadow = tuple(max(0, c - 25) for c in COLORS.WALL)
        pygame.draw.line(surface, shadow, 
                        (x, y + TILE_SIZE - 1), (x + TILE_SIZE, y + TILE_SIZE - 1), 2)
        pygame.draw.line(surface, shadow, 
                        (x + TILE_SIZE - 1, y + TILE_SIZE // 2), 
                        (x + TILE_SIZE - 1, y + TILE_SIZE), 2)
        
        # Tech panel details
        if (grid_x + grid_y) % 3 == 0:
            panel_color = tuple(min(255, c + 15) for c in COLORS.WALL)
            pygame.draw.rect(surface, panel_color, 
                           (x + 8, y + 8, TILE_SIZE - 16, TILE_SIZE - 16), 1)
    
    def _render_objects(self, screen: pygame.Surface):
        level = self.game.level
        if not level:
            return
        
        start_x = max(0, int(self.camera.x // TILE_SIZE) - 1)
        start_y = max(0, int(self.camera.y // TILE_SIZE) - 1)
        end_x = min(level.width, int((self.camera.x + SCREEN_WIDTH) // TILE_SIZE) + 2)
        end_y = min(level.height, int((self.camera.y + SCREEN_HEIGHT) // TILE_SIZE) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                cell = level.get_cell(x, y)
                if cell is None:
                    continue
                
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                
                if cell.cell_type == CellType.KEY:
                    self._draw_key(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.DOOR:
                    self._draw_door(screen, screen_x, screen_y, cell.is_locked)
                elif cell.cell_type == CellType.EXIT:
                    self._draw_exit(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.SPAWN:
                    self._draw_spawn(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.TRAP:
                    self._draw_trap(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.HIDING_SPOT:
                    self._draw_hiding_spot(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.CAMERA:
                    self._draw_camera_obj(screen, screen_x, screen_y)
    
    def _draw_key(self, surface: pygame.Surface, x: int, y: int):
        """Draw animated key with glow."""
        pulse = math.sin(self.pulse_time) * 0.2 + 1.0
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2
        bob_y = int(math.sin(self.time * 4) * 3)
        
        # Glow
        glow_color = (255, 215, 100, 50)
        glow_size = int(TILE_SIZE * 0.4 * pulse)
        pygame.draw.circle(surface, COLORS.KEY, 
                          (center_x, center_y + bob_y), glow_size)
        
        # Key shape
        ring_size = int(8 * pulse)
        pygame.draw.circle(surface, (255, 235, 100), 
                          (center_x, center_y - 4 + bob_y), ring_size)
        pygame.draw.circle(surface, COLORS.FLOOR, 
                          (center_x, center_y - 4 + bob_y), ring_size - 3)
        pygame.draw.rect(surface, (255, 235, 100), 
                        (center_x - 2, center_y + bob_y, 4, 14))
        pygame.draw.rect(surface, (255, 235, 100), 
                        (center_x + 2, center_y + 6 + bob_y, 4, 3))
    
    def _draw_door(self, surface: pygame.Surface, x: int, y: int, is_locked: bool):
        """Draw door with lock indicator."""
        color = COLORS.DOOR_LOCKED if is_locked else COLORS.DOOR_UNLOCKED
        pygame.draw.rect(surface, color, (x + 6, y + 2, TILE_SIZE - 12, TILE_SIZE - 4))
        
        # Frame
        pygame.draw.rect(surface, COLORS.WALL_HIGHLIGHT, 
                        (x + 6, y + 2, TILE_SIZE - 12, TILE_SIZE - 4), 2)
        
        if is_locked:
            # Lock icon
            pygame.draw.circle(surface, (60, 50, 40), 
                             (x + TILE_SIZE // 2, y + TILE_SIZE // 2 - 4), 6)
            pygame.draw.rect(surface, (60, 50, 40), 
                           (x + TILE_SIZE // 2 - 4, y + TILE_SIZE // 2, 8, 10))
    
    def _draw_exit(self, surface: pygame.Surface, x: int, y: int):
        """Draw pulsing exit."""
        pulse = math.sin(self.pulse_time * 1.5) * 0.3 + 0.7
        color = tuple(int(c * pulse) for c in COLORS.EXIT)
        
        pygame.draw.rect(surface, color, (x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8))
        pygame.draw.rect(surface, (255, 255, 255), 
                        (x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8), 2)
        
        # Arrow
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2
        pygame.draw.polygon(surface, (255, 255, 255), [
            (center_x, y + 10),
            (center_x + 10, center_y),
            (center_x + 4, center_y),
            (center_x + 4, y + TILE_SIZE - 10),
            (center_x - 4, y + TILE_SIZE - 10),
            (center_x - 4, center_y),
            (center_x - 10, center_y),
        ])
    
    def _draw_spawn(self, surface: pygame.Surface, x: int, y: int):
        pygame.draw.circle(surface, COLORS.SPAWN, 
                          (x + TILE_SIZE // 2, y + TILE_SIZE // 2), TILE_SIZE // 4, 2)
    
    def _draw_trap(self, surface: pygame.Surface, x: int, y: int):
        """Draw spike trap."""
        for i in range(4):
            spike_x = x + 6 + i * 10
            pygame.draw.polygon(surface, COLORS.TRAP, [
                (spike_x, y + TILE_SIZE - 8),
                (spike_x + 5, y + 8),
                (spike_x + 10, y + TILE_SIZE - 8)
            ])
    
    def _draw_hiding_spot(self, surface: pygame.Surface, x: int, y: int):
        pygame.draw.rect(surface, COLORS.HIDING_SPOT, 
                        (x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4))
        # Shadow lines
        for i in range(3):
            pygame.draw.line(surface, COLORS.WALL, 
                           (x + 6, y + 10 + i * 12), 
                           (x + TILE_SIZE - 6, y + 14 + i * 12), 2)
    
    def _draw_camera_obj(self, surface: pygame.Surface, x: int, y: int):
        pygame.draw.rect(surface, COLORS.CAMERA_INACTIVE, 
                        (x + 12, y + 12, TILE_SIZE - 24, TILE_SIZE - 24))
        # Blinking light
        blink = int(self.time * 2) % 2
        color = COLORS.CAMERA_ACTIVE if blink else (100, 50, 50)
        pygame.draw.circle(surface, color, (x + TILE_SIZE // 2, y + TILE_SIZE // 2), 4)
    
    def _render_player(self, screen: pygame.Surface):
        player = self.game.player
        if not player:
            return
        
        world_x = player.x * TILE_SIZE
        world_y = player.y * TILE_SIZE
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
        
        # Choose color
        if getattr(player, 'is_dashing', False):
            color = COLORS.PLAYER_DASH
            # Trail effect already handled by particles
        elif getattr(player, 'is_stealthed', False):
            color = COLORS.PLAYER_STEALTH
        else:
            color = COLORS.PLAYER
        
        # Glow effect
        glow_size = TILE_SIZE // 2 + int(math.sin(self.time * 3) * 2)
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color[:3], 30), (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (screen_x + TILE_SIZE // 2 - glow_size, 
                                screen_y + TILE_SIZE // 2 - glow_size))
        
        # Player body
        padding = 6
        pygame.draw.rect(screen, color, 
                        (screen_x + padding, screen_y + padding, 
                         TILE_SIZE - padding * 2, TILE_SIZE - padding * 2),
                        border_radius=4)
        
        # Highlight
        highlight = tuple(min(255, c + 60) for c in color)
        pygame.draw.rect(screen, highlight, 
                        (screen_x + padding, screen_y + padding, 
                         TILE_SIZE - padding * 2, 4),
                        border_radius=2)
        
        # Direction indicator
        facing = getattr(player, 'facing', (0, 1))
        center_x = screen_x + TILE_SIZE // 2
        center_y = screen_y + TILE_SIZE // 2
        ind_x = center_x + int(facing[0] * 10)
        ind_y = center_y + int(facing[1] * 10)
        pygame.draw.circle(screen, (255, 255, 255), (ind_x, ind_y), 4)
    
    def _render_enemies(self, screen: pygame.Surface):
        for enemy in self.game.enemies:
            self._render_enemy(screen, enemy)
    
    def _render_enemy(self, screen: pygame.Surface, enemy):
        world_x = enemy.pos.x * TILE_SIZE
        world_y = enemy.pos.y * TILE_SIZE
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
        
        # Get color based on state
        if enemy.state in [EnemyState.ALERT, EnemyState.CHASE]:
            color = COLORS.ENEMY_ALERT
            # Spawn alert particles
            if hasattr(self, '_last_alert_spawn'):
                if self.time - self._last_alert_spawn > 0.2:
                    self.particles.spawn(world_x + TILE_SIZE // 2, world_y + TILE_SIZE // 2,
                                        COLORS.ENEMY_ALERT, count=2, speed=20, lifetime=0.3)
                    self._last_alert_spawn = self.time
            else:
                self._last_alert_spawn = self.time
        else:
            color = enemy.color
        
        # Enemy body with glow when alerted
        padding = 8
        
        if enemy.state in [EnemyState.ALERT, EnemyState.CHASE]:
            # Alert glow
            glow_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*COLORS.ENEMY_ALERT[:3], 40), 
                             (TILE_SIZE // 2, TILE_SIZE // 2), TILE_SIZE // 2)
            screen.blit(glow_surf, (screen_x, screen_y))
        
        # Body
        pygame.draw.rect(screen, color, 
                        (screen_x + padding, screen_y + padding, 
                         TILE_SIZE - padding * 2, TILE_SIZE - padding * 2),
                        border_radius=3)
        
        # Eye
        eye_x = screen_x + TILE_SIZE // 2
        eye_y = screen_y + TILE_SIZE // 2
        pygame.draw.circle(screen, (255, 255, 255), (eye_x, eye_y), 6)
        
        # Pupil (looks toward player)
        if self.game.player:
            dx = self.game.player.x - enemy.pos.x
            dy = self.game.player.y - enemy.pos.y
            dist = max(1, math.sqrt(dx * dx + dy * dy))
            pygame.draw.circle(screen, (0, 0, 0), 
                             (int(eye_x + dx / dist * 2), int(eye_y + dy / dist * 2)), 3)
        
        # State indicator
        if enemy.state == EnemyState.SUSPICIOUS:
            pygame.draw.polygon(screen, (255, 255, 0), [
                (screen_x + TILE_SIZE // 2, screen_y - 8),
                (screen_x + TILE_SIZE // 2 - 6, screen_y - 2),
                (screen_x + TILE_SIZE // 2 + 6, screen_y - 2)
            ])
        elif enemy.state in [EnemyState.ALERT, EnemyState.CHASE]:
            pygame.draw.rect(screen, (255, 50, 50), 
                           (screen_x + TILE_SIZE // 2 - 2, screen_y - 16, 4, 10))
            pygame.draw.rect(screen, (255, 50, 50), 
                           (screen_x + TILE_SIZE // 2 - 2, screen_y - 4, 4, 4))
    
    def _render_ui(self, screen: pygame.Surface):
        player = self.game.player
        if not player:
            return
        
        # UI Panel background
        panel_height = 70
        panel = pygame.Surface((300, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*COLORS.UI_BG, 200), (0, 0, 300, panel_height), border_radius=8)
        pygame.draw.rect(panel, COLORS.UI_BORDER, (0, 0, 300, panel_height), 2, border_radius=8)
        screen.blit(panel, (15, SCREEN_HEIGHT - panel_height - 15))
        
        base_x = 25
        base_y = SCREEN_HEIGHT - panel_height
        
        # Health hearts
        for i in range(player.max_health):
            heart_x = base_x + i * 28
            heart_y = base_y + 10
            color = COLORS.UI_HEALTH if i < player.health else (60, 40, 50)
            self._draw_heart(screen, heart_x, heart_y, color)
        
        # Energy bar
        bar_x = base_x
        bar_y = base_y + 35
        bar_width = 200
        bar_height = 12
        
        energy_ratio = player.energy / player.max_energy
        pygame.draw.rect(screen, (30, 40, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=3)
        pygame.draw.rect(screen, COLORS.UI_ENERGY, 
                        (bar_x, bar_y, int(bar_width * energy_ratio), bar_height), border_radius=3)
        pygame.draw.rect(screen, COLORS.UI_BORDER, (bar_x, bar_y, bar_width, bar_height), 1, border_radius=3)
        
        # Key count
        key_x = base_x + 220
        key_y = base_y + 18
        pygame.draw.circle(screen, COLORS.KEY, (key_x, key_y), 8)
        key_text = self.game.font_small.render(f"x{player.keys}", True, COLORS.UI_TEXT)
        screen.blit(key_text, (key_x + 12, key_y - 10))
        
        # Stealth indicator
        if getattr(player, 'is_stealthed', False):
            stealth_text = self.game.font_medium.render("STEALTH", True, COLORS.UI_STEALTH)
            stealth_rect = stealth_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
            screen.blit(stealth_text, stealth_rect)
    
    def _draw_heart(self, surface: pygame.Surface, x: int, y: int, color: Tuple):
        """Draw a heart shape."""
        points = []
        for i in range(20):
            t = i / 20 * 2 * math.pi
            hx = 16 * (math.sin(t) ** 3)
            hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
            points.append((x + hx * 0.6, y + hy * 0.6))
        pygame.draw.polygon(surface, color, points)
    
    def _render_debug(self, screen: pygame.Surface):
        y_offset = 60
        
        if self.game.player:
            text = self.game.font_tiny.render(
                f"Player: ({self.game.player.x:.1f}, {self.game.player.y:.1f})", 
                True, COLORS.UI_TEXT_DIM)
            screen.blit(text, (10, y_offset))
            y_offset += 20
        
        text = self.game.font_tiny.render(
            f"Enemies: {len(self.game.enemies)}", True, COLORS.UI_TEXT_DIM)
        screen.blit(text, (10, y_offset))
        y_offset += 20
        
        text = self.game.font_tiny.render(
            f"Particles: {len(self.particles.particles)}", True, COLORS.UI_TEXT_DIM)
        screen.blit(text, (10, y_offset))
