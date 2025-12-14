"""
Maze Bourne - Main Game Engine
Handles game loop, state management, and core systems
"""

import pygame
import sys
import time
from typing import Optional, Callable, Dict, Any
from enum import Enum

from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TARGET_FPS, WINDOW_TITLE,
    GameState, COLORS, DEBUG_MODE, SHOW_FPS
)
from src.core.editor import Editor


class Game:
    """
    Main game class managing the game loop and core systems.
    Supports up to 144hz refresh with delta time handling.
    """
    
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        pygame.mixer.init()
        
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
    
    def _setup_default_handlers(self):
        """Set up default state handlers."""
        # Menu state
        self.register_state_handler(GameState.MENU, 
            update=self._menu_update,
            render=self._menu_render
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
            render=self._paused_render
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

        # Editor state
        self.register_state_handler(GameState.EDITOR,
            update=self.editor.update,
            render=self.editor.render,
            enter=self.editor.enter
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
            self.screen.fill(COLORS.BACKGROUND)
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
    
    def _menu_update(self, dt: float):
        """Update menu state."""
        # Press Enter to start game
        if self.is_key_just_pressed(pygame.K_RETURN):
            self.current_level_num = 1
            self.reset_level_requested = True
            self.change_state(GameState.PLAYING)
        
        # Press Escape to quit
        if self.is_key_just_pressed(pygame.K_ESCAPE):
            self.running = False
            
        # Press E to Editor
        if self.is_key_just_pressed(pygame.K_e):
            self.change_state(GameState.EDITOR)
    
    def _menu_render(self):
        """Render menu state."""
        # Title
        title = self.font_large.render("MAZE BOURNE", True, COLORS.PLAYER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.font_medium.render("A Stealth AI Adventure", True, COLORS.UI_TEXT_DIM)
        sub_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 60))
        self.screen.blit(subtitle, sub_rect)
        
        # Instructions
        start_text = self.font_small.render("Press ENTER to Start", True, COLORS.UI_TEXT)
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(start_text, start_rect)
        
        quit_text = self.font_small.render("Press ESC to Quit", True, COLORS.UI_TEXT_DIM)
        quit_rect = quit_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
        self.screen.blit(quit_text, quit_rect)
        
        editor_text = self.font_tiny.render("Press E for Level Editor", True, COLORS.UI_TEXT_DIM)
        editor_rect = editor_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 140))
        self.screen.blit(editor_text, editor_rect)
    
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
    
    def _paused_update(self, dt: float):
        """Update paused state."""
        if self.is_key_just_pressed(pygame.K_ESCAPE):
            self.change_state(GameState.PLAYING)
        
        if self.is_key_just_pressed(pygame.K_q):
            self.change_state(GameState.MENU)
    
    def _paused_render(self):
        """Render paused state."""
        # Render game underneath
        if self.renderer:
            self.renderer.render(self.screen)
        
        # Dim overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(150)
        self.screen.blit(overlay, (0, 0))
        
        # Paused text
        paused = self.font_large.render("PAUSED", True, COLORS.UI_TEXT)
        paused_rect = paused.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(paused, paused_rect)
        
        resume = self.font_small.render("Press ESC to Resume", True, COLORS.UI_TEXT_DIM)
        resume_rect = resume.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(resume, resume_rect)
        
        quit_text = self.font_small.render("Press Q to Quit to Menu", True, COLORS.UI_TEXT_DIM)
        quit_rect = quit_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))
        self.screen.blit(quit_text, quit_rect)
    
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