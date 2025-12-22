import pygame
from typing import Dict, Optional, Any
from src.ui.theme import UITheme
from src.core.constants import SCREEN_WIDTH, SCREEN_HEIGHT

class Screen:
    """Abstract base class for all UI screens (Menu, HUD, Pause, etc)."""
    def __init__(self, manager):
        self.manager = manager
        self.fonts = manager.fonts
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input event. Return True if consumed."""
        return False
        
    def update(self, dt: float):
        """Update logic (animations, etc)."""
        pass
        
    def draw(self, surface: pygame.Surface):
        """Render the screen."""
        pass
        
    def on_enter(self, **kwargs):
        """Called when this screen becomes active."""
        pass
        
    def on_exit(self):
        """Called when leaving this screen."""
        pass

class UIManager:
    """Central manager for UI screens and global state."""
    
    def __init__(self, game):
        self.game = game
        self.fonts = UITheme.load_fonts()
        self.screens: Dict[str, Screen] = {}
        self.active_screen: Optional[Screen] = None
        self.overlay_screen: Optional[Screen] = None # For Pause Menu over Game
        
        # Global UI State
        self.mouse_pos = (0, 0)
        
    def register_screen(self, name: str, screen: Screen):
        self.screens[name] = screen
        
    def switch_screen(self, name: str, **kwargs):
        """Switch the main active screen."""
        if self.active_screen:
            self.active_screen.on_exit()
        
        if name in self.screens:
            self.active_screen = self.screens[name]
            self.active_screen.on_enter(**kwargs)
            self.overlay_screen = None # Clear overlay on Switch
        else:
            print(f"ERROR: Screen '{name}' not found!")
            
    def set_overlay(self, name: str, **kwargs):
        """Set a screen as an overlay (e.g. Pause Menu)"""
        if name in self.screens:
            self.overlay_screen = self.screens[name]
            self.overlay_screen.on_enter(**kwargs)
        else:
            self.overlay_screen = None

    def clear_overlay(self):
        if self.overlay_screen:
            self.overlay_screen.on_exit()
            self.overlay_screen = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Route events to overlay first, then active screen."""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            
        consumed = False
        if self.overlay_screen:
            consumed = self.overlay_screen.handle_event(event)
        
        if not consumed and self.active_screen:
            consumed = self.active_screen.handle_event(event)
            
        return consumed

    def update(self, dt: float):
        if self.active_screen:
            self.active_screen.update(dt)
        if self.overlay_screen:
            self.overlay_screen.update(dt)
            
    def draw(self, surface: pygame.Surface):
        if self.active_screen:
            self.active_screen.draw(surface)
        if self.overlay_screen:
            self.overlay_screen.draw(surface)
