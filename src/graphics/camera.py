
import pygame
from src.core.constants import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT

class Camera:
    def __init__(self, width: int, height: int):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.zoom = 1.0
        
    def apply(self, entity):
        """Return the rect of an entity offset by the camera."""
        if hasattr(entity, 'rect'):
            return entity.rect.move(self.camera.topleft)
        elif isinstance(entity, pygame.Rect):
            return entity.move(self.camera.topleft)
        # Handle tuple pos
        return (entity[0] + self.camera.x, entity[1] + self.camera.y)
        
    def apply_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(self.camera.topleft)
        
    def apply_point(self, pos: tuple) -> tuple:
        return (pos[0] + self.camera.x, pos[1] + self.camera.y)
        
    def world_to_screen(self, x: float, y: float) -> tuple:
        """Convert world coordinates to screen coordinates."""
        return (x + self.camera.x, y + self.camera.y)

    def screen_to_world(self, x: float, y: float) -> tuple:
        """Convert screen coordinates to world coordinates."""
        return (x - self.camera.x, y - self.camera.y)

    def update(self, target):
        """Follow a target sprite/entity."""
        if not target:
            return
            
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)

        # Limit scrolling to map size (if we had map size here, but we don't always know it)
        # For now, simple centering
        self.camera = pygame.Rect(x, y, self.width, self.height)
