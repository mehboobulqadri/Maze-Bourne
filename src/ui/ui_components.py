import pygame
from typing import Callable, Optional, Tuple, Any
from src.core.constants import COLORS

class Button:
    def __init__(self, x: int, y: int, width: int, height: int, 
                 text: str, font: pygame.font.Font, 
                 action: Callable = None, 
                 bg_color: Tuple = COLORS.UI_BG,
                 hover_color: Tuple = COLORS.WALL_HIGHLIGHT,
                 text_color: Tuple = COLORS.UI_TEXT):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.action = action
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        
        self.is_hovered = False
        self.is_pressed = False
        
        # Pre-render text
        self.text_surf = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)
    
    def update(self, mouse_pos, mouse_click, audio_manager=None) -> bool:
        """Update state. Returns True if clicked."""
        was_hovered = self.is_hovered
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        if self.is_hovered and not was_hovered and audio_manager:
            audio_manager.play_sound("sfx_ui_hover", 0.5)
            
        clicked = False
        if self.is_hovered and mouse_click:
            self.is_pressed = True
        elif not mouse_click and self.is_pressed:
            if self.is_hovered:
                # Click released inside
                clicked = True
                if audio_manager:
                    audio_manager.play_sound("sfx_ui_select", 0.8)
                if self.action:
                    self.action()
            self.is_pressed = False
        elif not mouse_click:
             self.is_pressed = False
             
        return clicked

    def draw(self, surface: pygame.Surface):
        color = self.hover_color if self.is_hovered else self.bg_color
        
        # Draw shadow
        pygame.draw.rect(surface, (0, 0, 0, 100), self.rect.move(2, 2), border_radius=6)
        
        # Draw button
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLORS.UI_BORDER, self.rect, 2, border_radius=6)
        
        # Draw glow if hovered
        if self.is_hovered:
            pygame.draw.rect(surface, (255, 255, 255, 50), self.rect, border_radius=6)
        
        surface.blit(self.text_surf, self.text_rect)

class Slider:
    def __init__(self, x: int, y: int, width: int, height: int, 
                 min_val: float, max_val: float, current_val: float,
                 label: str, font: pygame.font.Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = current_val
        self.label = label
        self.font = font
        
        self.is_dragging = False
        self.handle_width = 16
        
    def update(self, mouse_pos, mouse_down) -> float:
        """Update state. Returns current value."""
        # Calculate handle pos
        ratio = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        handle_x = self.rect.x + int(ratio * (self.rect.width - self.handle_width))
        handle_rect = pygame.Rect(handle_x, self.rect.y - 4, self.handle_width, self.rect.height + 8)
        
        if mouse_down:
            if handle_rect.collidepoint(mouse_pos) or (self.rect.collidepoint(mouse_pos) and not self.is_dragging):
                self.is_dragging = True
        else:
            self.is_dragging = False
            
        if self.is_dragging:
            rel_x = mouse_pos[0] - self.rect.x - self.handle_width / 2
            ratio = max(0.0, min(1.0, rel_x / (self.rect.width - self.handle_width)))
            self.current_val = self.min_val + ratio * (self.max_val - self.min_val)
            
        return self.current_val

    def draw(self, surface: pygame.Surface):
        # Label
        label_surf = self.font.render(f"{self.label}: {self.current_val:.1f}", True, COLORS.UI_TEXT)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 25))
        
        # Track Background
        draw_rect = pygame.Rect(self.rect.x, self.rect.y + 4, self.rect.width, 4)
        pygame.draw.rect(surface, (0, 0, 0), draw_rect, border_radius=2)
        
        # Filled Track
        ratio = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        fill_width = int(ratio * self.rect.width)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y + 4, fill_width, 4)
        pygame.draw.rect(surface, COLORS.UI_ENERGY, fill_rect, border_radius=2)
        
        # Handle
        handle_x = self.rect.x + int(ratio * (self.rect.width - self.handle_width))
        handle_rect = pygame.Rect(handle_x, self.rect.y - 4, self.handle_width, self.rect.height + 8)
        
        pygame.draw.rect(surface, COLORS.UI_TEXT, handle_rect, border_radius=4)
        if self.is_dragging:
             pygame.draw.rect(surface, (255, 255, 255), handle_rect, 2, border_radius=4)
