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
from src.ui.ui_components import Button, Slider


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
        
        # Editor (needs fonts)
        self.editor = Editor(self)
        
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
        
        # Register default state handlers
        self._setup_default_handlers()
        
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
    
    def change_state(self, new_state: GameState):
        """Change the current game state."""
        if new_state == self.state:
            return
            
        # Exit current state
        if self.state in self.state_handlers:
            self.state_handlers[self.state]["exit"]()
        
        self.previous_state = self.state
        self.state = new_state
        
        # Enter new state
        if self.state in self.state_handlers:
            self.state_handlers[self.state]["enter"]()
    
    def _process_events(self):
        """Process pygame events."""
        # Clear just pressed/released keys
        self.keys_just_pressed.clear()
        self.keys_just_released.clear()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                self.keys_pressed.add(event.key)
                self.keys_just_pressed.add(event.key)
                
                # Global keys
                if event.key == pygame.K_F3:
                    self.debug_mode = not self.debug_mode
                if event.key == pygame.K_F4:
                    self.show_fps = not self.show_fps
            
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
            
        # UI Setup
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        btn_w, btn_h = 300, 50
        gap = 50
        
        self.menu_buttons = [
            Button(cx - btn_w//2, cy - 20, btn_w, btn_h, "PLAY CAMPAIGN", self.font_medium, 
                   action=lambda: self._menu_action("play")),
            Button(cx - btn_w//2, cy - 20 + gap, btn_w, btn_h, "ENDLESS RUN", self.font_medium, 
                   action=lambda: self._menu_action("endless")),
            Button(cx - btn_w//2, cy - 20 + gap*2, btn_w, btn_h, "SETTINGS", self.font_medium, 
                   action=lambda: self._menu_action("settings")),
            Button(cx - btn_w//2, cy - 20 + gap*2, btn_w, btn_h, "ACHIEVEMENTS", self.font_medium, 
                   action=lambda: self._menu_action("achievements")),
            Button(cx - btn_w//2, cy - 20 + gap*3, btn_w, btn_h, "EDITOR", self.font_medium, 
                   action=lambda: self._menu_action("editor")),
            Button(cx - btn_w//2, cy - 20 + gap*4, btn_w, btn_h, "HELP", self.font_medium, 
                   action=lambda: self._menu_action("help")),
            Button(cx - btn_w//2, cy - 20 + gap*5, btn_w, btn_h, "CREDITS", self.font_medium, 
                   action=lambda: self._menu_action("credits")),
            Button(cx - btn_w//2, cy - 20 + gap*6, btn_w, btn_h, "QUIT", self.font_medium, 
                   action=lambda: self._menu_action("quit")),
        ]

    # ... _menu_update/render ...

    def _help_enter(self):
        cx = SCREEN_WIDTH // 2
        self.help_buttons = [
             Button(cx - 120, SCREEN_HEIGHT - 90, 240, 55, "BACK", self.font_medium, 
                   action=lambda: self.change_state(GameState.MENU))
        ]
        self.help_scroll_y = 0
        self.max_scroll = 0 # Will be calculated in render

    def _help_update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        
        # Handle Scrolling
        for event in pygame.event.get(pygame.MOUSEWHEEL):
             self.help_scroll_y += event.y * 30
             
        # Clamp Scroll
        screen_h = SCREEN_HEIGHT - 150 # Visible area approx
        min_scroll = -(self.max_scroll - screen_h) if self.max_scroll > screen_h else 0
        self.help_scroll_y = max(min_scroll, min(0, self.help_scroll_y))
        
        for btn in self.help_buttons:
             btn.update(mouse_pos, mouse_click, self.audio_manager)
        
        if self.is_key_just_pressed(pygame.K_ESCAPE):
             self.change_state(GameState.MENU)

    def _help_render(self):
        """Render help screen with enemy info."""
        self.screen.fill(COLORS.BACKGROUND)
        
        # Draw Title (Fixed)
        title = self.font_large.render("HELP & GUIDE", True, COLORS.UI_TEXT)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 50)))
        
        # Scrollable Area Config
        start_y = 120 + self.help_scroll_y
        current_y = start_y
        left_margin = SCREEN_WIDTH // 2 - 300
        
        # --- CONTROLS SECTION ---
        header = self.font_medium.render("CONTROLS", True, COLORS.KEY)
        self.screen.blit(header, (left_margin, current_y))
        current_y += 50
        
        controls = [
            ("WASD / Arrows", "Move Player"),
            ("SHIFT", "Hold to Walk (Silent)"),
            ("SPACE", "Dash (Uses Energy)"),
            ("E", "Interact (Doors, Hiding Spots)"),
            ("ESC", "Pause / Back")
        ]
        
        for key, desc in controls:
            k_surf = self.font_small.render(key, True, COLORS.UI_TEXT_DIM)
            d_surf = self.font_small.render(desc, True, COLORS.UI_TEXT)
            self.screen.blit(k_surf, (left_margin, current_y))
            self.screen.blit(d_surf, (left_margin + 250, current_y))
            current_y += 35
            
        current_y += 40
        
        # --- ENEMIES SECTION ---
        header = self.font_medium.render("ENEMIES", True, COLORS.ENEMY_PATROL)
        self.screen.blit(header, (left_margin, current_y))
        current_y += 50
        
        # Import config if needed or use constants
        from src.core.constants import ENEMY_CONFIG, EnemyType
        
        enemy_data = [
            (EnemyType.PATROL, "Patrol Guard", "Standard guard. Follows a fixed path.", "Normal"),
            (EnemyType.TRACKER, "Tracker", "Fast runner. 360  Vision but short range. Follows trails.", "Fast"),
            (EnemyType.SOUND_HUNTER, "Sound Hunter", "Blind. Relies on hearing. Don't run near him!", "Fast"),
            (EnemyType.SIGHT_GUARD, "Sniper", "Slow. Sees very far. Avoid long corridors.", "Slow"),
        ]
        
        for e_type, name, desc, speed_desc in enemy_data:
            config = ENEMY_CONFIG[e_type]
            color = config["color"]
            
            # Draw Sprite Icon
            pygame.draw.circle(self.screen, color, (left_margin + 20, int(current_y + 15)), 15)
            # Eyes/Details
            pygame.draw.circle(self.screen, (255,255,255), (left_margin + 20, int(current_y + 15)), 6)
            
            # Name & Speed
            name_surf = self.font_medium.render(f"{name} ({speed_desc})", True, color)
            self.screen.blit(name_surf, (left_margin + 60, current_y))
            
            # Description
            desc_surf = self.font_tiny.render(desc, True, COLORS.UI_TEXT_DIM)
            self.screen.blit(desc_surf, (left_margin + 60, current_y + 35))
            
            current_y += 80
            
        # Draw Buttons (Fixed on top or bottom?)
        # Drawing them last ensures they are on top of scrolled content
        # Clear bottom area for back button
        bottom_bar = pygame.Surface((SCREEN_WIDTH, 100))
        bottom_bar.fill(COLORS.BACKGROUND)
        self.screen.blit(bottom_bar, (0, SCREEN_HEIGHT - 100))
        
        for btn in self.help_buttons:
            btn.draw(self.screen)
            
        # Calculate max scroll for next frame clamping
        # Total content height = current_y - start_y
        total_h = current_y - self.help_scroll_y
        self.max_scroll = total_h
    def _menu_update(self, dt: float):
        """Update menu state."""
        # Pan Camera
        if self.renderer and self.renderer.camera:
            self.renderer.camera.x += 20 * dt
            self.renderer.update(dt) # Update particles/effects
            
        # Get mouse position in window coordinates and convert to game surface coordinates
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        
        for btn in self.menu_buttons:
            if btn.update(mouse_pos, mouse_click, self.audio_manager):
                # Action triggered
                pass
    
    def _menu_render(self):
        """Render menu state."""
        # Draw background level
        self.screen.fill(COLORS.BACKGROUND)
        if self.renderer and self.level:
            self.renderer.render(self.screen)
        
        # Dark Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # Title
        title = self.font_large.render("MAZE BOURNE", True, COLORS.PLAYER)
        # Pulse title
        scale = 1.0 + math.sin(time.time() * 2) * 0.05
        w, h = title.get_size()
        scaled_title = pygame.transform.smoothscale(title, (int(w*scale), int(h*scale)))
        title_rect = scaled_title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(scaled_title, title_rect)
        
        # Buttons
        for btn in self.menu_buttons:
            btn.draw(self.screen)
            
    def _settings_enter(self):
        """Setup settings UI."""
        # Imports handled globally
        
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        
        self.settings_ui_elements = []
        
        # Sliders
        # Master Volume
        val = self.settings_manager.get("audio", "master_volume") or 0.7
        self.slider_master = Slider(cx - 150, 200, 300, 20, 0.0, 1.0, val, "Master Volume", self.font_small)
        self.settings_ui_elements.append(self.slider_master)
        
        # SFX Volume
        val = self.settings_manager.get("audio", "sfx_volume") or 0.8
        self.slider_sfx = Slider(cx - 150, 280, 300, 20, 0.0, 1.0, val, "SFX Volume", self.font_small)
        self.settings_ui_elements.append(self.slider_sfx)

        # Buttons for Difficulty
        self.settings_ui_elements.append(Button(cx - 150, 350, 300, 40, "Difficulty: " + str(self.settings_manager.get("gameplay", "difficulty")).upper(), self.font_small, 
                   action=lambda: self._toggle_difficulty()))
                   
        # Back Button
        self.settings_ui_elements.append(Button(cx - 120, 560, 240, 55, "BACK", self.font_medium, 
                   action=lambda: self.change_state(GameState.MENU)))

    def _toggle_difficulty(self):
        diffs = ["easy", "normal", "hard"]
        curr = self.settings_manager.get("gameplay", "difficulty")
        try:
            next_idx = (diffs.index(curr) + 1) % len(diffs)
        except:
            next_idx = 0
        new_diff = diffs[next_idx]
        self.settings_manager.set("gameplay", "difficulty", new_diff)
        
        # Update button text
        for el in self.settings_ui_elements:
            if isinstance(el, Button) and "Difficulty" in el.text:
                # Need to re-render text
                el.text = "Difficulty: " + new_diff.upper()
                el.text_surf = el.font.render(el.text, True, el.text_color)
                el.text_rect = el.text_surf.get_rect(center=el.rect.center)
                break

    def _settings_update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        mouse_down = pygame.mouse.get_pressed()[0]
        
        # Handle sliders
        new_master = self.slider_master.update(mouse_pos, mouse_down)
        if new_master != self.settings_manager.get("audio", "master_volume"):
            self.settings_manager.set("audio", "master_volume", new_master)
            self.audio_manager.set_master_volume(new_master)
            
        new_sfx = self.slider_sfx.update(mouse_pos, mouse_down)
        if new_sfx != self.settings_manager.get("audio", "sfx_volume"):
            self.settings_manager.set("audio", "sfx_volume", new_sfx)
            self.audio_manager.set_sfx_volume(new_sfx)
            
        # Handle buttons
        for el in self.settings_ui_elements:
            if hasattr(el, 'update') and not isinstance(el, Slider): # Sliders handled above
                 el.update(mouse_pos, mouse_click, self.audio_manager)

        if self.is_key_just_pressed(pygame.K_ESCAPE):
            self.change_state(GameState.MENU)

    def _settings_render(self):
        self.screen.fill(COLORS.BACKGROUND)
        
        title = self.font_medium.render("SETTINGS", True, COLORS.UI_TEXT)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))
        
        for el in self.settings_ui_elements:
            el.draw(self.screen)
    
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
        """Setup level selection UI with 10 levels."""
        self.level_select_buttons = []
        
        # Grid layout: 5 columns x 2 rows
        cols = 5
        rows = 2
        btn_w = 140
        btn_h = 100
        gap_x = 20
        gap_y = 30
        
        total_width = cols * btn_w + (cols - 1) * gap_x
        total_height = rows * btn_h + (rows - 1) * gap_y
        start_x = (SCREEN_WIDTH - total_width) // 2
        start_y = 150
        
        for i in range(10):
            level_num = i + 1
            row = i // cols
            col = i % cols
            
            x = start_x + col * (btn_w + gap_x)
            y = start_y + row * (btn_h + gap_y)
            
            # Get best stars for this level
            best_stars = 0
            if hasattr(self, 'stats_tracker'):
                best_stars = self.stats_tracker.get_best_stars(level_num)
            
            btn = Button(x, y, btn_w, btn_h, f"Level {level_num}", self.font_medium,
                        action=lambda lv=level_num: self._start_level(lv))
            btn.stars = best_stars
            btn.level_num = level_num
            self.level_select_buttons.append(btn)
        
        # Back button
        cx = SCREEN_WIDTH // 2
        self.level_select_back_btn = Button(cx - 120, SCREEN_HEIGHT - 90, 240, 55, 
                                            "BACK", self.font_medium,
                                            action=lambda: self.change_state(GameState.MENU))
    
    def _start_level(self, level_num):
        """Start a specific level."""
        self.current_level_num = level_num
        self.reset_level_requested = True
        self.change_state(GameState.PLAYING)
    
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
            print(f"[Maze Bourne] Loading Endless Floor {self.current_level_num}...")
            self.level = Level.from_endless(self.current_level_num)
            
            # Initialize behavior tracker for endless mode (or keep existing one)
            from src.ai.player_tracker import PlayerBehaviorTracker
            if self.behavior_tracker is None:
                self.behavior_tracker = PlayerBehaviorTracker()
            else:
                # Reset per-floor data but keep cumulative stats
                self.behavior_tracker.reset_for_new_floor()
            
            # Initialize LLM strategist for endless mode
            from src.ai.strategist import EnemyStrategist
            if not hasattr(self, 'strategist') or self.strategist is None:
                self.strategist = EnemyStrategist(self.settings_manager)
        else:
            # Create campaign level
            print(f"[Maze Bourne] Loading Campaign Level {self.current_level_num}...")
            self.level = Level.from_campaign(self.current_level_num)
        
        # Create player at spawn point with difficulty-based health
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
        
        print(f"[Maze Bourne] Level initialized: {self.level.width}x{self.level.height}")
        print(f"[Maze Bourne] Player spawned at: ({spawn_x}, {spawn_y})")
        print(f"[Maze Bourne] Spawned {len(self.enemies)} enemies")
        print(f"[Maze Bourne] Spawned {len(self.game_object_manager.objects)} game objects")
        
        # Start level timer
        self.stats_tracker.start_level(self.current_level_num)
        
        # Start ambient music
        if hasattr(self, 'music_generator') and not self.music_generator.is_playing:
            music_volume = self.settings_manager.get("audio", "music_volume") or 0.3
            self.music_generator.play(volume=music_volume)
    
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
        
        # Update game objects
        if self.game_object_manager:
            self.game_object_manager.update(dt, self)
            self.game_object_manager.check_player_collision(self.player, self)
        
        if self.renderer:
            self.renderer.update(dt)
    
    def _playing_render(self):
        """Render playing state."""
        if self.renderer:
            self.renderer.render(self.screen)
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
        cx = SCREEN_WIDTH // 2
        self.credits_buttons = [
             Button(cx - 120, SCREEN_HEIGHT - 90, 240, 55, "BACK", self.font_medium, 
                   action=lambda: self.change_state(GameState.MENU))
        ]
        self.credits_offset = 0.0

    def _credits_update(self, dt: float):
        self.credits_offset += 30 * dt
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        for btn in self.credits_buttons:
             btn.update(mouse_pos, mouse_click, self.audio_manager)
        if self.is_key_just_pressed(pygame.K_ESCAPE):
             self.change_state(GameState.MENU)

    def _credits_render(self):
        self.screen.fill(COLORS.VOID)
        
        lines = [
            "MAZE BOURNE", "", "Created by", "Antigravity Agent", "",
            "Tools Used", "Pygame Community Edition", "Python 3", "",
            "Special Thanks", "Google DeepMind", "The User", "",
            "Assets", "Procedural Audio Generator", "Geometric Graphics Engine", "",
            "Thank you for playing!"
        ]
        
        cx = SCREEN_WIDTH // 2
        start_y = SCREEN_HEIGHT - 100 - self.credits_offset
        
        for line in lines:
            if start_y > SCREEN_HEIGHT:
                 start_y += 40
                 continue
            if start_y < -50:
                 pass 
            
            color = COLORS.PLAYER if line == "MAZE BOURNE" else COLORS.UI_TEXT
            font = self.font_large if line == "MAZE BOURNE" else self.font_medium
            
            surf = font.render(line, True, color)
            self.screen.blit(surf, surf.get_rect(center=(cx, start_y)))
            start_y += 50
            
        if start_y < -500: self.credits_offset = -SCREEN_HEIGHT
        
        for btn in self.credits_buttons:
            btn.draw(self.screen)
            
    def _paused_enter(self):
        # Ensure buttons are created if they don't exist
        # But we should recreate them to ensure correct state/position
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        btn_w, btn_h = 300, 50
        gap = 65
        start_y = cy - gap
        
        self.pause_buttons = [
            Button(cx - btn_w//2, start_y, btn_w, btn_h, "RESUME", self.font_medium,
                   action=lambda: self.change_state(GameState.PLAYING)),
            
            Button(cx - btn_w//2, start_y + gap, btn_w, btn_h, "RESTART LEVEL", self.font_medium,
                   action=lambda: self._restart_level()),
                   
            Button(cx - btn_w//2, start_y + gap*2, btn_w, btn_h, "SETTINGS", self.font_medium,
                   action=lambda: self.change_state(GameState.SETTINGS)),
                   
            Button(cx - btn_w//2, start_y + gap*3, btn_w, btn_h, "MENU", self.font_medium,
                   action=lambda: self.change_state(GameState.MENU)),
        ]
        
    def _restart_level(self):
        self.reset_level_requested = True
        self.change_state(GameState.PLAYING)

    def _paused_update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        
        # Check if buttons exist (safety)
        if not hasattr(self, 'pause_buttons'):
            self._paused_enter()
            
        for btn in self.pause_buttons:
            btn.update(mouse_pos, mouse_click, self.audio_manager)
            
        if self.is_key_just_pressed(pygame.K_ESCAPE):
             self.change_state(GameState.PLAYING)

    def _paused_render(self):
        # Render game underneath
        if self.renderer:
            self.renderer.render(self.screen)
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(150)
        self.screen.blit(overlay, (0, 0))
        
        title = self.font_large.render("PAUSED", True, COLORS.UI_TEXT)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))
        
        if hasattr(self, 'pause_buttons'):
            for btn in self.pause_buttons:
                btn.draw(self.screen)
    
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
        """Update victory state."""
        if self.is_key_just_pressed(pygame.K_RETURN):
            # Analyze performance for AI adaptation
            if self.director:
                self.director.analyze_level_stats(self.stats_tracker)
                
            # Next level
            self.current_level_num += 1
            self.reset_level_requested = True
            self.change_state(GameState.PLAYING)
        elif self.is_key_just_pressed(pygame.K_ESCAPE):
            # Back to menu
            self.change_state(GameState.MENU)
    
    def _victory_render(self):
        """Render victory state with stats."""
        # Background
        self.screen.fill(COLORS.BACKGROUND)
        
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        
        # Title
        title_text = f"FLOOR {self.current_level_num} CLEARED!" if self.game_mode == "endless" else "LEVEL COMPLETE!"
        title = self.font_large.render(title_text, True, COLORS.EXIT)
        title_rect = title.get_rect(center=(cx, cy - 180))
        self.screen.blit(title, title_rect)
        
        # Get completion stats
        if hasattr(self, '_victory_stats'):
            stars, completion_time, is_new_best = self._victory_stats
        else:
            # Fallback
            stars = 1
            completion_time = 0.0
            is_new_best = False
        
        # Draw stars
        star_y = cy - 120
        star_spacing = 60
        star_start_x = cx - star_spacing
        
        for i in range(3):
            star_x = star_start_x + i * star_spacing
            self._draw_star(self.screen, star_x, star_y, 25, filled=(i < stars))
        
        # Time display
        time_text = self._format_time(completion_time)
        time_surf = self.font_medium.render(f"Time: {time_text}", True, COLORS.UI_TEXT)
        time_rect = time_surf.get_rect(center=(cx, cy - 40))
        self.screen.blit(time_surf, time_rect)
        
        # New best time indicator
        if is_new_best:
            best_surf = self.font_small.render("NEW BEST TIME!", True, COLORS.KEY)
            best_rect = best_surf.get_rect(center=(cx, cy))
            self.screen.blit(best_surf, best_rect)
        
        # Star thresholds
        thresholds = self.stats_tracker.get_star_thresholds(self.current_level_num - 1)
        threshold_y = cy + 40
        threshold_surf = self.font_tiny.render(
            f"Star Times: {self._format_time(thresholds[0])} | {self._format_time(thresholds[1])} | {self._format_time(thresholds[2])}", 
            True, COLORS.UI_TEXT_DIM
        )
        threshold_rect = threshold_surf.get_rect(center=(cx, threshold_y))
        self.screen.blit(threshold_surf, threshold_rect)
        
        # Newly unlocked achievements
        if hasattr(self, '_new_achievements') and self._new_achievements:
            ach_y = cy + 80
            ach_title = self.font_small.render("ACHIEVEMENTS UNLOCKED!", True, COLORS.KEY)
            ach_title_rect = ach_title.get_rect(center=(cx, ach_y))
            self.screen.blit(ach_title, ach_title_rect)
            
            for i, achievement in enumerate(self._new_achievements[:3]):
                ach_surf = self.font_tiny.render(f"• {achievement.name}", True, achievement.icon_color)
                ach_rect = ach_surf.get_rect(center=(cx, ach_y + 30 + i * 25))
                self.screen.blit(ach_surf, ach_rect)
        
        # Continue prompt
        continue_text = self.font_small.render("ENTER: Next Level  |  ESC: Menu", True, COLORS.UI_TEXT_DIM)
        continue_rect = continue_text.get_rect(center=(cx, SCREEN_HEIGHT - 60))
        self.screen.blit(continue_text, continue_rect)
    
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