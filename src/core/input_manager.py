"""
Input Manager for Maze Bourne
Centralizes input handling and supports key rebinding
"""

import pygame
from typing import Dict, Callable, Optional
from enum import Enum, auto

class InputAction(Enum):
    """Game input actions that can be rebound."""
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    DASH = auto()
    PARRY = auto()
    INTERACT = auto()
    PAUSE = auto()
    DEBUG_TOGGLE = auto()

class InputManager:
    """Manages keyboard and mouse input with rebindable keys."""
    
    def __init__(self):
        self.key_bindings: Dict[InputAction, int] = {
            InputAction.MOVE_UP: pygame.K_w,
            InputAction.MOVE_DOWN: pygame.K_s,
            InputAction.MOVE_LEFT: pygame.K_a,
            InputAction.MOVE_RIGHT: pygame.K_d,
            InputAction.DASH: pygame.K_SPACE,
            InputAction.PARRY: pygame.K_q,
            InputAction.INTERACT: pygame.K_e,
            InputAction.PAUSE: pygame.K_ESCAPE,
            InputAction.DEBUG_TOGGLE: pygame.K_F3,
        }
        
        self.alternate_bindings: Dict[InputAction, int] = {
            InputAction.MOVE_UP: pygame.K_UP,
            InputAction.MOVE_DOWN: pygame.K_DOWN,
            InputAction.MOVE_LEFT: pygame.K_LEFT,
            InputAction.MOVE_RIGHT: pygame.K_RIGHT,
        }
        
        self.pressed_actions: Dict[InputAction, bool] = {action: False for action in InputAction}
        self.just_pressed: Dict[InputAction, bool] = {action: False for action in InputAction}
        self.just_released: Dict[InputAction, bool] = {action: False for action in InputAction}
        
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        self.mouse_just_pressed = [False, False, False]
    
    def update(self, events: list):
        """Update input state from pygame events."""
        self.just_pressed = {action: False for action in InputAction}
        self.just_released = {action: False for action in InputAction}
        self.mouse_just_pressed = [False, False, False]
        
        keys = pygame.key.get_pressed()
        
        for action, key in self.key_bindings.items():
            was_pressed = self.pressed_actions[action]
            is_pressed = keys[key]
            
            if action in self.alternate_bindings:
                is_pressed = is_pressed or keys[self.alternate_bindings[action]]
            
            self.pressed_actions[action] = is_pressed
            
            if is_pressed and not was_pressed:
                self.just_pressed[action] = True
            elif not is_pressed and was_pressed:
                self.just_released[action] = True
        
        self.mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        
        for i in range(3):
            if mouse_buttons[i] and not self.mouse_buttons[i]:
                self.mouse_just_pressed[i] = True
            self.mouse_buttons[i] = mouse_buttons[i]
    
    def is_action_pressed(self, action: InputAction) -> bool:
        """Check if action is currently held down."""
        return self.pressed_actions.get(action, False)
    
    def is_action_just_pressed(self, action: InputAction) -> bool:
        """Check if action was just pressed this frame."""
        return self.just_pressed.get(action, False)
    
    def is_action_just_released(self, action: InputAction) -> bool:
        """Check if action was just released this frame."""
        return self.just_released.get(action, False)
    
    def rebind_key(self, action: InputAction, new_key: int):
        """Rebind an action to a new key."""
        self.key_bindings[action] = new_key
    
    def get_binding(self, action: InputAction) -> int:
        """Get current key binding for an action."""
        return self.key_bindings.get(action, -1)
    
    def get_movement_vector(self) -> tuple[float, float]:
        """Get normalized movement vector from input."""
        dx = 0.0
        dy = 0.0
        
        if self.is_action_pressed(InputAction.MOVE_LEFT):
            dx -= 1.0
        if self.is_action_pressed(InputAction.MOVE_RIGHT):
            dx += 1.0
        if self.is_action_pressed(InputAction.MOVE_UP):
            dy -= 1.0
        if self.is_action_pressed(InputAction.MOVE_DOWN):
            dy += 1.0
        
        if dx != 0 and dy != 0:
            magnitude = (dx * dx + dy * dy) ** 0.5
            dx /= magnitude
            dy /= magnitude
        
        return (dx, dy)
    
    def is_mouse_just_pressed(self, button: int = 0) -> bool:
        """Check if mouse button was just clicked (0=left, 1=middle, 2=right)."""
        return self.mouse_just_pressed[button] if 0 <= button < 3 else False
    
    def get_mouse_pos(self) -> tuple[int, int]:
        """Get current mouse position."""
        return self.mouse_pos
