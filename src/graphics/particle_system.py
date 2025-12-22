
import pygame
import random
import time
from typing import List, Tuple
from abc import ABC, abstractmethod

class Particle:
    def __init__(self, pos: tuple, vel: tuple, color: tuple, life: float, size: float):
        self.x, self.y = pos
        self.vx, self.vy = vel
        self.color = color
        self.max_life = life
        self.life = life
        self.size = size
        self.decay = 255.0 / life

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, offset: tuple):
        if self.life <= 0: return
        
        alpha = int((self.life / self.max_life) * 255)
        # Simple square/circle particle
        sx = int(self.x + offset[0])
        sy = int(self.y + offset[1])
        
        # Create surface for alpha support if needed, or simple draw
        # Simple draw is faster
        if alpha > 10:
             # Just fade size for effect
             r = max(1, int(self.size * (self.life / self.max_life)))
             pygame.draw.circle(surface, self.color, (sx, sy), r)

class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []
        
    def emit(self, pos: tuple, color: tuple, count: int = 10, speed: float = 100.0, life: float = 1.0, size: float = 3.0):
        for _ in range(count):
            angle = random.uniform(0, 6.28)
            v_speed = random.uniform(speed * 0.5, speed * 1.5)
            vx = math.cos(angle) * v_speed
            vy = math.sin(angle) * v_speed
            
            p = Particle(pos, (vx, vy), color, life * random.uniform(0.5, 1.5), size)
            self.particles.append(p)
            
    def update(self, dt: float):
        # Filter alive
        self.particles = [p for p in self.particles if p.update(dt)]
        
    def draw(self, surface: pygame.Surface, camera_offset: tuple = (0,0)):
        for p in self.particles:
            p.draw(surface, camera_offset)
            
# Need math import
import math
