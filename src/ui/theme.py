import pygame
from src.core.constants import COLORS

class UITheme:
    """Defines the visual style for the Maze Bourne UI."""
    
    # Fonts
    FONT_MAIN = "Consolas" # Fallback, likely overridden by load
    FONT_HEADER_SIZE = 64
    FONT_TITLE_SIZE = 48
    FONT_NORMAL_SIZE = 24
    FONT_SMALL_SIZE = 16
    
    # Colors (Cyberpunk/Stealth Palette)
    COLOR_BG_OVERLAY = (10, 15, 20, 220) # Dark transparent background
    
    COLOR_TEXT_PRIMARY = (220, 230, 240)
    COLOR_TEXT_SECONDARY = (140, 160, 180)
    COLOR_TEXT_ACCENT = (0, 255, 215)  # Cyan Neon
    COLOR_TEXT_DANGER = (255, 60, 80)  # Red Neon
    
    COLOR_BUTTON_NORMAL = (30, 40, 50)
    COLOR_BUTTON_HOVER = (50, 70, 90)
    COLOR_BUTTON_PRESSED = (70, 90, 110)
    COLOR_BUTTON_BORDER = (0, 150, 130) # Cyan border
    
    COLOR_PANEL_BG = (15, 20, 25, 240)
    COLOR_PANEL_BORDER = (40, 50, 60)
    
    # HUD Specific
    COLOR_HEALTH_BAR = (220, 40, 60)
    COLOR_STAMINA_BAR = (60, 180, 220)
    COLOR_BOSS_BAR = (180, 30, 50)
    COLOR_STEALTH_BAR = (100, 220, 160)
    
    # Layout
    BUTTON_HEIGHT = 50
    BUTTON_WIDTH = 220
    BUTTON_PADDING = 15
    PANEL_PADDING = 20
    
    # Animation
    ANIM_HOVER_SPEED = 10.0
    ANIM_PULSE_SPEED = 2.0

    @staticmethod
    def load_fonts():
        """Initialize fonts (call during startup)."""
        # For now using system fonts or default file
        # In a real polished app we'd load .ttf files
        pygame.font.init()
        return {
            'header': pygame.font.SysFont(UITheme.FONT_MAIN, UITheme.FONT_HEADER_SIZE, bold=True),
            'title': pygame.font.SysFont(UITheme.FONT_MAIN, UITheme.FONT_TITLE_SIZE, bold=True),
            'normal': pygame.font.SysFont(UITheme.FONT_MAIN, UITheme.FONT_NORMAL_SIZE),
            'small': pygame.font.SysFont(UITheme.FONT_MAIN, UITheme.FONT_SMALL_SIZE),
            'mono': pygame.font.Font(None, UITheme.FONT_NORMAL_SIZE) # Default pygame font is usually monospace-like
        }
