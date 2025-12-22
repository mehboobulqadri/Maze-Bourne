"""
Tests for Input Manager
"""

import pytest
import pygame
from src.core.input_manager import InputManager, InputAction

@pytest.fixture
def input_manager():
    """Create input manager instance."""
    pygame.init()
    return InputManager()

def test_input_manager_initialization(input_manager):
    """Test input manager initializes correctly."""
    assert input_manager is not None
    assert len(input_manager.key_bindings) > 0
    assert InputAction.MOVE_UP in input_manager.key_bindings

def test_get_movement_vector(input_manager):
    """Test movement vector calculation."""
    vec = input_manager.get_movement_vector()
    assert isinstance(vec, tuple)
    assert len(vec) == 2

def test_rebind_key(input_manager):
    """Test key rebinding."""
    original_key = input_manager.get_binding(InputAction.DASH)
    new_key = pygame.K_LSHIFT
    
    input_manager.rebind_key(InputAction.DASH, new_key)
    assert input_manager.get_binding(InputAction.DASH) == new_key
    
    input_manager.rebind_key(InputAction.DASH, original_key)
    assert input_manager.get_binding(InputAction.DASH) == original_key

def test_mouse_position(input_manager):
    """Test mouse position tracking."""
    pos = input_manager.get_mouse_pos()
    assert isinstance(pos, tuple)
    assert len(pos) == 2
