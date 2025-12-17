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
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.DOUBLEBUF | pygame.HWSURFACE
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
        self.game_objects = []
        
        # Input state
        self.keys_pressed = set()
        self.keys_just_pressed = set()
        self.keys_just_released = set()
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        
        # Campaign progress
        self.current_level_num = 1
        self.reset_level_requested = False
        
        # Debug mode
        self.debug_mode = DEBUG_MODE
        self.show_fps = SHOW_FPS
        
        # Fonts
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 32)
        self.font_tiny = pygame.font.Font(None, 24)
        
        # Editor (needs fonts)
        self.editor = Editor(self)
        
        # Register default state handlers
        self._setup_default_handlers()
        
        # Initialize initial state
        if self.state in self.state_handlers:
            handler = self.state_handlers[self.state]
            if "enter" in handler and handler["enter"]:
                handler["enter"]()
    
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
    
    def run(self):
        """Main game loop - runs at up to 144hz."""
        last_time = time.perf_counter()
        
        while self.running:
            # Calculate delta time
            current_time = time.perf_counter()
            self.dt = current_time - last_time
            last_time = current_time
            
            # Cap delta time to prevent physics explosions
            self.dt = min(self.dt, 0.1)
            
            # Process events
            self._process_events()
            
            # Update current state
            if self.state in self.state_handlers:
                self.state_handlers[self.state]["update"](self.dt)
            
            # Render current state
            # CLEAR SCREEN logic moved inside render for custom backgrounds
            if self.state in self.state_handlers:
                self.state_handlers[self.state]["render"]()
            
            # Render debug info
            if self.show_fps:
                self._render_fps()
            
            # Flip display
            pygame.display.flip()
            
            # Frame rate management
            self.clock.tick(self.target_fps)
            
            # Update FPS counter
            self.frame_count += 1
            self.fps_update_timer += self.dt
            if self.fps_update_timer >= 0.5:
                self.fps = self.frame_count / self.fps_update_timer
                self.frame_count = 0
                self.fps_update_timer = 0.0
        
        self._cleanup()
    
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
            self.player = None 
        except Exception:
            self.level = None
            
        # UI Setup
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        btn_w, btn_h = 200, 45
        gap = 55
        
        self.menu_buttons = [
            Button(cx - btn_w//2, cy - 20, btn_w, btn_h, "PLAY", self.font_medium, 
                   action=lambda: self._menu_action("play")),
            Button(cx - btn_w//2, cy - 20 + gap, btn_w, btn_h, "SETTINGS", self.font_medium, 
                   action=lambda: self._menu_action("settings")),
            Button(cx - btn_w//2, cy - 20 + gap*2, btn_w, btn_h, "EDITOR", self.font_medium, 
                   action=lambda: self._menu_action("editor")),
            Button(cx - btn_w//2, cy - 20 + gap*3, btn_w, btn_h, "HELP", self.font_medium, 
                   action=lambda: self._menu_action("help")),
            Button(cx - btn_w//2, cy - 20 + gap*4, btn_w, btn_h, "CREDITS", self.font_medium, 
                   action=lambda: self._menu_action("credits")),
            Button(cx - btn_w//2, cy - 20 + gap*5, btn_w, btn_h, "QUIT", self.font_medium, 
                   action=lambda: self._menu_action("quit")),
        ]

    # ... _menu_update/render ...

    def _help_enter(self):
        cx = SCREEN_WIDTH // 2
        self.help_buttons = [
             Button(cx - 100, SCREEN_HEIGHT - 80, 200, 50, "BACK", self.font_medium, 
                   action=lambda: self.change_state(GameState.MENU))
        ]

    def _help_update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        for btn in self.help_buttons:
             btn.update(mouse_pos, mouse_click, self.audio_manager)
        if self.is_key_just_pressed(pygame.K_ESCAPE):
             self.change_state(GameState.MENU)

    def _help_render(self):
        self.screen.fill(COLORS.BACKGROUND)
        
        title = self.font_large.render("HOW TO PLAY", True, COLORS.PLAYER)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 50)))
        
        # Mechanics
        info = [
            ("Objective", "Find the Key (Gold) -> Escape (Green Portal)"),
            ("Movement", "WASD to Move. Shift to Sneak (Silent). Space to Dash."),
            ("Enemies", "Red Drones (Patrol), Orange Bots (Tracking), Yellow (Sound)."),
            ("Survival", "Avoid Vision Cones. Use Hiding Spots (Blue Boxes)."),
            ("Energy", "Dashing/Sneaking uses Energy. Stay still to Regen."),
        ]
        
        y = 120
        for head, body in info:
            h_surf = self.font_medium.render(head, True, COLORS.UI_ENERGY)
            self.screen.blit(h_surf, (100, y))
            b_surf = self.font_small.render(body, True, COLORS.UI_TEXT)
            self.screen.blit(b_surf, (100, y + 35))
            y += 80
            
        # Draw some example entities
        # Key
        pygame.draw.circle(self.screen, COLORS.KEY, (SCREEN_WIDTH - 200, 150), 15)
        k_txt = self.font_tiny.render("Key", True, COLORS.UI_TEXT_DIM)
        self.screen.blit(k_txt, (SCREEN_WIDTH - 200 - 10, 180))
        
        # Enemy
        pygame.draw.rect(self.screen, COLORS.ENEMY_PATROL, (SCREEN_WIDTH - 220, 250, 40, 40), border_radius=5)
        e_txt = self.font_tiny.render("Patrol", True, COLORS.UI_TEXT_DIM)
        self.screen.blit(e_txt, (SCREEN_WIDTH - 220, 300))
        
        for btn in self.help_buttons:
            btn.draw(self.screen)

    def _credits_enter(self):
        cx = SCREEN_WIDTH // 2
        self.credits_buttons = [
             Button(cx - 100, SCREEN_HEIGHT - 80, 200, 50, "BACK", self.font_medium, 
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
        
        # Rolling credits
        lines = [
            "MAZE BOURNE",
            "",
            "Created by",
            "Antigravity Agent",
            "",
            "Tools Used",
            "Pygame Community Edition",
            "Python 3",
            "",
            "Special Thanks",
            "Google DeepMind",
            "The User",
            "",
            "Assets",
            "Procedural Audio Generator",
            "Geometric Graphics Engine",
            "",
            "Thank you for playing!"
        ]
        
        cx = SCREEN_WIDTH // 2
        start_y = SCREEN_HEIGHT - 100 - self.credits_offset
        
        for line in lines:
            if start_y > SCREEN_HEIGHT:
                 start_y += 40
                 continue
            if start_y < -50:
                 pass # optimized out
            
            color = COLORS.PLAYER if line == "MAZE BOURNE" else COLORS.UI_TEXT
            font = self.font_large if line == "MAZE BOURNE" else self.font_medium
            
            surf = font.render(line, True, color)
            self.screen.blit(surf, surf.get_rect(center=(cx, start_y)))
            start_y += 50
            
        # Restart text if scrolled far
        if start_y < -500:
             self.credits_offset = -SCREEN_HEIGHT
        
        for btn in self.credits_buttons:
            btn.draw(self.screen)

    def _menu_update(self, dt: float):
        """Update menu state."""
        # Pan Camera
        if self.renderer and self.renderer.camera:
            self.renderer.camera.x += 20 * dt
            self.renderer.update(dt) # Update particles/effects
            
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
        self.settings_ui_elements.append(Button(cx - 100, 550, 200, 50, "BACK", self.font_medium, 
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
        
        # Create campaign level
        print(f"[Maze Bourne] Loading Campaign Level {self.current_level_num}...")
        self.level = Level.from_campaign(self.current_level_num)
        
        # Create player at spawn point
        spawn_x, spawn_y = self.level.spawn_point
        self.player = Player(spawn_x, spawn_y)
        
        # Initialize renderer if needed
        if not self.renderer:
            self.renderer = Renderer(self)
        self.renderer.setup_for_level(self.level)
        self.renderer.add_notification(f"Level {self.current_level_num}", duration=3.0)
        
        # Spawn enemies from level config
        self.enemies = []
        for config in self.level.get_enemy_configs():
            enemy = Enemy(config["x"], config["y"], config["type"])
            self.enemies.append(enemy)
        
        print(f"[Maze Bourne] Level initialized: {self.level.width}x{self.level.height}")
        print(f"[Maze Bourne] Player spawned at: ({spawn_x}, {spawn_y})")
        print(f"[Maze Bourne] Spawned {len(self.enemies)} enemies")
    
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
        
        # Update game systems
        if self.player:
            self.player.update(dt, self)
        
        for enemy in self.enemies:
            enemy.update(dt, self)
        
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
        ctrl_desc = self.font_small.render("Move. SHIFT to Sneak (Silent). SPACE to Dash.", True, COLORS.UI_TEXT)
        self.screen.blit(ctrl_desc, (250, start_y + 40))
        
        # 3. Enemies
        start_y += item_height + 20
        # Draw actual enemy shapes
        # Patrol (Red)
        pygame.draw.rect(self.screen, COLORS.ENEMY_PATROL, (60, start_y, 30, 30))
        pygame.draw.line(self.screen, (255, 0, 0), (75, start_y+15), (75+30, start_y+15), 2) # Vision ray
        
        # Guard (Orange)
        pygame.draw.circle(self.screen, COLORS.ENEMY_GUARD, (130, start_y + 15), 15)
        
        # Hunter (Yellow)
        pts = [(180, start_y + 30), (195, start_y), (210, start_y + 30)]
        pygame.draw.polygon(self.screen, COLORS.ENEMY_HUNTER, pts)
        
        en_text = self.font_medium.render("AVOID ENEMIES", True, COLORS.UI_ENERGY)
        self.screen.blit(en_text, (250, start_y))
        en_desc = self.font_small.render("Red: Patrols | Orange: Guards | Yellow: Hears Noise", True, COLORS.UI_TEXT)
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
             Button(cx - 100, SCREEN_HEIGHT - 80, 200, 50, "BACK", self.font_medium, 
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
        self.pause_buttons = [
            Button(cx - 100, cy - 60, 200, 50, "RESUME", self.font_medium,
                   action=lambda: self.change_state(GameState.PLAYING)),
            Button(cx - 100, cy + 20, 200, 50, "MENU", self.font_medium,
                   action=lambda: self.change_state(GameState.MENU)),
        ]

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
            # Next level
            self.current_level_num += 1
            self.reset_level_requested = True
            self.change_state(GameState.PLAYING)
    
    def _victory_render(self):
        """Render victory state."""
        text = self.font_large.render("LEVEL COMPLETE!", True, COLORS.EXIT)
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(text, rect)
        
        continue_text = self.font_small.render("Press ENTER to Continue", True, COLORS.UI_TEXT_DIM)
        continue_rect = continue_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(continue_text, continue_rect)
    
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