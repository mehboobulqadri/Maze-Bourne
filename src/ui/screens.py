import pygame
import math
import time
from typing import List, Tuple, Callable
from src.ui.theme import UITheme
from src.ui.ui_manager import Screen
from src.core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLORS




class UISlider:
    def __init__(self, x: int, y: int, width: int, height: int, min_val: float, max_val: float, current_val: float, label: str, font: pygame.font.Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = current_val
        self.label = label
        self.font = font
        
        self.is_dragging = False
        self.handle_width = 16
        self.is_hovered = False
        
    def update(self, mouse_pos: Tuple[int, int], mouse_down: bool) -> float:
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Calculate handle pos for hit detection
        ratio = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        handle_x = self.rect.x + int(ratio * (self.rect.width - self.handle_width))
        handle_rect = pygame.Rect(handle_x, self.rect.y - 4, self.handle_width, self.rect.height + 8)
        
        if mouse_down:
            if handle_rect.collidepoint(mouse_pos) or (self.is_hovered and not self.is_dragging):
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
        label_surf = self.font.render(f"{self.label}: {self.current_val:.1f}", True, UITheme.COLOR_TEXT_PRIMARY)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 25))
        
        # Track Background
        draw_rect = pygame.Rect(self.rect.x, self.rect.y + 4, self.rect.width, 4)
        pygame.draw.rect(surface, UITheme.COLOR_PANEL_BORDER, draw_rect, border_radius=2)
        
        # Filled Track
        ratio = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        fill_width = int(ratio * self.rect.width)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y + 4, fill_width, 4)
        pygame.draw.rect(surface, UITheme.COLOR_STAMINA_BAR, fill_rect, border_radius=2)
        
        # Handle
        handle_x = self.rect.x + int(ratio * (self.rect.width - self.handle_width))
        handle_rect = pygame.Rect(handle_x, self.rect.y - 4, self.handle_width, self.rect.height + 8)
        
        color = UITheme.COLOR_TEXT_ACCENT if self.is_dragging else UITheme.COLOR_TEXT_PRIMARY
        pygame.draw.rect(surface, color, handle_rect, border_radius=4)

class SettingsScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.elements = []
        self.center_x = SCREEN_WIDTH // 2
        
    def on_enter(self):
        self.elements = []
        font_small = self.fonts['small']
        font_med = self.fonts['normal']
        
        # Sliders
        # We need access to settings manager via game
        sm = self.manager.game.settings_manager
        
        val_master = sm.get("audio", "master_volume") or 0.7
        self.slider_master = UISlider(self.center_x - 150, 200, 300, 20, 0.0, 1.0, val_master, "Master Volume", font_small)
        self.elements.append(self.slider_master)
        
        val_sfx = sm.get("audio", "sfx_volume") or 0.8
        self.slider_sfx = UISlider(self.center_x - 150, 280, 300, 20, 0.0, 1.0, val_sfx, "SFX Volume", font_small)
        self.elements.append(self.slider_sfx)
        
        # Back Button
        btn_back = UIButton(self.center_x - 120, 560, 240, 55, "BACK", 
                            lambda: self.manager.switch_screen("menu"), font_med)
        self.elements.append(btn_back)

    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        mouse_down = pygame.mouse.get_pressed()[0]
        
        # Update sliders
        old_master = self.slider_master.current_val
        new_master = self.slider_master.update(mouse_pos, mouse_down)
        if abs(new_master - old_master) > 0.001:
             self.manager.game.settings_manager.set("audio", "master_volume", new_master)
             self.manager.game.audio_manager.set_master_volume(new_master)
             
        old_sfx = self.slider_sfx.current_val
        new_sfx = self.slider_sfx.update(mouse_pos, mouse_down)
        if abs(new_sfx - old_sfx) > 0.001:
             self.manager.game.settings_manager.set("audio", "sfx_volume", new_sfx)
             self.manager.game.audio_manager.set_sfx_volume(new_sfx)

        # Update buttons
        for el in self.elements:
            if isinstance(el, UIButton):
                if not mouse_down:
                    el.update(mouse_pos, False)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            for el in self.elements:
                if isinstance(el, UIButton):
                    if el.update(mouse_pos, False): pass
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for el in self.elements:
                if isinstance(el, UIButton):
                    el.update(mouse_pos, True)
            return True
        return False
        
    def draw(self, surface: pygame.Surface):
        surface.fill(COLORS.BACKGROUND)
        
        title = self.fonts['header'].render("SETTINGS", True, UITheme.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(center=(self.center_x, 80)))
        
        for el in self.elements:
            el.draw(surface)

        for el in self.elements:
            el.draw(surface)

class CreditsScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.center_x = SCREEN_WIDTH // 2
        
    def on_enter(self):
        font = self.fonts['normal']
        
        # Back Button
        self.btn_back = UIButton(self.center_x - 120, SCREEN_HEIGHT - 100, 240, 55, "BACK", 
                            lambda: self.manager.switch_screen("menu"), font)
                            
        self.start_time = time.time()
        
    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()[0]
        
        self.btn_back.update(mouse_pos, mouse_click)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            if self.btn_back.update(mouse_pos, False): pass
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            self.btn_back.update(mouse_pos, True)
            return True
        return False
        
    def draw(self, surface: pygame.Surface):
        surface.fill(COLORS.BACKGROUND)
        
        # Title
        title = self.fonts['header'].render("CREDITS", True, UITheme.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(center=(self.center_x, 80)))
        
        # Developers
        devs = [
            "DEVELOPED BY",
            "",
            "Mehboob ul Qadri",
            "Zainab Saeed",
            "Muhmmad Ehtisham Anjum"
        ]
        
        y = 250
        for line in devs:
            color = UITheme.COLOR_TEXT_ACCENT if line == "DEVELOPED BY" else UITheme.COLOR_TEXT_PRIMARY
            font = self.fonts['title'] if line == "DEVELOPED BY" else self.fonts['normal']
            
            surf = font.render(line, True, color)
            surface.blit(surf, surf.get_rect(center=(self.center_x, y)))
            y += 50
            
        self.btn_back.draw(surface)

class UIButton:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, action: Callable, font: pygame.font.Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.font = font
        self.is_hovered = False
        self.is_pressed = False
        
        # Pre-render text
        self.text_surf = self.font.render(text, True, UITheme.COLOR_TEXT_PRIMARY)
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)
        
    def update(self, mouse_pos: Tuple[int, int], mouse_click: bool) -> bool:
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        clicked = False
        
        if self.is_hovered and mouse_click:
            self.is_pressed = True
        elif not mouse_click and self.is_pressed:
            if self.is_hovered:
                clicked = True
                if self.action:
                    self.action()
            self.is_pressed = False
        elif not mouse_click:
            self.is_pressed = False
            
        return clicked

    def draw(self, surface: pygame.Surface):
        # Color based on state
        color = UITheme.COLOR_BUTTON_NORMAL
        if self.is_pressed:
            color = UITheme.COLOR_BUTTON_PRESSED
        elif self.is_hovered:
            color = UITheme.COLOR_BUTTON_HOVER
            
        # Draw Body
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        
        # Draw Border
        pygame.draw.rect(surface, UITheme.COLOR_BUTTON_BORDER, self.rect, 2, border_radius=4)
        
        # Draw Glow if hovered
        if self.is_hovered:
             pygame.draw.rect(surface, (0, 255, 215, 50), self.rect.inflate(4, 4), 2, border_radius=6)

        surface.blit(self.text_surf, self.text_rect)

class PauseScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.buttons: List[UIButton] = []
        
        # Layout
        center_x = SCREEN_WIDTH // 2
        start_y = 250
        gap = 20
        btn_w, btn_h = UITheme.BUTTON_WIDTH, UITheme.BUTTON_HEIGHT
        
        self.create_buttons(center_x, start_y, gap, btn_w, btn_h)

    def create_buttons(self, x, start_y, gap, w, h):
        font = self.fonts['normal']
        
        def resume_game():
             self.manager.game.unpause()

        def open_settings():
             self.manager.switch_screen("settings")

        def quit_to_menu():
            self.manager.game.quit_to_menu()

        self.buttons = [
            UIButton(x - w//2, start_y, w, h, "RESUME", resume_game, font),
            UIButton(x - w//2, start_y + (h+gap), w, h, "SETTINGS", open_settings, font),
            UIButton(x - w//2, start_y + (h+gap)*2, w, h, "QUIT TO MENU", quit_to_menu, font)
        ]

    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            if not pygame.mouse.get_pressed()[0]:
                btn.update(mouse_pos, False)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn.update(mouse_pos, False):
                    pass
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                btn.update(mouse_pos, True)
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.game.unpause()
                return True
        return False

    def draw(self, surface: pygame.Surface):
        # Semi-transparent background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(UITheme.COLOR_BG_OVERLAY)
        surface.blit(overlay, (0,0))
        
        # Title
        title_font = self.fonts['header']
        title_text = "PAUSED"
        title_surf = title_font.render(title_text, True, UITheme.COLOR_TEXT_PRIMARY)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 150))
        surface.blit(title_surf, title_rect)
        
        # Buttons
        for btn in self.buttons:
            btn.draw(surface)

class GameOverScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.buttons: List[UIButton] = []
        self.is_victory = False
        self.stats = {}
        
        # Layout
        self.center_x = SCREEN_WIDTH // 2
        
    def on_enter(self, victory=False, stats=None):
        self.is_victory = victory
        self.stats = stats or {}
        
        self.create_buttons()
        
    def create_buttons(self):
        font = self.fonts['normal']
        btn_w, btn_h = UITheme.BUTTON_WIDTH, UITheme.BUTTON_HEIGHT
        gap = 20
        start_y = 500
        
        def restart_level():
            # Restart current level
            self.manager.game.reset_level_requested = True
            self.manager.game.change_state(GameState.PLAYING)
            
        def quit_to_menu():
            self.manager.game.quit_to_menu()
            
        self.buttons = [
            UIButton(self.center_x - btn_w//2, start_y, btn_w, btn_h, "TRY AGAIN", restart_level, font),
            UIButton(self.center_x - btn_w//2, start_y + btn_h + gap, btn_w, btn_h, "MAIN MENU", quit_to_menu, font)
        ]

    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            if not pygame.mouse.get_pressed()[0]:
                btn.update(mouse_pos, False)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.buttons[0] if event.type == pygame.MOUSEBUTTONDOWN else False: # Simple logic, better to use standard
             pass
             
        if event.type == pygame.MOUSEBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn.update(mouse_pos, False): pass
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                btn.update(mouse_pos, True)
            return True
        return False

    def draw(self, surface: pygame.Surface):
        # Draw dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0,0))
        
        # Title
        text = "VICTORY" if self.is_victory else "GAME OVER"
        color = UITheme.COLOR_TEXT_ACCENT if self.is_victory else UITheme.COLOR_TEXT_DANGER
        title_surf = self.fonts['header'].render(text, True, color)
        title_rect = title_surf.get_rect(center=(self.center_x, 150))
        surface.blit(title_surf, title_rect)
        
        # Stats
        y = 250
        stat_color = UITheme.COLOR_TEXT_PRIMARY
        if self.stats:
            lines = [
                f"Floor Reached: {self.stats.get('floor', 1)}",
                f"Time: {self.stats.get('time', 0):.1f}s",
                f"Score: {self.stats.get('score', 0)}"
            ]
            for line in lines:
                s = self.fonts['normal'].render(line, True, stat_color)
                r = s.get_rect(center=(self.center_x, y))
                surface.blit(s, r)
                y += 40
        
        # Buttons
        for btn in self.buttons:
            btn.draw(surface)

class MainMenuScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.buttons: List[UIButton] = []
        self.start_time = time.time()
        
        # Layout
        center_x = SCREEN_WIDTH // 2
        start_y = 300
        gap = 20
        btn_w, btn_h = UITheme.BUTTON_WIDTH + 60, UITheme.BUTTON_HEIGHT
        
        # Create Buttons (Actions will be hooked up in on_enter if needed, or static if manager.game accessible)
        # We need access to Game methods. Manager has self.game.
        
        self.create_buttons(center_x, start_y, gap, btn_w, btn_h)
        
    def create_buttons(self, x, start_y, gap, w, h):
        font = self.fonts['normal']
        
        # We wrap functions to ensure they bind correctly at runtime
        def start_campaign():
            self.manager.game.start_game("campaign")
            self.manager.switch_screen("hud")
            
        def start_endless():
            self.manager.game.start_game("endless")
            self.manager.switch_screen("hud")
            
        def quit_game():
            self.manager.game.running = False
            
        def go_settings():
             self.manager.switch_screen("settings")
             # And also change state to SETTINGS to satisfy game loop logic if needed
             self.manager.game.state = self.manager.game.GameState.SETTINGS 
             # Wait, importing GameState in screens.py?
             
        def go_credits():
             self.manager.switch_screen("credits")
             self.manager.game.state = self.manager.game.GameState.CREDITS

        self.buttons = [
            UIButton(x - w//2, start_y, w, h, "START CAMPAIGN", start_campaign, font),
            UIButton(x - w//2, start_y + (h+gap), w, h, "ENDLESS MODE", start_endless, font),
            UIButton(x - w//2, start_y + (h+gap)*2, w, h, "SETTINGS", go_settings, font),
            UIButton(x - w//2, start_y + (h+gap)*3, w, h, "CREDITS", go_credits, font),
            UIButton(x - w//2, start_y + (h+gap)*4, w, h, "QUIT", quit_game, font)
        ]

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn.update(mouse_pos, False): # Click logic handled in update
                    pass # Action triggered inside button
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                btn.update(mouse_pos, True)
            return True
        return False

    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        # Just update hover states for visuals if needed
        for btn in self.buttons:
            # We pass False for click here as we handle clicks in events, 
            # but update needs to run for hover detection every frame
            if not pygame.mouse.get_pressed()[0]:
                btn.update(mouse_pos, False)

    def draw(self, surface: pygame.Surface):
        # Background
        surface.fill(COLORS.BACKGROUND)
        
        # Animated Grid Effect
        t = time.time() - self.start_time
        grid_alpha = int(30 + math.sin(t) * 10)
        grid_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(grid_surf, (0, 255, 215, grid_alpha), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(grid_surf, (0, 255, 215, grid_alpha), (0, y), (SCREEN_WIDTH, y))
            
        surface.blit(grid_surf, (0,0))
        
        # Title
        title_font = self.fonts['header']
        title_text = "MAZE BOURNE"
        
        # Pulse Effect
        scale = 1.0 + math.sin(t * 2) * 0.02
        title_surf = title_font.render(title_text, True, UITheme.COLOR_TEXT_ACCENT)
        w, h = title_surf.get_size()
        scaled_surf = pygame.transform.smoothscale(title_surf, (int(w*scale), int(h*scale)))
        title_rect = scaled_surf.get_rect(center=(SCREEN_WIDTH // 2, 150))
        
        # Glow
        glow_rect = title_rect.inflate(20, 20)
        pygame.draw.ellipse(surface, (0, 100, 100), glow_rect) # Simple cheat glow behind
        
        surface.blit(scaled_surf, title_rect)
        
        # Buttons
        for btn in self.buttons:
            btn.draw(surface)

class HUDScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.font_stat = self.fonts['normal']
        self.font_boss = self.fonts['title']
        
    def draw(self, surface: pygame.Surface):
        player = self.manager.game.player
        if not player:
            return
            
        # 1. Health Bar (Bottom Left)
        self._draw_status_bar(surface, 20, SCREEN_HEIGHT - 50, 200, 20, 
                            player.hp / 3.0, UITheme.COLOR_HEALTH_BAR, "HP")
                            
        # 2. Stamina Bar (Bottom Left, above HP)
        self._draw_status_bar(surface, 20, SCREEN_HEIGHT - 80, 200, 15,
                            player.energy / 100.0, UITheme.COLOR_STAMINA_BAR, "ENG")
                            
        # 3. Boss Health (Top Center)
        boss = self.manager.game.current_boss
        if boss and boss.is_alive:
            self._draw_boss_bar(surface, boss)
            
        # 4. Stealth Indicator (Bottom Right)
        if player.is_stealthed:
            text = self.font_stat.render("STEALTH ACTIVE", True, UITheme.COLOR_TEXT_ACCENT)
            surface.blit(text, (SCREEN_WIDTH - 180, SCREEN_HEIGHT - 50))

    def _draw_status_bar(self, surface, x, y, w, h, pct, color, label):
        # Background
        pygame.draw.rect(surface, (30, 30, 30), (x, y, w, h), border_radius=4)
        # Fill
        fill_w = int(w * max(0, min(1, pct)))
        pygame.draw.rect(surface, color, (x, y, fill_w, h), border_radius=4)
        # Border
        pygame.draw.rect(surface, UITheme.COLOR_PANEL_BORDER, (x, y, w, h), 2, border_radius=4)
        # Label
        text = self.fonts['small'].render(label, True, UITheme.COLOR_TEXT_PRIMARY)
        surface.blit(text, (x - 30, y + (h-text.get_height())//2))

    def _draw_boss_bar(self, surface, boss):
        w, h = 600, 25
        x = (SCREEN_WIDTH - w) // 2
        y = 50
        
        # Background
        pygame.draw.rect(surface, (0, 0, 0), (x, y, w, h), border_radius=8)
        # Fill
        pct = boss.hp / boss.max_hp
        pygame.draw.rect(surface, UITheme.COLOR_BOSS_BAR, (x, y, int(w*pct), h), border_radius=8)
        # Border
        pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 2, border_radius=8)
        
        # Name
        text = self.font_boss.render(f"BOSS - TIER {boss.tier}", True, UITheme.COLOR_TEXT_DANGER)
        text_rect = text.get_rect(center=(SCREEN_WIDTH//2, y - 25))
        surface.blit(text, text_rect)
