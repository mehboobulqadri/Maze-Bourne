"""
Maze Bourne - Main Game Engine
Handles game loop, state management, and core systems
"""

import pygame
import sys
import time
import math
from typing import Optional, Callable, Dict, Any
from enum import Enum

from src.core.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GAME_WIDTH, GAME_HEIGHT,
    SCREEN_WIDTH, SCREEN_HEIGHT, TARGET_FPS, WINDOW_TITLE,
    GameState, COLORS, DEBUG_MODE, SHOW_FPS
)
from src.core.editor import Editor
from src.core.logger import get_logger
from src.entities.boss import Boss, BossButton, create_boss, should_spawn_boss



class Game:
    """
    Main game class managing the game loop and core systems.
    Supports up to 144hz refresh with delta time handling.
    """
    
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        pygame.mixer.init()
        
        # Settings
        from src.core.settings_manager import SettingsManager
        self.settings_manager = SettingsManager()
        
        # Audio - apply settings
        from src.core.audio_manager import AudioManager
        self.audio_manager = AudioManager()
        self.audio_manager.set_master_volume(self.settings_manager.get("audio", "master_volume"))
        self.audio_manager.set_sfx_volume(self.settings_manager.get("audio", "sfx_volume"))
        
        # Procedural Music
        from src.core.music_generator import ProceduralMusicGenerator
        self.music_generator = ProceduralMusicGenerator()
        
        # Stats and Achievements
        from src.core.stats_tracker import StatsTracker
        from src.core.achievements import AchievementManager
        self.stats_tracker = StatsTracker()
        self.achievement_manager = AchievementManager()
        
        # Settings UI State
        self.settings_index = 0
        self.settings_options = [
            {"label": "Master Volume", "cat": "audio", "key": "master_volume", "type": "float", "min": 0.0, "max": 1.0, "step": 0.1},
            {"label": "SFX Volume", "cat": "audio", "key": "sfx_volume", "type": "float", "min": 0.0, "max": 1.0, "step": 0.1},
            {"label": "Difficulty", "cat": "gameplay", "key": "difficulty", "type": "list", "values": ["easy", "normal", "hard"]},
            {"label": "Enemy Speed", "cat": "gameplay", "key": "enemy_speed_multiplier", "type": "float", "min": 0.5, "max": 2.0, "step": 0.1},
            {"label": "AI Smartness", "cat": "gameplay", "key": "enemy_smartness", "type": "float", "min": 0.5, "max": 2.0, "step": 0.25},
        ]
        
        # Display setup
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.RESIZABLE
        )
        pygame.display.set_caption(WINDOW_TITLE)
        
        # Timing
        self.clock = pygame.time.Clock()
        self.target_fps = TARGET_FPS
        self.dt = 0.0  # Delta time in seconds
        self.fps = 0.0
        self.frame_count = 0
        self.fps_update_timer = 0.0
        
        # Game state
        self.state = GameState.MENU
        self.previous_state = GameState.MENU
        self.running = True
        
        # State handlers
        self.state_handlers: Dict[GameState, Dict[str, Callable]] = {}
        
        # Core systems (will be initialized later)
        self.renderer = None
        self.level = None
        self.player = None
        self.enemies = []
        self.game_object_manager = None
        
        # Input state
        self.keys_pressed = set()
        self.keys_just_pressed = set()
        self.keys_just_released = set()
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        
        # Campaign progress
        self.current_level_num = 1
        self.reset_level_requested = False
        self.game_mode = "campaign" # "campaign" or "endless"
        
        # Debug mode
        self.debug_mode = DEBUG_MODE
        self.show_fps = SHOW_FPS
        
        # Fonts (optimized for 720p)
        self.font_large = pygame.font.Font(None, 80)
        self.font_medium = pygame.font.Font(None, 52)
        self.font_small = pygame.font.Font(None, 36)
        self.font_tiny = pygame.font.Font(None, 28)
        

        
        # Entities
        self.enemies = []
        from src.entities.game_objects import GameObjectManager
        self.game_objects = GameObjectManager()
        
        # AI Director (Adaptive Difficulty)
        from src.core.director import AIDirector
        self.director = AIDirector()
        
        # Player Behavior Tracker (for endless mode adaptive AI)
        self.behavior_tracker = None  # Initialized in endless mode
        
        # LLM Strategist (for endless mode enemy coordination)
        self.strategist = None  # Initialized in endless mode
        
        # Audio
        from src.core.audio_manager import AudioManager
        self.audio_manager = AudioManager()
        self.audio_manager.set_master_volume(self.settings_manager.get("audio", "master_volume"))
        self.audio_manager.set_sfx_volume(self.settings_manager.get("audio", "sfx_volume"))
        
        # UI System
        from src.ui.ui_manager import UIManager
        from src.ui.screens import MainMenuScreen, HUDScreen, PauseScreen, GameOverScreen, SettingsScreen, CreditsScreen
        
        self.ui_manager = UIManager(self)
        self.ui_manager.register_screen("menu", MainMenuScreen(self.ui_manager))
        self.ui_manager.register_screen("hud", HUDScreen(self.ui_manager))
        self.ui_manager.register_screen("pause", PauseScreen(self.ui_manager))
        self.ui_manager.register_screen("game_over", GameOverScreen(self.ui_manager))
        self.ui_manager.register_screen("settings", SettingsScreen(self.ui_manager))
        self.ui_manager.register_screen("credits", CreditsScreen(self.ui_manager))
        self.ui_manager.switch_screen("menu")
        
        # Editor (needs fonts, ui, audio)
        self.editor = Editor(self)
        
        # RL / AI initialization (deferred to endless)
        self.previous_frame_time = time.time()
        self.dt = 0.0
        
        # Boss components
        self.current_boss = None
        self.boss_buttons = []

        # Start background music
        self.audio_manager.play_music("music_menu")
        
        # Register default state handlers
        self._setup_default_handlers()
        
        # Boss Battle System
        self.current_boss = None
        self.boss_buttons = []

        # Initialize initial state
        if self.state in self.state_handlers:
            handler = self.state_handlers[self.state]
            if "enter" in handler and handler["enter"]:
                handler["enter"]()

    def run(self):
        """Main game loop."""
        while self.running:
            # delta time
            self.dt = self.clock.tick(self.target_fps) / 1000.0
            
            # FPS tracking
            self.frame_count += 1
            self.fps_update_timer += self.dt
            if self.fps_update_timer >= 1.0:
                self.fps = self.frame_count / self.fps_update_timer
                self.frame_count = 0
                self.fps_update_timer = 0.0
                if self.show_fps:
                    pygame.display.set_caption(f"{WINDOW_TITLE} | FPS: {self.fps:.1f}")
            
            # Event handling
            self.keys_just_pressed.clear()
            self.keys_just_released.clear()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.keys_pressed.add(event.key)
                    self.keys_just_pressed.add(event.key)
                    
                    # Global debug toggle
                    if event.key == pygame.K_F1:
                        self.debug_mode = not self.debug_mode
                        
                elif event.type == pygame.KEYUP:
                    self.keys_pressed.discard(event.key)
                    self.keys_just_released.add(event.key)
                
                # Mouse Input
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    mx, my = event.pos
                    
                    # Clamp to game bounds
                    mx = max(0, min(GAME_WIDTH - 1, mx))
                    my = max(0, min(GAME_HEIGHT - 1, my))
                    
                    self.mouse_pos = (mx, my)
                    
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button <= 3: 
                            self.mouse_buttons[event.button - 1] = True
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if event.button <= 3:
                            self.mouse_buttons[event.button - 1] = False
            
                # Pass event to UI Manager
                self.ui_manager.handle_event(event)
            
            # Update
            if self.state in self.state_handlers:
                self.state_handlers[self.state]["update"](self.dt)
            
            # Render Phase
            # Clear screen
            self.screen.fill(COLORS.BACKGROUND)
            
            # Call State Render
            if self.state in self.state_handlers:
                handler = self.state_handlers[self.state]["render"]
                handler()

            # Flip
            pygame.display.flip()
            
        self._cleanup()
    
    def _setup_default_handlers(self):
        """Set up default state handlers."""
        # Menu state
        self.register_state_handler(GameState.MENU, 
            update=self._menu_update,
            render=self._menu_render,
            enter=self._menu_enter
        )
        
        # Playing state
        self.register_state_handler(GameState.PLAYING,
            update=self._playing_update,
            render=self._playing_render,
            enter=self._playing_enter
        )
        
        # Paused state
        self.register_state_handler(GameState.PAUSED,
            update=self._paused_update,
            render=self._paused_render,
            enter=self._paused_enter
        )
        
        # Game over state
        self.register_state_handler(GameState.GAME_OVER,
            update=self._game_over_update,
            render=self._game_over_render
        )
        
        # Victory state
        self.register_state_handler(GameState.VICTORY,
            update=self._victory_update,
            render=self._victory_render
        )

        # Help state
        self.register_state_handler(GameState.HELP,
            update=self._help_update,
            render=self._help_render,
            enter=self._help_enter
        )
        
        # Level Select state
        self.register_state_handler(GameState.LEVEL_SELECT,
            update=self._level_select_update,
            render=self._level_select_render,
            enter=self._level_select_enter
        )

        # Credits state
        self.register_state_handler(GameState.CREDITS,
            update=self._credits_update,
            render=self._credits_render,
            enter=self._credits_enter
        )

        # Editor state
        self.register_state_handler(GameState.EDITOR,
            update=self.editor.update,
            render=self.editor.render,
            enter=self.editor.enter
        )
        
        # Settings state
        self.register_state_handler(GameState.SETTINGS,
            update=self._settings_update,
            render=self._settings_render,
            enter=self._settings_enter
        )
        
        # Achievements state
        self.register_state_handler(GameState.ACHIEVEMENTS,
            update=self._achievements_update,
            render=self._achievements_render,
            enter=self._achievements_enter
        )
    
    def register_state_handler(self, state: GameState, 
                               update: Optional[Callable] = None,
                               render: Optional[Callable] = None,
                               enter: Optional[Callable] = None,
                               exit: Optional[Callable] = None):
        """Register handlers for a game state."""
        self.state_handlers[state] = {
            "update": update or (lambda dt: None),
            "render": render or (lambda: None),
            "enter": enter or (lambda: None),
            "exit": exit or (lambda: None),
        }
    
    def unpause(self):
        """Helper to resume game."""
        self.ui_manager.clear_overlay()
        self.change_state(GameState.PLAYING)
        
    def quit_to_menu(self):
        """Helper to return to menu."""
        self.ui_manager.clear_overlay()
        self.ui_manager.switch_screen("menu")
        self.change_state(GameState.MENU)

    def change_state(self, new_state: GameState):
        """Transition to a new game state."""
        if self.state == new_state:
            return
            
        # Exit current state
        if self.state in self.state_handlers:
            self.state_handlers[self.state]["exit"]()
            
        self.last_state = self.state
        self.state = new_state
        get_logger().info(f"State changed: {self.last_state.name} -> {self.state.name}")
        
        # UIManager Logic based on state
        if new_state == GameState.PAUSED:
            self.ui_manager.set_overlay("pause")
        elif new_state == GameState.PLAYING:
            self.ui_manager.switch_screen("hud")
            self.ui_manager.clear_overlay()
        elif new_state == GameState.GAME_OVER:
            # Collect stats
            stats = {"floor": self.current_level_num} # TODO: Add more stats from tracker
            self.ui_manager.switch_screen("game_over", victory=False, stats=stats)
        elif new_state == GameState.VICTORY:
            stats = {"floor": self.current_level_num, "score": 999}
            self.ui_manager.switch_screen("game_over", victory=True, stats=stats)
        elif new_state == GameState.MENU:
            self.ui_manager.switch_screen("menu")
        elif new_state == GameState.SETTINGS:
            self.ui_manager.switch_screen("settings")
        elif new_state == GameState.CREDITS:
            self.ui_manager.switch_screen("credits")
            
        # Enter new state
        if self.state in self.state_handlers:
            self.state_handlers[self.state]["enter"]()
    
    def _handle_events(self):
        """Process input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            # Global Key Handlers
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    # Toggle Debug
                    import src.core.constants as c
                    c.DEBUG_MODE = not c.DEBUG_MODE
                    
            # UI Manager Routing
            # If UI consumes event, don't pass to game logic
            if self.ui_manager.handle_event(event):
                continue
                
            # If not consumed, normal game input handling (state specific if needed)
            if self.state == GameState.PLAYING:
                 # Interaction handled in update via key polling usually, 
                 # but if we had click-to-move, it would be here.
                 pass
            
            elif event.type == pygame.KEYUP:
                self.keys_pressed.discard(event.key)
                self.keys_just_released.add(event.key)
            
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button <= 3:
                    self.mouse_buttons[event.button - 1] = True
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button <= 3:
                    self.mouse_buttons[event.button - 1] = False
    
    def is_key_pressed(self, key: int) -> bool:
        """Check if a key is currently held down."""
        return key in self.keys_pressed
    
    def is_key_just_pressed(self, key: int) -> bool:
        """Check if a key was just pressed this frame."""
        return key in self.keys_just_pressed
    
    def is_key_just_released(self, key: int) -> bool:
        """Check if a key was just released this frame."""
        return key in self.keys_just_released
    

    def _render_fps(self):
        """Render FPS counter."""
        fps_text = f"FPS: {self.fps:.1f}"
        fps_surface = self.font_tiny.render(fps_text, True, COLORS.UI_TEXT)
        self.screen.blit(fps_surface, (10, 10))
        
        if self.debug_mode:
            state_text = f"State: {self.state.name}"
            state_surface = self.font_tiny.render(state_text, True, COLORS.UI_TEXT_DIM)
            self.screen.blit(state_surface, (10, 35))
    
    # =========================================================================
    # Default State Handlers
    # =========================================================================
    
    def start_game(self, mode="campaign"):
        """Start a new game session."""
        self.game_mode = mode
        if mode == "campaign":
             # Should technically go to level select or level 1
             # For now, let's just start level 1
             self.current_level_num = 1
        elif mode == "endless":
             self.current_level_num = 1
             
        self.reset_level_requested = True
        self.change_state(GameState.PLAYING)

    def _menu_action(self, action):
        if action == "play":
            self.game_mode = "campaign"
            self.change_state(GameState.LEVEL_SELECT)
        elif action == "endless":
            self.game_mode = "endless"
            self.current_level_num = 1
            self.reset_level_requested = True
            self.change_state(GameState.PLAYING)
        elif action == "settings":
            self.change_state(GameState.SETTINGS)
        elif action == "editor":
            self.change_state(GameState.EDITOR)
        elif action == "help":
             self.change_state(GameState.HELP)
        elif action == "credits":
             self.change_state(GameState.CREDITS)
        elif action == "achievements":
             self.change_state(GameState.ACHIEVEMENTS)
        elif action == "quit":
            self.running = False

    def _menu_enter(self):
        """Setup main menu UI and fake background."""
        from src.levels.level import Level
        from src.graphics.renderer import Renderer
        
        if not self.renderer:
            self.renderer = Renderer(self)
            
        # Load a random level for background
        try:
            self.level = Level.from_campaign(1)
            self.renderer.setup_for_level(self.level)
            self.renderer.menu_mode = True  # Show full map in menu
            self.player = None 
        except Exception:
            self.level = None
            
        # UI is handled by UIManager
        self.ui_manager.switch_screen("menu")

    # ... _menu_update/render ...

    def _help_enter(self):
        # TODO: Implement HelpScreen in UIManager if needed
        pass

    def _help_render(self):
        # TODO: Implement HelpScreen in UIManager
        pass

    def _help_update(self, dt: float):
        pass
    def _menu_update(self, dt: float):
        """Update menu state."""
        self.ui_manager.update(dt)
    
    def _menu_render(self):
        """Render menu state."""
        self.ui_manager.draw(self.screen)
            
    def _settings_enter(self):
        """Setup settings UI."""
        # UIManager handles this now via change_state -> switch_screen
        pass

    def _settings_update(self, dt: float):
        self.ui_manager.update(dt)

    def _settings_render(self):
        self.ui_manager.draw(self.screen)
    
    # =========================================================================
    # Achievements State
    # =========================================================================
    
    def _achievements_enter(self):
        """Setup achievements screen UI."""
        cx = SCREEN_WIDTH // 2
        self.achievements_buttons = [
            Button(cx - 120, SCREEN_HEIGHT - 90, 240, 55, "BACK", self.font_medium, 
                   action=lambda: self.change_state(GameState.MENU))
        ]
        self.achievements_scroll = 0.0
    
    def _achievements_update(self, dt: float):
        """Update achievements screen."""
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        
        for btn in self.achievements_buttons:
            btn.update(mouse_pos, mouse_click, self.audio_manager)
        
        if self.is_key_just_pressed(pygame.K_ESCAPE):
            self.change_state(GameState.MENU)
    
    def _achievements_render(self):
        """Render achievements screen."""
        self.screen.fill(COLORS.BACKGROUND)
        
        # Title
        title = self.font_large.render("ACHIEVEMENTS", True, COLORS.PLAYER)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 60)))
        
        # Get achievements data
        if hasattr(self, 'achievement_manager'):
            achievements = self.achievement_manager.get_all_visible()
            progress = self.achievement_manager.get_progress()
        else:
            achievements = []
            progress = (0, 0)
        
        # Progress bar
        prog_text = self.font_small.render(f"Unlocked: {progress[0]} / {progress[1]}", 
                                           True, COLORS.UI_TEXT_DIM)
        self.screen.blit(prog_text, prog_text.get_rect(center=(SCREEN_WIDTH // 2, 100)))
        
        # Achievement grid (2 columns)
        start_y = 140
        col_width = SCREEN_WIDTH // 2 - 40
        row_height = 80
        
        for i, ach in enumerate(achievements[:8]):  # Show max 8
            col = i % 2
            row = i // 2
            
            x = 40 + col * (col_width + 20)
            y = start_y + row * row_height
            
            # Achievement box
            box_rect = pygame.Rect(x, y, col_width, row_height - 10)
            bg_color = (40, 50, 60) if ach.unlocked else (25, 30, 35)
            pygame.draw.rect(self.screen, bg_color, box_rect, border_radius=8)
            
            # Border with achievement color if unlocked
            border_color = ach.icon_color if ach.unlocked else COLORS.UI_BORDER
            pygame.draw.rect(self.screen, border_color, box_rect, 2, border_radius=8)
            
            # Icon circle
            icon_x = x + 35
            icon_y = y + 35
            if ach.unlocked:
                pygame.draw.circle(self.screen, ach.icon_color, (icon_x, icon_y), 20)
                # Checkmark
                pygame.draw.line(self.screen, (30, 30, 30), (icon_x - 8, icon_y), (icon_x - 2, icon_y + 8), 3)
                pygame.draw.line(self.screen, (30, 30, 30), (icon_x - 2, icon_y + 8), (icon_x + 10, icon_y - 6), 3)
            else:
                pygame.draw.circle(self.screen, COLORS.UI_TEXT_DIM, (icon_x, icon_y), 20, 2)
                pygame.draw.line(self.screen, COLORS.UI_TEXT_DIM, (icon_x - 8, icon_y), (icon_x + 8, icon_y), 2)
            
            # Title
            title_color = COLORS.UI_TEXT if ach.unlocked else COLORS.UI_TEXT_DIM
            name_surf = self.font_small.render(ach.name, True, title_color)
            self.screen.blit(name_surf, (x + 65, y + 12))
            
            # Description
            desc_color = COLORS.UI_TEXT_DIM if ach.unlocked else (80, 80, 80)
            desc_surf = self.font_tiny.render(ach.description, True, desc_color)
            self.screen.blit(desc_surf, (x + 65, y + 38))
        
        # Back button
        for btn in self.achievements_buttons:
            btn.draw(self.screen)
    
    # =========================================================================
    # Level Select State
    # =========================================================================
    
    def _level_select_enter(self):
        # TODO: Implement LevelSelectScreen
        pass

    def _level_select_update(self, dt: float):
        pass

    def _level_select_render(self):
        pass

    def _achievements_enter(self):
        # TODO: Implement AchievementsScreen
        pass

    def _achievements_update(self, dt: float):
        pass

    def _achievements_render(self):
        pass
    
    def _start_level(self, level_num):
        """Start a specific level."""
        self.current_level_num = level_num
        self.reset_level_requested = True
        self.change_state(GameState.PLAYING)
    
    def _game_over_update(self, dt: float):
        self.ui_manager.update(dt)
        
    def _game_over_render(self):
        if self.renderer:
            self.renderer.render(self.screen)
        self.ui_manager.draw(self.screen)
            
    def _level_select_update(self, dt: float):
        """Handle level selection input."""
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        
        for btn in self.level_select_buttons:
            btn.update(mouse_pos, mouse_click, self.audio_manager)
        
        self.level_select_back_btn.update(mouse_pos, mouse_click, self.audio_manager)
        
        if self.is_key_just_pressed(pygame.K_ESCAPE):
            self.change_state(GameState.MENU)
    
    def _level_select_render(self):
        """Render level selection grid."""
        self.screen.fill(COLORS.BACKGROUND)
        
        # Title
        title = self.font_large.render("SELECT LEVEL", True, COLORS.PLAYER)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))
        
        # Draw level buttons with stars
        for btn in self.level_select_buttons:
            btn.draw(self.screen)
            
            # Draw stars below button text
            stars = getattr(btn, 'stars', 0)
            star_y = btn.rect.bottom - 25
            star_spacing = 25
            star_start_x = btn.rect.centerx - star_spacing
            
            for i in range(3):
                star_x = star_start_x + i * star_spacing
                self._draw_level_star(self.screen, star_x, star_y, 10, filled=(i < stars))
        
        # Draw back button
        self.level_select_back_btn.draw(self.screen)
        
        # Difficulty reminder
        diff = "Normal"
        if hasattr(self, 'settings_manager'):
            diff = self.settings_manager.get("gameplay", "difficulty") or "normal"
            diff = diff.capitalize()
        
        diff_lives = {"Easy": 3, "Normal": 2, "Hard": 1}
        lives = diff_lives.get(diff, 2)
        
        hint = self.font_tiny.render(f"Difficulty: {diff} ({lives} {'lives' if lives > 1 else 'life'})", 
                                     True, COLORS.UI_TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 140)))
    
    def _draw_level_star(self, surface, x, y, size, filled=True):
        """Draw a small star for level select."""
        import math
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
    
    def _playing_enter(self):
        """Called when entering the playing state - initialize game objects."""
        # Only re-initialize if level is missing or reset requested
        if self.level is not None and not self.reset_level_requested:
            # Just changing state (e.g. from Pause), verify renderer setup
            if self.renderer and self.level:
                # Ensure renderer is linked to current level (in case of weird state)
                pass 
            return

        self.reset_level_requested = False

        # Import game components
        from src.levels.level import Level
        from src.entities.player import Player
        from src.graphics.renderer import Renderer
        from src.entities.enemy import Enemy
        from src.entities.game_objects import (
            GameObjectManager, SecurityCamera, Trap, HidingSpot
        )
        
        if self.game_mode == "endless":
            get_logger().info(f"Loading Endless Floor {self.current_level_num}...")
            self.level = Level.from_endless(self.current_level_num)
            
            # Initialize behavior tracker
            from src.ai.player_tracker import PlayerBehaviorTracker
            if self.behavior_tracker is None:
                self.behavior_tracker = PlayerBehaviorTracker()
            else:
                self.behavior_tracker.reset_for_new_floor()
            
            # Initialize LLM strategist
            from src.ai.strategist import EnemyStrategist
            if not hasattr(self, 'strategist') or self.strategist is None:
                self.strategist = EnemyStrategist(self.settings_manager)
            
            # Boss Battle Check
            self.current_boss = None
            self.boss_buttons = []
            if self.current_level_num > 0 and self.current_level_num % 10 == 0:
                get_logger().info(f"BOSS BATTLE - Floor {self.current_level_num}")
                from src.entities.boss import create_boss, BossButton
                
                # Create boss at center
                center_x = self.level.width / 2.0
                center_y = self.level.height / 2.0
                self.current_boss = create_boss(self.current_level_num, (center_x, center_y))
                
                # Create buttons
                if hasattr(self.level, 'boss_button_positions'):
                    for i, (bx, by) in enumerate(self.level.boss_button_positions):
                        btn = BossButton(bx, by, f"btn_{i}")
                        self.boss_buttons.append(btn)
                        self.game_object_manager.add(btn)
        else:
            # Create campaign level
            get_logger().info(f"Loading Campaign Level {self.current_level_num}...")
            self.level = Level.from_campaign(self.current_level_num)
            self.current_boss = None
            self.boss_buttons = []
        
        # Create player at spawn point
        spawn_x, spawn_y = self.level.spawn_point
        difficulty = self.settings_manager.get("gameplay", "difficulty")
        
        # Difficulty determines max health: easy=3, medium=2, hard=1
        health_by_difficulty = {"easy": 3, "normal": 2, "hard": 1}
        max_health = health_by_difficulty.get(difficulty, 2)
        
        self.player = Player(spawn_x, spawn_y, max_health=max_health)
        
        # Initialize renderer if needed
        if not self.renderer:
            self.renderer = Renderer(self)
        self.renderer.setup_for_level(self.level)
        self.renderer.menu_mode = False  # Disable menu mode for gameplay FOV
        self.renderer.add_notification(f"Level {self.current_level_num}", duration=3.0)
        
        # Get AI Modifiers for this level
        enemy_modifiers = self.director.get_enemy_config_modifiers()
        enemy_modifiers["modifiers"] = self.director.active_modifiers
        
        # Spawn enemies from level config
        self.enemies = []
        for config in self.level.get_enemy_configs():
            enemy = Enemy(config["x"], config["y"], config["type"], config_overrides=enemy_modifiers)
            self.enemies.append(enemy)
        
        # Initialize game objects manager and spawn objects
        self.game_object_manager = GameObjectManager()
        
        # Spawn cameras with smart rotation
        for i, pos in enumerate(self.level.camera_positions):
            # Check valid directions
            valid_stats = []
            
            # Check 4 cardinals
            cx, cy = int(pos[0]), int(pos[1])
            candidates = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            valid_dirs = []
            
            for dx, dy in candidates:
                if self.level.is_walkable(cx + dx, cy + dy):
                    valid_dirs.append((dx, dy))
            
            # Fallback if trapped (e.g. inside walls?)
            if not valid_dirs:
                valid_dirs = [(1, 0)]
                
            rotation_pat = valid_dirs
            # If we have multiple directions, use them for rotation
            # If only 1, the list will have 1 item and rotation effectively pauses on it (or loops)
            
            camera = SecurityCamera(
                x=pos[0], y=pos[1],
                camera_id=f"cam_{i}",
                vision_range=6.0,
                vision_angle=90.0,
                facing_direction=rotation_pat[0],
                rotation_pattern=rotation_pat,
                rotation_wait=2.0
            )
            self.game_object_manager.add(camera)
        
        # Spawn traps
        for i, pos in enumerate(self.level.trap_positions):
            trap = Trap(
                x=pos[0], y=pos[1],
                trap_id=f"trap_{i}",
                damage=1,
                is_hidden=False
            )
            self.game_object_manager.add(trap)
        
        # Spawn hiding spots
        for i, pos in enumerate(self.level.hiding_spot_positions):
            hiding_spot = HidingSpot(
                x=pos[0], y=pos[1],
                spot_id=f"hide_{i}",
                capacity=1
            )
            self.game_object_manager.add(hiding_spot)
        
        # Spawn levers
        from src.entities.game_objects import Lever
        for i, pos in enumerate(getattr(self.level, 'lever_positions', [])):
            lever = Lever(
                x=pos[0], y=pos[1],
                is_on=False,
                linked_objects=[]
            )
            self.game_object_manager.add(lever)
        
        get_logger().info(f"Level initialized: {self.level.width}x{self.level.height}")
        get_logger().info(f"Player spawned at: ({spawn_x}, {spawn_y})")
        get_logger().info(f"Spawned {len(self.enemies)} enemies")
        get_logger().info(f"Spawned {len(self.game_object_manager.objects)} game objects")
        
        # Start level timer
        self.stats_tracker.start_level(self.current_level_num)
        
        # Start ambient music
        if hasattr(self, 'music_generator') and not self.music_generator.is_playing:
            music_volume = self.settings_manager.get("audio", "music_volume") or 0.3
            self.music_generator.play(volume=music_volume)
    
    def _advance_to_next_level(self):
        """Advance to the next level after boss defeat or exit reached."""
        self.current_level_num += 1
        self.reset_level_requested = True
        self.level = None
        self.current_boss = None
        self.boss_buttons = []
        
        get_logger().info(f"Advancing to level {self.current_level_num}")
        
        self._playing_enter()
    
    def _playing_update(self, dt: float):
        """Update playing state."""
        # Pause
        if self.is_key_just_pressed(pygame.K_ESCAPE):
            self.change_state(GameState.PAUSED)
        
        # Interact key
        for key in [pygame.K_e]:
            if self.is_key_just_pressed(key):
                if self.player:
                    self.player.interact(self)
        
        # Update stats tracker
        if self.player:
            is_moving = getattr(self.player, '_move_input', (0,0)) != (0,0) and not getattr(self.player, 'is_hidden', False)
            
            # Record distance if moving
            if is_moving:
                # Approximate distance for this frame
                speed = self.player.speed
                if self.player.is_stealthed:
                    speed *= 0.6  # approx stealth mult
                self.stats_tracker.record_movement(speed * dt)
                
            self.stats_tracker.update(dt, 
                                      is_stealthed=getattr(self.player, 'is_stealthed', False),
                                      is_hiding=getattr(self.player, 'is_hidden', False),
                                      is_moving=is_moving)
            
            # Update behavior tracker for endless mode
            if self.game_mode == "endless" and self.behavior_tracker:
                self.behavior_tracker.record_position(
                    self.player.x, self.player.y,
                    is_stealthed=getattr(self.player, 'is_stealthed', False),
                    dt=dt
                )
        
        # Update game systems
        if self.player:
            self.player.update(dt, self)
        
        for enemy in self.enemies:
            enemy.update(dt, self)
        
        # LLM Strategist for Endless Mode (periodic strategy requests)
        if self.game_mode == "endless" and hasattr(self, 'strategist') and self.strategist:
            # Check if any enemies are searching
            from src.core.constants import EnemyState
            searching_enemies = [e for e in self.enemies if e.state == EnemyState.SEARCH]
            
            if searching_enemies:
                # Request strategy periodically
                if not hasattr(self, '_strategist_request_id'):
                    self._strategist_request_id = self.strategist.request_strategy(self, self.enemies)
                elif self._strategist_request_id:
                    # Check for response
                    response = self.strategist.get_response(self._strategist_request_id)
                    if response:
                        # Apply strategy to searching enemies
                        get_logger().debug(f"Strategist response: {response.reasoning}")
                        self._strategist_request_id = None
            else:
                # Reset when no enemies searching
                self._strategist_request_id = None
        
        # Update Boss
        if self.current_boss:
            self.current_boss.update(dt, self)
            
            # Check for defeat
            if self.current_boss.is_defeated:
                # Delay before transitioning to next level
                if not hasattr(self, '_boss_defeat_timer'):
                    self._boss_defeat_timer = 3.0
                    get_logger().info("Boss defeated! Transitioning to next level...")
                else:
                    self._boss_defeat_timer -= dt
                    if self._boss_defeat_timer <= 0:
                        delattr(self, '_boss_defeat_timer')
                        self._advance_to_next_level()
        
        # Update Boss Buttons
        for btn in self.boss_buttons:
            btn.update(dt)
            # Simple collision interaction (if player walks on it? No, use 'E' interact)
            # We'll rely on player.interact() calling btn.on_interact()
            # BUT player.interact only checks cells.
            # Buttons are logically on cells.
            # We need to bridge Player.interact -> BossButton
        
        # Update game objects
        
        # Update game objects
        if self.game_object_manager:
            self.game_object_manager.update(dt, self)
            self.game_object_manager.check_player_collision(self.player, self)
        
        if self.renderer:
            self.renderer.update(dt)
    
    def _playing_render(self):
        """Render playing state."""
        if self.renderer:
            # Main render (World)
            self.renderer.render(self.screen)
            
            # Boss specific rendering (World Space)
            if self.current_boss and self.current_boss.is_alive:
                self.renderer.render_boss(self.current_boss, self.renderer.camera)
            
            # Boss Buttons (World Space)
            for btn in self.boss_buttons:
                self.renderer.render_boss_button(btn, self.renderer.camera)
                
            # UI Overlay (HUD, Boss Bar, etc)
            self.ui_manager.draw(self.screen)
            
        else:
            # Placeholder when renderer not initialized
            text = self.font_medium.render("Game View - Renderer Loading...", True, COLORS.UI_TEXT)
            rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(text, rect)
    
    def _help_render(self):
        self.screen.fill(COLORS.BACKGROUND)
        
        # Title
        title = self.font_large.render("HOW TO PLAY", True, COLORS.PLAYER)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 50)))
        
        # Grid layout for help items
        start_y = 120
        item_height = 80
        
        # 1. Objective
        pygame.draw.circle(self.screen, COLORS.KEY, (100, start_y + 20), 15) # Key Icon
        pygame.draw.rect(self.screen, COLORS.EXIT, (180, start_y, 40, 40), 2) # Exit Icon
        # Arrow
        pygame.draw.line(self.screen, COLORS.UI_TEXT, (130, start_y + 20), (170, start_y + 20), 2)
        
        obj_text = self.font_medium.render("OBJECTIVE", True, COLORS.UI_ENERGY)
        self.screen.blit(obj_text, (250, start_y))
        obj_desc = self.font_small.render("Collect the Golden Key -> Escape via Green Portal", True, COLORS.UI_TEXT)
        self.screen.blit(obj_desc, (250, start_y + 30))
        
        # 2. Controls
        start_y += item_height
        # WASD Keys visualization
        self._draw_key_icon(80, start_y, "W")
        self._draw_key_icon(50, start_y + 35, "A")
        self._draw_key_icon(80, start_y + 35, "S")
        self._draw_key_icon(110, start_y + 35, "D")
        
        ctrl_text = self.font_medium.render("CONTROLS", True, COLORS.UI_ENERGY)
        self.screen.blit(ctrl_text, (250, start_y + 10))
        ctrl_desc = self.font_small.render("Move. SHIFT: Sneak (Silent, uses Energy). SPACE: Dash (Burst, uses Energy).", True, COLORS.UI_TEXT)
        self.screen.blit(ctrl_desc, (250, start_y + 40))
        
        # 3. Enemies
        start_y += item_height + 20
        # Draw actual enemy shapes
        # Patrol (Red)
        pygame.draw.rect(self.screen, COLORS.ENEMY_PATROL, (60, start_y, 30, 30))
        pygame.draw.line(self.screen, (255, 0, 0), (75, start_y+15), (75+30, start_y+15), 2) # Vision ray
        
        # Guard (Purple/Orange check)
        # Replacing circle with Purple Guard
        pygame.draw.circle(self.screen, COLORS.ENEMY_GUARD, (130, start_y + 15), 15)
        
        # Hunter (Yellow)
        pts = [(180, start_y + 30), (195, start_y), (210, start_y + 30)]
        pygame.draw.polygon(self.screen, COLORS.ENEMY_HUNTER, pts)
        
        en_text = self.font_medium.render("AVOID ENEMIES", True, COLORS.UI_ENERGY)
        self.screen.blit(en_text, (250, start_y))
        en_desc = self.font_small.render("Red: Patrol | Orange: Tracker | Yellow: Hunter | Purple: Guard", True, COLORS.UI_TEXT)
        self.screen.blit(en_desc, (250, start_y + 30))
        
        # 4. Hiding
        start_y += item_height
        pygame.draw.rect(self.screen, COLORS.HIDING_SPOT, (80, start_y, 40, 40))
        pygame.draw.rect(self.screen, (100, 100, 255), (80, start_y, 40, 40), 2) # Glow
        
        hide_text = self.font_medium.render("STAY HIDDEN", True, COLORS.UI_ENERGY)
        self.screen.blit(hide_text, (250, start_y + 5))
        hide_desc = self.font_small.render("Hide in Blue Zones to evade chase. Sneaking consumes Energy.", True, COLORS.UI_TEXT)
        self.screen.blit(hide_desc, (250, start_y + 35))
        
        # 5. Editor Mode
        start_y += item_height
        
        edit_text = self.font_medium.render("LEVEL EDITOR", True, COLORS.UI_ENERGY)
        self.screen.blit(edit_text, (100, start_y + 5))
        edit_desc = self.font_small.render("Drag to Paint. Right Click to Erase. Save & Play your own levels!", True, COLORS.UI_TEXT)
        self.screen.blit(edit_desc, (100, start_y + 35))
        
        for btn in self.help_buttons:
            btn.draw(self.screen)

    def _draw_key_icon(self, x, y, char):
        pygame.draw.rect(self.screen, (50, 50, 60), (x, y, 28, 28), border_radius=4)
        pygame.draw.rect(self.screen, (150, 150, 160), (x, y, 28, 28), 1, border_radius=4)
        txt = self.font_tiny.render(char, True, COLORS.UI_TEXT)
        self.screen.blit(txt, (x + 8, y + 6))
        
    def _credits_enter(self):
        # UI is handled by UIManager
        self.ui_manager.switch_screen("credits")

    def _credits_update(self, dt: float):
        self.ui_manager.update(dt)

    def _credits_render(self):
        self.ui_manager.draw(self.screen)
            
    def _paused_enter(self):
        # UI is handled by UIManager
        self.ui_manager.switch_screen("pause")
        
    def _restart_level(self):
        self.reset_level_requested = True
        self.change_state(GameState.PLAYING)

    def _paused_update(self, dt: float):
        self.ui_manager.update(dt)
        
    def _paused_render(self):
        self.renderer.render(self.screen) # Draw underlying game
        self.ui_manager.draw(self.screen) # Draw Pause Overlay (handled by set_overlay ideally, or just switch_screen logic)
        
        # NOTE: If using switch_screen("pause"), the game won't render behind it unless PauseScreen handles it?
        # My UIManager has 'active_screen' and 'overlay_screen'.
        # Best approach: GameState.PAUSED sets overlay 'pause'.
        pass
    
    def _game_over_update(self, dt: float):
        """Update game over state."""
        if self.is_key_just_pressed(pygame.K_RETURN):
            # Retry level
            self.reset_level_requested = True
            self.change_state(GameState.PLAYING)
    
    def _game_over_render(self):
        """Render game over state."""
        text = self.font_large.render("GAME OVER", True, COLORS.UI_HEALTH)
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(text, rect)
        
        restart = self.font_small.render("Press ENTER to Retry", True, COLORS.UI_TEXT_DIM)
        restart_rect = restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(restart, restart_rect)
    
    def _victory_update(self, dt: float):
        self.ui_manager.update(dt)

    def _victory_render(self):
        self.ui_manager.draw(self.screen)
    
    def _draw_star(self, surface, x, y, size, filled=True):
        """Draw a star shape."""
        import math
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
    
    def _format_time(self, seconds):
        """Format seconds as MM:SS.mmm"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:06.3f}"
    
    def _cleanup(self):
        """Clean up resources."""
        pygame.mixer.quit()
        pygame.quit()
        sys.exit()


def main():
    """Entry point for the game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()