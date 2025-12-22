"""
Maze Bourne - Main Renderer
Handles all game rendering including level, entities, UI, and effects
"""

import pygame
import math
import time
from typing import Optional, List, Tuple, Set
from dataclasses import dataclass

from src.core.constants import (
    TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, COLORS, 
    CellType, EnemyType, EnemyState
)
from src.graphics.camera import Camera
from src.graphics.particle_system import ParticleSystem


class Renderer:
    """
    Main rendering system for Maze Bourne.
    Handles camera, particles, FOV, vision cones, and all visual effects.
    """
    
    def __init__(self, game):
        self.game = game
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.particle_system = ParticleSystem()
        
        # Visibility tracking
        self.visible_tiles: Set[Tuple[int, int]] = set()
        self.fov_enabled = True
        
        # Animation timing
        self.time = 0.0
        
        # Notification system
        self.notifications = []
        
        # Font for UI
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)
    
    def update(self, dt: float):
        """Update renderer state."""
        self.time += dt
        self.particle_system.update(dt)
        
        # Update notifications
        for notif in self.notifications[:]:
            notif['time'] -= dt
            if notif['time'] <= 0:
                self.notifications.remove(notif)
        
        # Update camera to follow player
        if self.game.player:
            target_x = self.game.player.x * TILE_SIZE + TILE_SIZE // 2
            target_y = self.game.player.y * TILE_SIZE + TILE_SIZE // 2
            self.camera.follow(target_x, target_y, dt)
        
        # Update FOV
        if self.game.player and self.game.level:
            self._update_fov()
    
    def render(self, screen: pygame.Surface):
        """Main render function."""
        screen.fill(COLORS.BACKGROUND)
        
        if not self.game.level:
            return
        
        # Render game world
        self._render_level(screen)
        self._render_vision_cones(screen)
        self._render_game_objects(screen)
        self._render_enemies(screen)
        self._render_boss(screen)
        self._render_player(screen)
        self._render_particles(screen)
        
        # Render UI overlays
        self._render_interaction_prompts(screen)
        self._render_hud(screen)
        self._render_notifications(screen)
        
        # Debug overlays
        if self.game.debug_mode:
            self._render_debug_overlay(screen)
    
    def _update_fov(self):
        """Calculate visible tiles from player perspective."""
        if not self.fov_enabled or not self.game.player or not self.game.level:
            # Show all tiles if FOV disabled
            self.visible_tiles = {(x, y) for x in range(self.game.level.width) 
                                 for y in range(self.game.level.height)}
            return
        
        self.visible_tiles.clear()
        
        # Player is always hidden - show limited FOV
        if getattr(self.game.player, 'is_hidden', False):
            # Very limited vision when hidden
            px, py = int(self.game.player.x), int(self.game.player.y)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    self.visible_tiles.add((px + dx, py + dy))
            return
        
        # Normal FOV calculation
        vision_range = 12  # tiles
        px, py = self.game.player.x, self.game.player.y
        
        # Raycast in all directions
        num_rays = 360
        for i in range(num_rays):
            angle = (i / num_rays) * 2 * math.pi
            dx = math.cos(angle)
            dy = math.sin(angle)
            
            for distance in range(vision_range):
                check_x = px + dx * distance
                check_y = py + dy * distance
                tile_x, tile_y = int(check_x), int(check_y)
                
                if 0 <= tile_x < self.game.level.width and 0 <= tile_y < self.game.level.height:
                    self.visible_tiles.add((tile_x, tile_y))
                    
                    # Stop at walls
                    if not self.game.level.is_walkable(tile_x, tile_y):
                        break
                else:
                    break
    
    def _render_level(self, screen: pygame.Surface):
        """Render the maze grid."""
        if not self.game.level:
            return
        
        for y in range(self.game.level.height):
            for x in range(self.game.level.width):
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
                
                # Check if tile is visible
                is_visible = (x, y) in self.visible_tiles
                
                # Get cell type
                cell = self.game.level.cells.get((x, y))
                if not cell:
                    continue
                
                # Choose color
                if cell.cell_type == CellType.WALL:
                    color = COLORS.WALL
                elif cell.cell_type == CellType.FLOOR:
                    color = COLORS.FLOOR
                elif cell.cell_type == CellType.KEY:
                    if (x, y) not in self.game.level.collected_keys:
                        color = COLORS.KEY
                        # Draw key icon
                        if is_visible:
                            self._draw_key(screen, screen_x, screen_y)
                        continue
                    else:
                        color = COLORS.FLOOR
                elif cell.cell_type == CellType.EXIT:
                    color = COLORS.EXIT
                elif cell.cell_type == CellType.DOOR:
                    if (x, y) in self.game.level.opened_doors:
                        color = COLORS.FLOOR
                    else:
                        color = COLORS.DOOR
                else:
                    color = COLORS.FLOOR
                
                # Apply fog of war
                if not is_visible:
                    color = tuple(c // 3 for c in color)
                
                # Draw tile
                rect = pygame.Rect(screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, color, rect)
                
                # Draw grid lines (subtle)
                if self.game.debug_mode:
                    pygame.draw.rect(screen, (50, 50, 50), rect, 1)
    
    def _draw_key(self, screen: pygame.Surface, x: int, y: int):
        """Draw a key icon."""
        # Golden glow
        glow_size = TILE_SIZE // 2 + int(math.sin(self.time * 3) * 4)
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*COLORS.KEY[:3], 40), (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (x + TILE_SIZE // 2 - glow_size, y + TILE_SIZE // 2 - glow_size))
        
        # Key body
        key_size = TILE_SIZE // 3
        pygame.draw.circle(screen, COLORS.KEY, 
                         (x + TILE_SIZE // 2, y + TILE_SIZE // 2), key_size)
        
        # Shine effect
        shine_offset = int(math.sin(self.time * 2) * 2)
        pygame.draw.circle(screen, (255, 255, 200), 
                         (x + TILE_SIZE // 2 - 4 + shine_offset, y + TILE_SIZE // 2 - 4), 3)
    
    def _render_vision_cones(self, screen: pygame.Surface):
        """Render enemy and camera vision cones."""
        if not self.game.level:
            return
        
        from src.entities.game_objects import SecurityCamera
        
        # 1. Render Enemy Cones
        for enemy in self.game.enemies:
            if not enemy.is_alive or getattr(enemy, 'is_hiding', False):
                continue
            
            facing_angle = math.atan2(enemy.facing_direction[1], enemy.facing_direction[0])
            
            # Get clipped polygon points
            world_points = self._calculate_vision_polygon(
                enemy.pos.x, enemy.pos.y, 
                facing_angle, enemy.vision_angle, enemy.vision_range
            )
            
            # Different colors based on state
            if enemy.state == EnemyState.ALERT or enemy.state == EnemyState.CHASE:
                color_base = (255, 0, 0)
            elif enemy.state == EnemyState.SUSPICIOUS or enemy.state == EnemyState.SEARCH:
                color_base = (255, 165, 0)
            else:
                color_base = (255, 255, 0)
            
            self._draw_vision_polygon(screen, world_points, color_base)
        
        # 2. Render Camera Cones
        if hasattr(self.game, 'game_object_manager') and self.game.game_object_manager:
            for obj in self.game.game_object_manager.objects:
                if isinstance(obj, SecurityCamera) and not obj.is_disabled:
                    facing_angle = math.atan2(obj.facing_direction[1], obj.facing_direction[0])
                    
                    # Get clipped polygon points
                    world_points = self._calculate_vision_polygon(
                        obj.x, obj.y,
                        facing_angle, obj.vision_angle, obj.vision_range
                    )
                    
                    lens_color = (255, 100, 100) if obj.alert_triggered else (150, 150, 255)
                    self._draw_vision_polygon(screen, world_points, lens_color)

    def _draw_vision_polygon(self, screen, world_points, color_base):
        """Helper to draw a single vision polygon."""
        if len(world_points) > 2:
            # Convert to SCREEN coordinates
            screen_points = []
            for wx, wy in world_points:
                    sx, sy = self.camera.world_to_screen(wx, wy)
                    screen_points.append((sx, sy))
            
            # Draw
            min_x = min(p[0] for p in screen_points)
            min_y = min(p[1] for p in screen_points)
            max_x = max(p[0] for p in screen_points)
            max_y = max(p[1] for p in screen_points)
            w, h = max(1, max_x - min_x), max(1, max_y - min_y)
            
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            local_points = [(p[0] - min_x, p[1] - min_y) for p in screen_points]
            pygame.draw.polygon(surf, (*color_base, 30), local_points)
            screen.blit(surf, (min_x, min_y))

    def _calculate_vision_polygon(self, cx, cy, facing_angle, vision_angle, vision_range) -> List[Tuple[float, float]]:
        """Calculate vision cone polygon clipped by walls."""
        points = []
        
        # Center point
        center_world_x = cx * TILE_SIZE + TILE_SIZE // 2
        center_world_y = cy * TILE_SIZE + TILE_SIZE // 2
        points.append((center_world_x, center_world_y))
        
        # Arc points
        half_angle = math.radians(vision_angle / 2)
        num_samples = 20
        
        for i in range(num_samples + 1):
            t = i / num_samples
            angle = facing_angle - half_angle + (half_angle * 2 * t)
            
            # Raycast to find actual endpoint
            max_dist = vision_range * TILE_SIZE
            dx = math.cos(angle)
            dy = math.sin(angle)
            
            # Check for wall collision
            dist = max_dist
            for step in range(int(vision_range * 2)):
                check_dist = step * TILE_SIZE / 2
                if check_dist > max_dist:
                    break
                
                check_x = cx + (dx * check_dist) / TILE_SIZE
                check_y = cy + (dy * check_dist) / TILE_SIZE
                
                if self.game.level and not self.game.level.is_walkable(int(check_x), int(check_y)):
                    dist = check_dist
                    break
            
            end_x = center_world_x + dx * dist
            end_y = center_world_y + dy * dist
            points.append((end_x, end_y))
        
        return points
    
    def _render_enemies(self, screen: pygame.Surface):
        """Render all enemies."""
        for enemy in self.game.enemies:
            if not enemy.is_alive:
                continue
            
            # Only render visible enemies
            if (int(enemy.pos.x), int(enemy.pos.y)) not in self.visible_tiles:
                continue
            
            world_x = enemy.pos.x * TILE_SIZE
            world_y = enemy.pos.y * TILE_SIZE
            screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
            
            # Choose color based on type and state
            if enemy.state == EnemyState.ALERT or enemy.state == EnemyState.CHASE:
                color = (255, 0, 0)
            elif enemy.state == EnemyState.SUSPICIOUS or enemy.state == EnemyState.SEARCH:
                color = (255, 165, 0)
            else:
                # Normal patrol colors
                if enemy.enemy_type == EnemyType.PATROL:
                    color = COLORS.ENEMY_PATROL
                elif enemy.enemy_type == EnemyType.TRACKER:
                    color = COLORS.ENEMY_TRACKER
                elif enemy.enemy_type == EnemyType.SOUND_HUNTER:
                    color = COLORS.ENEMY_HUNTER
                elif enemy.enemy_type == EnemyType.SIGHT_GUARD:
                    color = COLORS.ENEMY_GUARD
                else:
                    color = COLORS.ENEMY_PATROL
            
            # Draw enemy body
            padding = 4
            pygame.draw.rect(screen, color,
                           (screen_x + padding, screen_y + padding,
                            TILE_SIZE - padding * 2, TILE_SIZE - padding * 2),
                           border_radius=3)
            
            # Draw facing direction indicator
            center_x = screen_x + TILE_SIZE // 2
            center_y = screen_y + TILE_SIZE // 2
            facing_x = center_x + enemy.facing_direction[0] * 12
            facing_y = center_y + enemy.facing_direction[1] * 12
            pygame.draw.line(screen, (255, 255, 255), (center_x, center_y), (facing_x, facing_y), 2)
    
    def _render_game_objects(self, screen: pygame.Surface):
        """Render all game objects (cameras, traps, hiding spots)."""
        if not hasattr(self.game, 'game_object_manager') or not self.game.game_object_manager:
            return
        
        from src.entities.game_objects import SecurityCamera, Trap, HidingSpot, Lever
        from src.entities.boss import BossButton
        
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
            elif isinstance(obj, Lever):
                self._draw_lever_object(screen, screen_x, screen_y, obj)
            elif isinstance(obj, BossButton):
                self._draw_boss_button_object(screen, screen_x, screen_y, obj)
    
    def _render_interaction_prompts(self, screen: pygame.Surface):
        """Draw 'E' prompt near interactable objects."""
        if not self.game.player or not self.game.level:
            return
            
        px, py = self.game.player.x, self.game.player.y
        
        # Check for game object interactions
        if hasattr(self.game, 'game_object_manager') and self.game.game_object_manager:
            from src.entities.game_objects import HidingSpot, Lever
            from src.entities.boss import BossButton
            positions = [
                (int(px), int(py)),
                (int(px) + 1, int(py)),
                (int(px) - 1, int(py)),
                (int(px), int(py) + 1),
                (int(px), int(py) - 1),
            ]
            
            for pos in positions:
                for obj in self.game.game_object_manager.get_at(*pos):
                    if isinstance(obj, (HidingSpot, Lever, BossButton)) and obj.is_active:
                        world_x = obj.x * TILE_SIZE + TILE_SIZE // 2
                        world_y = obj.y * TILE_SIZE - 10
                        sx, sy = self.camera.world_to_screen(world_x, world_y)
                        
                        # Bobbing motion
                        bob = math.sin(self.time * 4) * 3
                        sy += bob
                        
                        # Draw E prompt
                        text = self.font_small.render("E", True, (255, 255, 255))
                        text_rect = text.get_rect(center=(sx, sy))
                        
                        # Background circle
                        pygame.draw.circle(screen, (0, 0, 0, 180), (sx, sy), 15)
                        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 15, 2)
                        screen.blit(text, text_rect)
                        return  # Only show one prompt
    
    def _render_player(self, screen: pygame.Surface):
        """Render the player."""
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
        
        # Parry indicator
        if getattr(player, 'is_parrying', False):
            # Shield effect
            shield_surf = pygame.Surface((TILE_SIZE + 20, TILE_SIZE + 20), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (100, 200, 255, 100), 
                             (TILE_SIZE // 2 + 10, TILE_SIZE // 2 + 10), TILE_SIZE // 2 + 10)
            pygame.draw.circle(shield_surf, (150, 220, 255, 200), 
                             (TILE_SIZE // 2 + 10, TILE_SIZE // 2 + 10), TILE_SIZE // 2 + 10, 3)
            screen.blit(shield_surf, (screen_x - 10, screen_y - 10))
    
    def _render_particles(self, screen: pygame.Surface):
        """Render particle effects."""
        self.particle_system.render(screen, self.camera)
    
    def _render_hud(self, screen: pygame.Surface):
        """Render heads-up display."""
        if not self.game.player:
            return
        
        # Health bar
        health_width = 200
        health_height = 20
        health_x = 20
        health_y = 20
        
        # Background
        pygame.draw.rect(screen, (50, 50, 50), 
                        (health_x, health_y, health_width, health_height),
                        border_radius=5)
        
        # Health fill
        health_ratio = self.game.player.health / self.game.player.max_health
        fill_width = int(health_width * health_ratio)
        health_color = COLORS.UI_HEALTH if health_ratio > 0.3 else (255, 0, 0)
        pygame.draw.rect(screen, health_color,
                        (health_x, health_y, fill_width, health_height),
                        border_radius=5)
        
        # Border
        pygame.draw.rect(screen, (200, 200, 200),
                        (health_x, health_y, health_width, health_height), 2,
                        border_radius=5)
        
        # Health text
        health_text = self.font_small.render(f"HP: {self.game.player.health}/{self.game.player.max_health}", 
                                            True, COLORS.UI_TEXT)
        screen.blit(health_text, (health_x + 5, health_y + 2))
        
        # Energy bar
        energy_x = health_x
        energy_y = health_y + 30
        
        pygame.draw.rect(screen, (50, 50, 50),
                        (energy_x, energy_y, health_width, health_height),
                        border_radius=5)
        
        energy_ratio = self.game.player.energy / self.game.player.max_energy
        energy_fill = int(health_width * energy_ratio)
        pygame.draw.rect(screen, COLORS.UI_ENERGY,
                        (energy_x, energy_y, energy_fill, health_height),
                        border_radius=5)
        
        pygame.draw.rect(screen, (200, 200, 200),
                        (energy_x, energy_y, health_width, health_height), 2,
                        border_radius=5)
        
        energy_text = self.font_small.render(f"Energy: {int(self.game.player.energy)}", 
                                             True, COLORS.UI_TEXT)
        screen.blit(energy_text, (energy_x + 5, energy_y + 2))
        
        # Keys collected
        if self.game.player.keys > 0:
            key_text = self.font.render(f"🔑 x{self.game.player.keys}", True, COLORS.KEY)
            screen.blit(key_text, (health_x, energy_y + 35))
    
    def _render_notifications(self, screen: pygame.Surface):
        """Render notification messages."""
        y_offset = SCREEN_HEIGHT - 100
        
        for notif in self.notifications:
            alpha = min(255, int(notif['time'] * 255))
            text_surf = self.font.render(notif['message'], True, notif['color'])
            text_surf.set_alpha(alpha)
            
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            screen.blit(text_surf, text_rect)
            y_offset -= 40
    
    def add_notification(self, message: str, color=(255, 255, 255), duration: float = 2.0):
        """Add a notification message."""
        self.notifications.append({
            'message': message,
            'color': color,
            'time': duration
        })
    
    def _render_debug_overlay(self, screen: pygame.Surface):
        """Render debug information."""
        if not self.game.player:
            return
        
        debug_lines = [
            f"Pos: ({self.game.player.x:.1f}, {self.game.player.y:.1f})",
            f"Health: {self.game.player.health}/{self.game.player.max_health}",
            f"Energy: {int(self.game.player.energy)}/{self.game.player.max_energy}",
            f"Enemies: {len([e for e in self.game.enemies if e.is_alive])}",
            f"FPS: {self.game.fps:.1f}",
        ]
        
        y = 120
        for line in debug_lines:
            text = self.font_small.render(line, True, (255, 255, 0))
            screen.blit(text, (20, y))
            y += 25
    
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
    
    def _draw_lever_object(self, surface: pygame.Surface, x: int, y: int, lever):
        """Draw a lever switch."""
        from src.entities.game_objects import Lever
        
        # Base platform
        base_color = (80, 80, 80)
        base_rect = pygame.Rect(x + 8, y + TILE_SIZE - 12, TILE_SIZE - 16, 8)
        pygame.draw.rect(surface, base_color, base_rect, border_radius=2)
        
        # Lever handle
        center_x = x + TILE_SIZE // 2
        base_y = y + TILE_SIZE - 8
        
        if lever.is_on:
            # Lever pulled (tilted right)
            handle_color = (100, 255, 100)
            handle_end_x = center_x + 12
            handle_end_y = base_y - 16
        else:
            # Lever not pulled (tilted left)
            handle_color = (200, 200, 200)
            handle_end_x = center_x - 12
            handle_end_y = base_y - 16
        
        # Draw lever arm
        pygame.draw.line(surface, handle_color, (center_x, base_y), (handle_end_x, handle_end_y), 4)
        
        # Draw handle knob
        pygame.draw.circle(surface, handle_color, (handle_end_x, handle_end_y), 5)
        
        # Glow effect when active
        if lever.is_on:
            glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (100, 255, 100, 60), (15, 15), 15)
            surface.blit(glow_surf, (handle_end_x - 15, handle_end_y - 15))
    
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
    
    def _draw_boss_button_object(self, surface: pygame.Surface, x: int, y: int, button):
        """Draw a boss button."""
        from src.entities.boss import BossButton
        
        # Button platform
        platform_color = (80, 80, 100)
        platform_rect = pygame.Rect(x + 6, y + 6, TILE_SIZE - 12, TILE_SIZE - 12)
        pygame.draw.rect(surface, platform_color, platform_rect, border_radius=3)
        
        # Button state
        if button.is_pressed:
            button_color = (50, 255, 50)
            button_offset = 4
        else:
            button_color = (200, 50, 50)
            button_offset = 2
        
        # Button top
        button_rect = pygame.Rect(x + 10, y + 10 + button_offset, TILE_SIZE - 20, TILE_SIZE - 20)
        pygame.draw.circle(surface, button_color, button_rect.center, button_rect.width // 2)
        
        # Glow effect when pressed
        if button.is_pressed:
            glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (50, 255, 50, 80), (20, 20), 20)
            surface.blit(glow_surf, (x + TILE_SIZE // 2 - 20, y + TILE_SIZE // 2 - 20))
    
    
    def _render_boss(self, screen: pygame.Surface):
        """Render the boss if active."""
        if not hasattr(self.game, 'current_boss') or not self.game.current_boss:
            return
        
        boss = self.game.current_boss
        if not boss.is_alive:
            return
        
        # Convert boss position to screen coordinates
        world_x = boss.x * TILE_SIZE
        world_y = boss.y * TILE_SIZE
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
        
        # Boss size (larger than normal enemies)
        boss_size = int(TILE_SIZE * boss.size)
        center_x = screen_x + boss_size // 2
        center_y = screen_y + boss_size // 2
        
        # Flash effect
        if boss.flash_timer > 0:
            flash_alpha = int((boss.flash_timer / 0.5) * 100)
            flash_surf = pygame.Surface((boss_size + 10, boss_size + 10), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha), (boss_size // 2 + 5, boss_size // 2 + 5), boss_size // 2 + 5)
            screen.blit(flash_surf, (screen_x - 5, screen_y - 5))
        
        # Boss body color based on state
        if boss.is_vulnerable:
            body_color = (255, 200, 50)
        elif boss.state.name == 'STUNNED':
            body_color = (150, 150, 200)
        elif boss.is_enraged:
            body_color = (255, 50, 50)
        else:
            body_color = (150, 50, 150)
        
        # Boss body
        pygame.draw.circle(screen, body_color, (center_x, center_y), boss_size // 2)
        pygame.draw.circle(screen, (100, 30, 100), (center_x, center_y), boss_size // 2, 3)
        
        # Facing direction indicator
        facing_x = center_x + boss.facing_direction[0] * (boss_size // 2 + 5)
        facing_y = center_y + boss.facing_direction[1] * (boss_size // 2 + 5)
        pygame.draw.line(screen, (255, 255, 255), (center_x, center_y), (facing_x, facing_y), 3)
        
        # Attack telegraph (during charging state)
        if boss.state.name == 'CHARGING' and boss.current_attack:
            atk = boss.current_attack
            progress = boss.attack_timer / atk.windup_time
            
            # Draw warning indicator
            telegraph_surf = pygame.Surface((boss_size + 20, boss_size + 20), pygame.SRCALPHA)
            alpha = int(100 + 155 * abs(math.sin(progress * 6.28 * 2)))
            pygame.draw.circle(telegraph_surf, (255, 0, 0, alpha), (boss_size // 2 + 10, boss_size // 2 + 10), boss_size // 2 + 10, 4)
            screen.blit(telegraph_surf, (screen_x - 10, screen_y - 10))
        
        # Vulnerability indicator
        if boss.is_vulnerable:
            text = self.font_small.render("VULNERABLE!", True, (255, 255, 0))
            text_x = center_x - text.get_width() // 2
            text_y = screen_y - 25
            screen.blit(text, (text_x, text_y))

    # =========================================================================
    # Public Boss Render Methods
    # =========================================================================

    def render_boss(self, boss, camera=None):
        """Public wrapper for boss rendering."""
        # We ignore arguments and use internal state for consistency with existing architecture
        self._render_boss(self.game.screen)

    def render_boss_button(self, button, camera=None):
        """Render a boss button."""
        screen = self.game.screen
        world_x = button.x * TILE_SIZE
        world_y = button.y * TILE_SIZE
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)
        self._draw_boss_button_object(screen, screen_x, screen_y, button)

    def render_boss_ui(self, boss):
        """Render boss UI elements (Big Top Health Bar)."""
        screen = self.game.screen
        
        # Config
        bar_width = 600
        bar_height = 25
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = 50
        
        # Background
        pygame.draw.rect(screen, (40, 0, 0), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
        
        # Health Fill
        health_pct = max(0, boss.health / boss.max_health)
        fill_width = int(bar_width * health_pct)
        
        # Color transition (Green -> Yellow -> Red)
        if health_pct > 0.6:
            color = (50, 255, 50)
        elif health_pct > 0.3:
            color = (255, 200, 0)
        else:
            color = (255, 0, 0)
            
        pygame.draw.rect(screen, color, (bar_x, bar_y, fill_width, bar_height), border_radius=5)
        
        # Border
        pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2, border_radius=5)
        
        # Boss Name
        name_text = self.font_medium.render(f"FLOOR {boss.tier * 10} GUARDIAN", True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(SCREEN_WIDTH // 2, bar_y - 15))
        
        # Shadow for text
        shadow = self.font_medium.render(f"FLOOR {boss.tier * 10} GUARDIAN", True, (0, 0, 0))
        shadow_rect = shadow.get_rect(center=(SCREEN_WIDTH // 2 + 2, bar_y - 13))
        screen.blit(shadow, shadow_rect)
        screen.blit(name_text, name_rect)

