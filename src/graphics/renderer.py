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
    
    # Centering offset
    center_offset_x: float = 0.0
    center_offset_y: float = 0.0
    
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
        
        # Clamp to bounds or Calculate centering
        if self.world_width > 0:
            if self.world_width < self.view_width:
                # Center horizontally
                self.center_offset_x = (self.view_width - self.world_width) // 2
                self.x = -self.center_offset_x  # Effectively ignores target_x logic for centering
            else:
                self.center_offset_x = 0
                self.x = max(0, min(self.world_width - self.view_width, self.x))
                
        if self.world_height > 0:
            if self.world_height < self.view_height:
                # Center vertically
                self.center_offset_y = (self.view_height - self.world_height) // 2
                self.y = -self.center_offset_y
            else:
                self.center_offset_y = 0
                self.y = max(0, min(self.world_height - self.view_height, self.y))
    
    def set_target(self, x: float, y: float):
        if self.world_width >= self.view_width:
            self.target_x = x - self.view_width // 2
        if self.world_height >= self.view_height:
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
        # Note: self.x/y already include the negative offset if centering is active
        # because we set self.x = -offset.
        # So (world_x - self.x) becomes (world_x - (-offset)) = world_x + offset
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
    
        # Visibility
        self.visible_tiles = set()
        self.explored_tiles = set()
        
        # Menu mode: show full map without FOV restrictions
        self.menu_mode = False
    
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
            
            # Calculate FOV
            self._update_fov(self.game.player.x, self.game.player.y)
        
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

    def _update_fov(self, px: float, py: float):
        """Simple Raycast FOV."""
        self.visible_tiles.clear()
        
        radius = 12
        radius_sq = radius * radius
        
        # Optimization: Only check bounding box
        min_x = int(px - radius)
        max_x = int(px + radius)
        min_y = int(py - radius)
        max_y = int(py + radius)
        
        # Add center
        self.visible_tiles.add((int(px), int(py)))
        
        # Steps for raycasting
        steps = 20 # checks per unit distance
        
        level = self.game.level
        if not level: return

        # Iterate through border of the box and cast rays to it? 
        # Better: iterate all tiles in box, if close enough, check line of sight
        # Even Better for performance: Shadowcasting, but let's do simple ray check for now
        
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                dx = x - px
                dy = y - py
                dist_sq = dx*dx + dy*dy
                
                if dist_sq > radius_sq:
                    continue
                
                # Check Line of Sight
                if self._has_line_of_sight(px, py, x + 0.5, y + 0.5, level):
                    self.visible_tiles.add((x, y))
                    self.explored_tiles.add((x, y))
    
    def _has_line_of_sight(self, x0, y0, x1, y1, level):
        """Bresenham-like line check."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x = int(x0)
        y = int(y0)
        n = 1 + int(dx + dy)
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2
        
        # Note: This is a discrete approximation. For precise wall corners, 
        # meaningful raycasting is needed. But for grid, stepping tiles is okay.
        # Actually proper DDA is better.
        
        # Let's use simple sampling
        dist = math.hypot(x1 - x0, y1 - y0)
        if dist == 0: return True
        
        step_size = 0.5 # Check every half tile
        steps = int(dist / step_size) + 1
        
        cur_x = x0
        cur_y = y0
        vx = (x1 - x0) / dist * step_size
        vy = (y1 - y0) / dist * step_size
        
        for _ in range(steps):
             tx, ty = int(cur_x), int(cur_y)
             # If strictly wall and not start/end?
             # Player can see wall itself, but not behind it
             if (tx, ty) != (int(x0), int(y0)) and (tx, ty) != (int(x1), int(y1)):
                 cell = level.get_cell(tx, ty)
                 if cell and cell.cell_type == CellType.WALL:
                     return False
             
             cur_x += vx
             cur_y += vy
             
        # Check endpoint (wall is visible)
        return True

    def render(self, screen: pygame.Surface):
        # Clear with black (Fog)
        screen.fill(COLORS.VOID)
        
        # Only render visible stuff
        # Draw level
        self._render_floor(screen)
        self._render_walls(screen)
        self._render_objects(screen)
        
        # Draw enemies with glow
        self._render_enemies(screen)
        
        # Draw game objects (cameras, traps, hiding spots)
        self._render_game_objects(screen)
        
        # Draw player with effects
        self._render_player(screen)
        
        # Draw Fog Overlay (Soft edges?)
        # For now, tiles outside 'visible_tiles' are just not drawn (Black)
        
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

    # MODIFIED RENDER METHODS TO CHECK VISIBILITY
    
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
                # Visibility Check (bypass in menu mode)
                if not self.menu_mode and (x, y) not in self.visible_tiles:
                    continue
                
                cell = level.get_cell(x, y)
                if cell is None or cell.cell_type == CellType.WALL:
                    continue
                    continue
                
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                
                # Draw floor
                self._draw_floor_tile(screen, screen_x, screen_y, x, y)

    def _draw_floor_tile(self, surface: pygame.Surface, x: int, y: int, 
                         grid_x: int, grid_y: int, brightness_mult: float = 1.0):
        """Draw stylized floor tile."""
        # Base color with slight variation
        tile_bright = 1.0 + math.sin((grid_x + grid_y) * 0.5) * 0.05
        
        # Apply FOV brightness
        final_bright = tile_bright * brightness_mult
        
        base_color = tuple(int(c * final_bright) for c in COLORS.FLOOR)
        pattern_color = tuple(int(c * brightness_mult) for c in COLORS.FLOOR_PATTERN)
        
        pygame.draw.rect(surface, base_color, (x, y, TILE_SIZE, TILE_SIZE))
        
        # Subtle grid lines
        pygame.draw.rect(surface, pattern_color, (x, y, TILE_SIZE, TILE_SIZE), 1)
        
        # Detail only if bright enough
        if brightness_mult > 0.5:
            if (grid_x + grid_y) % 5 == 0:
                hl_color = tuple(int(c * brightness_mult) for c in COLORS.WALL_HIGHLIGHT)
                pygame.draw.rect(surface, hl_color, (x + 4, y + 4, 6, 6), 1)

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
                # Visibility Check (bypass in menu mode)
                if not self.menu_mode and (x, y) not in self.visible_tiles:
                    continue

                cell = level.get_cell(x, y)
                if cell is None or cell.cell_type != CellType.WALL:
                    continue
                
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                
                self._draw_wall(screen, screen_x, screen_y, x, y)

    def _draw_wall(self, surface: pygame.Surface, x: int, y: int,
                   grid_x: int, grid_y: int, brightness: float = 1.0):
        """Draw stylized 3D wall."""
        
        def darken(color, factor):
            return tuple(int(c * factor) for c in color)
            
        wall_color = darken(COLORS.WALL, brightness)
        hl_color = darken(COLORS.WALL_HIGHLIGHT, brightness)
        
        # Main wall
        pygame.draw.rect(surface, wall_color, (x, y, TILE_SIZE, TILE_SIZE))
        
        # Top highlight
        pygame.draw.line(surface, hl_color, (x, y), (x + TILE_SIZE, y), 2)
        
        # Only draw details if visible
        if brightness > 0.5:
             pygame.draw.line(surface, hl_color, (x, y), (x, y + TILE_SIZE // 3), 2)
             # Tech panel
             if (grid_x + grid_y) % 3 == 0:
                 p_color = darken(tuple(min(255, c + 15) for c in COLORS.WALL), brightness)
                 pygame.draw.rect(surface, p_color, (x + 8, y + 8, TILE_SIZE - 16, TILE_SIZE - 16), 1)

    def _render_objects(self, screen: pygame.Surface):
        level = self.game.level
        if not level: return
        
        # Same iteration...
        start_x = max(0, int(self.camera.x // TILE_SIZE) - 1)
        start_y = max(0, int(self.camera.y // TILE_SIZE) - 1)
        end_x = min(level.width, int((self.camera.x + SCREEN_WIDTH) // TILE_SIZE) + 2)
        end_y = min(level.height, int((self.camera.y + SCREEN_HEIGHT) // TILE_SIZE) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # In menu mode, show all objects
                if self.menu_mode:
                    cell = level.get_cell(x, y)
                    if not cell: continue
                    world_x = x * TILE_SIZE
                    world_y = y * TILE_SIZE
                    screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                    self._draw_object_by_type(screen, screen_x, screen_y, cell)
                    continue
                    
                # Objects only visible if in LOS? 
                # Yes. Hidden behind walls.
                if (x, y) not in self.visible_tiles:
                     # Maybe show explored stationary objects (exits/doors) as dim?
                     # Let's show Explored-but-not-visible as dim for static objects
                     if (x, y) not in self.explored_tiles:
                         continue
                     # Only draw static objects dimly
                     cell = level.get_cell(x, y)
                     if not cell: continue
                     # Key/Enemies should NOT be shown if not visible, even if explored?
                     # Key is static until picked up.
                     # Let's say only Doors/Exits/Traps/Spawns are static map features.
                     if cell.cell_type in [CellType.KEY, CellType.ENEMY_SPAWN]:
                         continue # Dynamic-ish (Keys disappear)
                
                cell = level.get_cell(x, y) # Re-get cell if it was skipped above
                if cell is None: continue
                
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                
                # Check dimming
                is_dim = (x, y) not in self.visible_tiles
                
                if cell.cell_type == CellType.KEY and not is_dim:
                    self._draw_key(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.DOOR:
                    self._draw_door(screen, screen_x, screen_y, cell.is_locked)
                elif cell.cell_type == CellType.EXIT:
                    self._draw_exit(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.TRAP and not is_dim:
                     self._draw_trap(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.HIDING_SPOT:
                     self._draw_hiding_spot(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.CAMERA and not is_dim:
                    self._draw_camera_obj(screen, screen_x, screen_y)
                elif cell.cell_type == CellType.LEVER and not is_dim:
                    self._draw_lever(screen, screen_x, screen_y, cell.is_active)
    
    def _draw_object_by_type(self, screen, screen_x, screen_y, cell):
        """Draw a cell object by its type (for menu mode)."""
        if cell.cell_type == CellType.KEY:
            self._draw_key(screen, screen_x, screen_y)
        elif cell.cell_type == CellType.DOOR:
            self._draw_door(screen, screen_x, screen_y, cell.is_locked)
        elif cell.cell_type == CellType.EXIT:
            self._draw_exit(screen, screen_x, screen_y)
        elif cell.cell_type == CellType.TRAP:
            self._draw_trap(screen, screen_x, screen_y)
        elif cell.cell_type == CellType.HIDING_SPOT:
            self._draw_hiding_spot(screen, screen_x, screen_y)

    def _render_enemies(self, screen: pygame.Surface):
        for enemy in self.game.enemies:
            # Only render if visible!
            ex, ey = int(enemy.pos.x), int(enemy.pos.y)
            if (ex, ey) in self.visible_tiles:
                self._render_enemy(screen, enemy)
    
    def _render_game_objects(self, screen: pygame.Surface):
        """Render all game objects (cameras, traps, hiding spots)."""
        if not hasattr(self.game, 'game_object_manager') or not self.game.game_object_manager:
            return
        
        from src.entities.game_objects import SecurityCamera, Trap, HidingSpot
        
        for obj in self.game.game_object_manager.objects:
            if not obj.is_active:
                continue
            
            # Only render if visible
            if (obj.x, obj.y) not in self.visible_tiles:
                continue
            
            world_x = obj.x * TILE_SIZE
            world_y = obj.y * TILE_SIZE
            screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
            
            if isinstance(obj, SecurityCamera):
                self._draw_security_camera(screen, screen_x, screen_y, obj)
            elif isinstance(obj, Trap):
                self._draw_trap_object(screen, screen_x, screen_y, obj)
            elif isinstance(obj, HidingSpot):
                self._draw_hiding_spot_object(screen, screen_x, screen_y, obj)
    
    def _render_debug(self, screen: pygame.Surface):
        # ... logic ...
        pass
    
    def _render_interaction_prompts(self, screen: pygame.Surface):
        """Draw 'E' prompt near interactable objects."""
        if not self.game.player or not self.game.level:
            return
            
        px, py = self.game.player.x, self.game.player.y
        
        # Check for game object interactions
        if hasattr(self.game, 'game_object_manager') and self.game.game_object_manager:
            from src.entities.game_objects import HidingSpot, Lever
            positions = [
                (int(px), int(py)),
                (int(px) + 1, int(py)),
                (int(px) - 1, int(py)),
                (int(px), int(py) + 1),
                (int(px), int(py) - 1),
            ]
            
            for pos in positions:
                for obj in self.game.game_object_manager.get_at(*pos):
                    if isinstance(obj, (HidingSpot, Lever)) and obj.is_active:
                        world_x = obj.x * TILE_SIZE + TILE_SIZE // 2
                        world_y = obj.y * TILE_SIZE - 10
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
        
        # Check adjacent cells for doors/levers
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
        y = 100  # Moved to top
        
        for text, time_left, color in self.notifications:
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
            
            y += 40  # Stack downwards
    
    def _draw_background(self, screen: pygame.Surface):
        """Draw gradient background."""
        screen.fill(COLORS.VOID)
    
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
        pulse = math.sin(self.pulse_time * 2.0) * 0.2 + 0.8
        
        # Outer glow
        glow_surf = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2), pygame.SRCALPHA)
        glow_radius = int(TILE_SIZE * 0.8 * pulse)
        pygame.draw.circle(glow_surf, (*COLORS.EXIT[:3], 50), (TILE_SIZE, TILE_SIZE), glow_radius)
        surface.blit(glow_surf, (x - TILE_SIZE // 2, y - TILE_SIZE // 2))
        
        color = tuple(int(c * pulse) for c in COLORS.EXIT)
        
        # Main Platform
        rect = (x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255), rect, 2, border_radius=4)
        
        # Upward Arrow Animation
        arrow_y_offset = (self.time * 20) % 10 - 5
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2 + arrow_y_offset
        
        # Draw Arrow
        points = [
            (center_x, center_y - 6),
            (center_x + 6, center_y + 2),
            (center_x - 6, center_y + 2)
        ]
        pygame.draw.polygon(surface, (255, 255, 255), points)
        pygame.draw.rect(surface, (255, 255, 255), (center_x - 2, center_y + 2, 4, 6))
    
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
        
        # Player is invisible when hiding
        if getattr(player, 'is_hidden', False):
            return
        
        # Blink effect if invulnerable
        if getattr(player, 'invulnerable_timer', 0) > 0:
            # Blink every 0.1s
            if int(self.time * 20) % 2 == 0:
                pass # Continue rendering but maybe transparent?
            else:
                return # Skip rendering for blink effect
        
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
        
        # UI Panel background (Glassmorphism)
        panel_width = 340
        panel_height = 90
        panel_x = 20
        panel_y = SCREEN_HEIGHT - panel_height - 20
        
        # Blur/Glass effect backing
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((10, 15, 25, 220))  # Dark blue semi-transparent
        screen.blit(s, (panel_x, panel_y))
        
        # Tech border
        pygame.draw.rect(screen, COLORS.UI_BORDER, (panel_x, panel_y, panel_width, panel_height), 2, border_radius=10)
        # Corner accents
        accent_len = 15
        pygame.draw.line(screen, COLORS.UI_ENERGY, (panel_x, panel_y), (panel_x + accent_len, panel_y), 2)
        pygame.draw.line(screen, COLORS.UI_ENERGY, (panel_x, panel_y), (panel_x, panel_y + accent_len), 2)
        pygame.draw.line(screen, COLORS.UI_ENERGY, (panel_x + panel_width - accent_len, panel_y + panel_height), (panel_x + panel_width, panel_y + panel_height), 2)
        pygame.draw.line(screen, COLORS.UI_ENERGY, (panel_x + panel_width, panel_y + panel_height - accent_len), (panel_x + panel_width, panel_y + panel_height), 2)

        base_x = panel_x + 20
        base_y = panel_y + 15
        
        # Health (Tech Blocks)
        hp_label = self.game.font_tiny.render("VITALS", True, COLORS.UI_TEXT_DIM)
        screen.blit(hp_label, (base_x, base_y))
        
        for i in range(player.max_health):
            block_w = 25
            block_h = 10
            spacing = 5
            x = base_x + i * (block_w + spacing)
            y = base_y + 15
            
            color = COLORS.UI_HEALTH if i < player.health else (40, 20, 20)
            pygame.draw.rect(screen, color, (x, y, block_w, block_h))
            if i < player.health:
                # Glow
                pygame.draw.rect(screen, (255, 100, 100), (x, y, block_w, 2))
        
        # Energy Bar (Tech Style)
        en_label = self.game.font_tiny.render("ENERGY", True, COLORS.UI_TEXT_DIM)
        screen.blit(en_label, (base_x, base_y + 35))
        
        bar_x = base_x
        bar_y = base_y + 50
        bar_width = 180
        bar_height = 6
        
        # Track
        pygame.draw.rect(screen, (20, 30, 40), (bar_x, bar_y, bar_width, bar_height))
        
        # Fill
        energy_ratio = player.energy / player.max_energy
        fill_width = int(bar_width * energy_ratio)
        if fill_width > 0:
            pygame.draw.rect(screen, COLORS.UI_ENERGY, (bar_x, bar_y, fill_width, bar_height))
            # Moving shine on bar
            shine_x = bar_x + (int(self.time * 100) % bar_width)
            if shine_x < bar_x + fill_width:
                 pygame.draw.rect(screen, (255, 255, 255, 200), (shine_x, bar_y, 5, bar_height))

        # Key Inventory (Right Side)
        key_box_x = panel_x + 250
        key_box_y = panel_y + 20
        box_size = 50
        
        # Box frame
        pygame.draw.rect(screen, (15, 20, 30), (key_box_x, key_box_y, box_size, box_size), border_radius=5)
        pygame.draw.rect(screen, COLORS.UI_BORDER, (key_box_x, key_box_y, box_size, box_size), 1, border_radius=5)
        
        # Key Label
        key_label = self.game.font_tiny.render("ACCESS", True, COLORS.UI_TEXT_DIM)
        screen.blit(key_label, (key_box_x + 5, key_box_y + box_size + 2))
        
        if player.keys > 0:
            # Draw big key icon
            cx, cy = key_box_x + box_size // 2, key_box_y + box_size // 2
            pulse = 1.0 + math.sin(self.time * 5) * 0.1
            
            # Glow
            glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*COLORS.KEY[:3], 50), (20, 20), 15 * pulse)
            screen.blit(glow_surf, (cx - 20, cy - 20))
            
            # Key
            rect_w = 6
            rect_h = 24
            pygame.draw.circle(screen, COLORS.KEY, (cx, cy - 5), 8)
            pygame.draw.rect(screen, COLORS.KEY, (cx - rect_w//2, cy, rect_w, rect_h))
            pygame.draw.rect(screen, COLORS.KEY, (cx, cy + 10, 8, 4))
            pygame.draw.rect(screen, COLORS.KEY, (cx, cy + 16, 6, 4))
        
        # Stealth Text overlay (Center Screen, not HUD panel)
        if getattr(player, 'is_stealthed', False):
            stealth_text = self.game.font_medium.render("-- STEALTH MODE --", True, COLORS.UI_STEALTH)
            rect = stealth_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
            # Blink
            if int(self.time * 4) % 2 == 0:
                screen.blit(stealth_text, rect)
        
        # Speedrun Timer (Top Right)
        if hasattr(self.game, 'stats_tracker'):
            import time
            elapsed = time.time() - self.game.stats_tracker.current_level_start_time
            timer_text = self._format_speedrun_time(elapsed)
            
            # Determine color based on star projection
            thresholds = self.game.stats_tracker.get_star_thresholds(self.game.current_level_num)
            if elapsed <= thresholds[0]:
                timer_color = (255, 215, 0)  # Gold - 3 stars
            elif elapsed <= thresholds[1]:
                timer_color = (192, 192, 192)  # Silver - 2 stars
            elif elapsed <= thresholds[2]:
                timer_color = (205, 127, 50)  # Bronze - 1 star
            else:
                timer_color = COLORS.UI_TEXT_DIM  # Gray - over time
            
            timer_surf = self.game.font_medium.render(timer_text, True, timer_color)
            timer_rect = timer_surf.get_rect(topright=(SCREEN_WIDTH - 20, 20))
            
            # Background for timer
            bg_rect = pygame.Rect(timer_rect.left - 10, timer_rect.top - 5, timer_rect.width + 20, timer_rect.height + 10)
            bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surf.fill((10, 15, 25, 220))
            screen.blit(bg_surf, bg_rect.topleft)
            pygame.draw.rect(screen, timer_color, bg_rect, 2, border_radius=5)
            
            screen.blit(timer_surf, timer_rect)
            
            # Star projection below timer
            stars = self._calculate_stars_for_time(elapsed, thresholds)
            star_display_y = timer_rect.bottom + 15
            star_size = 12
            star_spacing = 28
            star_start_x = SCREEN_WIDTH - 20 - star_spacing * 1.5
            
            for i in range(3):
                star_x = star_start_x + i * star_spacing
                self._draw_mini_star(screen, star_x, star_display_y, star_size, filled=(i < stars))
    
    def _format_speedrun_time(self, seconds):
        """Format time for speedrun display."""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:06.3f}"
    
    def _calculate_stars_for_time(self, elapsed, thresholds):
        """Calculate star rating for current time."""
        if elapsed <= thresholds[0]:
            return 3
        elif elapsed <= thresholds[1]:
            return 2
        elif elapsed <= thresholds[2]:
            return 1
        return 0
    
    def _draw_mini_star(self, surface, x, y, size, filled=True):
        """Draw a small star."""
        points = []
        for i in range(5):
            angle = math.pi / 2 + i * 2 * math.pi / 5
            outer_x = x + size * math.cos(angle)
            outer_y = y - size * math.sin(angle)
            points.append((outer_x, outer_y))
            
            angle += math.pi / 5
            inner_x = x + size * 0.4 * math.cos(angle)
            inner_y = y - size * 0.4 * math.sin(angle)
            points.append((inner_x, inner_y))
        
        if filled:
            pygame.draw.polygon(surface, COLORS.KEY, points)
        else:
            pygame.draw.polygon(surface, COLORS.UI_TEXT_DIM, points, 2)
    
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
    
    def _draw_security_camera(self, surface: pygame.Surface, x: int, y: int, camera):
        """Draw an animated security camera with vision cone."""
        from src.entities.game_objects import SecurityCamera
        
        # Camera body (small square)
        body_size = TILE_SIZE // 3
        body_rect = pygame.Rect(
            x + TILE_SIZE // 2 - body_size // 2,
            y + TILE_SIZE // 2 - body_size // 2,
            body_size, body_size
        )
        
        # Color based on state
        if camera.is_disabled:
            body_color = (80, 80, 80)
            lens_color = (40, 40, 40)
        elif camera.alert_triggered:
            body_color = (255, 0, 0)
            lens_color = (255, 100, 100)
        elif camera.detection_timer > 0:
            body_color = (255, 165, 0)
            lens_color = (255, 200, 100)
        else:
            body_color = (100, 100, 150)
            lens_color = (150, 150, 255)
        
        pygame.draw.rect(surface, body_color, body_rect, border_radius=3)
        
        # Lens (direction indicator)
        facing_angle = math.atan2(camera.facing_direction[1], camera.facing_direction[0])
        lens_x = x + TILE_SIZE // 2 + math.cos(facing_angle) * (body_size // 2)
        lens_y = y + TILE_SIZE // 2 + math.sin(facing_angle) * (body_size // 2)
        pygame.draw.circle(surface, lens_color, (int(lens_x), int(lens_y)), 4)
        
        # Draw vision cone (simplified)
        if not camera.is_disabled:
            cone_color = (*lens_color[:3], 30)
            cone_surface = pygame.Surface((TILE_SIZE * 8, TILE_SIZE * 8), pygame.SRCALPHA)
            
            start_angle = facing_angle - math.radians(camera.vision_angle / 2)
            end_angle = facing_angle + math.radians(camera.vision_angle / 2)
            
            center = (TILE_SIZE * 4, TILE_SIZE * 4)
            radius = int(camera.vision_range * TILE_SIZE)
            
            points = [center]
            for i in range(20):
                angle = start_angle + (end_angle - start_angle) * i / 19
                px = center[0] + math.cos(angle) * radius
                py = center[1] + math.sin(angle) * radius
                points.append((px, py))
            points.append(center)
            
            pygame.draw.polygon(cone_surface, cone_color, points)
            
            cone_x = x + TILE_SIZE // 2 - TILE_SIZE * 4
            cone_y = y + TILE_SIZE // 2 - TILE_SIZE * 4
            surface.blit(cone_surface, (cone_x, cone_y))
    
    def _draw_trap_object(self, surface: pygame.Surface, x: int, y: int, trap):
        """Draw a trap object."""
        from src.entities.game_objects import Trap
        
        if trap.is_hidden:
            return
        
        # Trap appearance
        if trap.is_triggered:
            color = (255, 50, 50)
            inner_color = (200, 0, 0)
        else:
            color = (200, 100, 0)
            inner_color = (150, 50, 0)
        
        # Draw as spikes/danger pattern
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2
        
        # Outer danger border
        danger_rect = pygame.Rect(x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8)
        pygame.draw.rect(surface, color, danger_rect, 2)
        
        # Inner pattern
        for i in range(3):
            for j in range(3):
                spike_x = x + 8 + i * 10
                spike_y = y + 8 + j * 10
                pygame.draw.circle(surface, inner_color, (spike_x, spike_y), 2)
        
        # Pulsing effect when triggered
        if trap.is_triggered:
            pulse = abs(math.sin(self.time * 10)) * 10
            glow_rect = danger_rect.inflate(pulse, pulse)
            pygame.draw.rect(surface, (255, 0, 0, 100), glow_rect, 3)
    
    def _draw_hiding_spot_object(self, surface: pygame.Surface, x: int, y: int, hiding_spot):
        """Draw a hiding spot object."""
        from src.entities.game_objects import HidingSpot
        
        # Draw as a locker/crate
        color = (120, 80, 40)
        highlight = (150, 110, 70)
        
        # Body
        body_rect = pygame.Rect(x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8)
        pygame.draw.rect(surface, color, body_rect, border_radius=2)
        
        # Highlight edges
        pygame.draw.rect(surface, highlight, body_rect, 2, border_radius=2)
        
        # Vertical lines to indicate slats/doors
        for i in range(1, 3):
            line_x = x + (TILE_SIZE // 3) * i
            pygame.draw.line(surface, highlight, (line_x, y + 6), (line_x, y + TILE_SIZE - 6), 1)
        
        # Occupied indicator
        if hiding_spot.currently_hiding > 0:
            dot_x = x + TILE_SIZE - 10
            dot_y = y + 10
            pygame.draw.circle(surface, (0, 255, 0), (dot_x, dot_y), 4)
            pygame.draw.circle(surface, (0, 200, 0), (dot_x, dot_y), 2)
