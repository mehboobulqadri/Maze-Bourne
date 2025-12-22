"""
Boss Battle System
Unique boss encounters every 10 floors in Endless Mode.
Features attack patterns, parryable attacks, and button puzzle mechanics.
"""

import math
import time
import random
from enum import Enum, auto
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

from src.utils.grid import GridPos
from src.core.constants import TILE_SIZE
from src.core.logger import get_logger


class BossState(Enum):
    """Boss behavior states."""
    IDLE = auto()
    PATROLLING = auto()
    CHARGING = auto()
    ATTACKING = auto()
    STUNNED = auto()
    VULNERABLE = auto()
    ENRAGED = auto()
    DEFEATED = auto()


class AttackType(Enum):
    """Types of boss attacks."""
    MELEE_SWIPE = auto()     # Fast, short range, parryable
    CHARGE = auto()          # Dash attack, dodgeable
    GROUND_SLAM = auto()     # AOE, requires running away
    PROJECTILE = auto()      # Ranged attack, dodgeable
    SUMMON = auto()          # Spawns minions


@dataclass
class Attack:
    """An attack the boss can perform."""
    attack_type: AttackType
    damage: int
    range: float
    windup_time: float  # Seconds to telegraph before attack
    active_time: float  # How long attack hitbox is active
    cooldown: float     # Seconds before can use again
    is_parryable: bool = False
    aoe_radius: float = 0.0  # For area attacks
    

class Boss:
    """
    Boss entity for floor 10, 20, 30... battles.
    
    Mechanics:
    - Multiple attack patterns with telegraph animations
    - Parryable attacks that stun the boss briefly
    - Requires hitting 4 buttons in arena to make vulnerable
    - Enrage phase at low health
    """
    
    def __init__(self, x: float, y: float, boss_tier: int = 1):
        # Position
        self.x = x
        self.y = y
        self.spawn_x = x
        self.spawn_y = y
        
        # Stats (scale with tier)
        self.tier = boss_tier
        self.max_health = 5 + (boss_tier * 2)  # 7, 9, 11, etc.
        self.health = self.max_health
        self.speed = 2.0 + (boss_tier * 0.3)
        self.size = 1.5  # Larger than regular enemies
        
        # State machine
        self.state = BossState.IDLE
        self.state_timer = 0.0
        self.previous_state = BossState.IDLE
        
        # Attack system
        self.current_attack: Optional[Attack] = None
        self.attack_timer = 0.0
        self.attack_cooldowns: dict = {}  # attack_type -> time remaining
        self.attack_target: Optional[Tuple[float, float]] = None
        
        # Define attacks based on tier
        self._init_attacks()
        
        # Vulnerability (button puzzle)
        self.buttons_required = 4
        self.buttons_pressed = 0
        self.is_vulnerable = False
        self.vulnerability_timer = 0.0
        self.vulnerability_duration = 3.0  # Seconds to deal damage
        
        # Stun state
        self.stun_timer = 0.0
        self.stun_duration = 2.0
        
        # Movement
        self.facing_direction = (0, 1)
        self.velocity = (0.0, 0.0)
        self.charge_target: Optional[Tuple[float, float]] = None
        
        # Enrage
        self.is_enraged = False
        self.enrage_threshold = 0.3  # Enrage at 30% health
        
        # Visual feedback
        self.flash_timer = 0.0
        self.shake_amount = 0.0
        
        # Status
        self.is_alive = True
        self.is_defeated = False
        
    def _init_attacks(self):
        """Initialize attack patterns based on tier."""
        self.attacks = [
            Attack(
                attack_type=AttackType.MELEE_SWIPE,
                damage=1,
                range=1.5,
                windup_time=0.5,
                active_time=0.3,
                cooldown=1.5,
                is_parryable=True
            ),
            Attack(
                attack_type=AttackType.CHARGE,
                damage=1,
                range=6.0,
                windup_time=0.8,
                active_time=0.5,
                cooldown=3.0,
                is_parryable=False
            ),
        ]
        
        # Add more attacks for higher tiers
        if self.tier >= 2:
            self.attacks.append(Attack(
                attack_type=AttackType.GROUND_SLAM,
                damage=1,
                range=3.0,
                windup_time=1.0,
                active_time=0.4,
                cooldown=4.0,
                is_parryable=False,
                aoe_radius=2.5
            ))
        
        if self.tier >= 3:
            self.attacks.append(Attack(
                attack_type=AttackType.SUMMON,
                damage=0,
                range=0,
                windup_time=1.5,
                active_time=0.1,
                cooldown=8.0,
                is_parryable=False
            ))
    
    def update(self, dt: float, game):
        """Update boss AI and animations."""
        if not self.is_alive:
            return
        
        player = game.player
        level = game.level
        
        # Update timers
        self.state_timer += dt
        self.flash_timer = max(0, self.flash_timer - dt)
        self.shake_amount = max(0, self.shake_amount - dt * 10)
        
        # Update attack cooldowns
        for atk_type in list(self.attack_cooldowns.keys()):
            self.attack_cooldowns[atk_type] -= dt
            if self.attack_cooldowns[atk_type] <= 0:
                del self.attack_cooldowns[atk_type]
        
        # Check for enrage
        if not self.is_enraged and self.health <= self.max_health * self.enrage_threshold:
            self._enter_enrage()
        
        # State machine
        if self.state == BossState.IDLE:
            self._update_idle(dt, player)
        elif self.state == BossState.PATROLLING:
            self._update_patrol(dt, player)
        elif self.state == BossState.CHARGING:
            self._update_charging(dt, player)
        elif self.state == BossState.ATTACKING:
            self._update_attacking(dt, player, game)
        elif self.state == BossState.STUNNED:
            self._update_stunned(dt)
        elif self.state == BossState.VULNERABLE:
            self._update_vulnerable(dt)
        elif self.state == BossState.ENRAGED:
            self._update_enraged(dt, player)
    
    def _change_state(self, new_state: BossState):
        """Change boss state."""
        self.previous_state = self.state
        self.state = new_state
        self.state_timer = 0.0
    
    def _update_idle(self, dt: float, player):
        """Idle - decide next action."""
        if self.state_timer > 0.5:
            # Start patrolling or attack
            dist_to_player = self._distance_to(player.x, player.y)
            
            if dist_to_player < 2.0:
                self._choose_attack(player)
            else:
                self._change_state(BossState.PATROLLING)
    
    def _update_patrol(self, dt: float, player):
        """Move toward player."""
        # Move toward player
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0.1:
            speed = self.speed * (1.5 if self.is_enraged else 1.0)
            self.x += (dx / dist) * speed * dt
            self.y += (dy / dist) * speed * dt
            self.facing_direction = (dx / dist, dy / dist)
        
        # Check if close enough to attack
        if dist < 2.0:
            self._choose_attack(player)
        
        # Max patrol time
        if self.state_timer > 5.0:
            self._change_state(BossState.IDLE)
    
    def _choose_attack(self, player):
        """Choose and start an attack."""
        available_attacks = [
            atk for atk in self.attacks 
            if atk.attack_type not in self.attack_cooldowns
        ]
        
        if not available_attacks:
            self._change_state(BossState.PATROLLING)
            return
        
        # Weight attacks (prefer melee when close, charge when far)
        dist = self._distance_to(player.x, player.y)
        
        weights = []
        for atk in available_attacks:
            weight = 1.0
            if atk.attack_type == AttackType.MELEE_SWIPE and dist < 2.0:
                weight = 3.0
            elif atk.attack_type == AttackType.CHARGE and dist > 3.0:
                weight = 2.0
            elif atk.attack_type == AttackType.GROUND_SLAM and dist < 3.0:
                weight = 2.5
            weights.append(weight)
        
        # Pick weighted random
        total = sum(weights)
        r = random.random() * total
        cumsum = 0
        for i, w in enumerate(weights):
            cumsum += w
            if r <= cumsum:
                self.current_attack = available_attacks[i]
                break
        
        if self.current_attack:
            self.attack_target = (player.x, player.y)
            self._change_state(BossState.CHARGING)
            self.attack_timer = 0.0
    
    def _update_charging(self, dt: float, player):
        """Wind up attack."""
        self.attack_timer += dt
        
        if not self.current_attack:
            self._change_state(BossState.IDLE)
            return
        
        # Update target tracking during windup
        self.attack_target = (player.x, player.y)
        
        # Face target
        dx = self.attack_target[0] - self.x
        dy = self.attack_target[1] - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0.1:
            self.facing_direction = (dx / dist, dy / dist)
        
        # Windup complete, execute attack
        if self.attack_timer >= self.current_attack.windup_time:
            self._change_state(BossState.ATTACKING)
            self.attack_timer = 0.0
    
    def _update_attacking(self, dt: float, player, game):
        """Execute attack."""
        self.attack_timer += dt
        
        if not self.current_attack:
            self._change_state(BossState.IDLE)
            return
        
        atk = self.current_attack
        
        # Check for parry (if parryable attack and player is parrying)
        if atk.is_parryable and getattr(player, 'is_parrying', False):
            if self._distance_to(player.x, player.y) < atk.range:
                self._get_parried(game)
                return
        
        # Execute attack based on type
        if atk.attack_type == AttackType.MELEE_SWIPE:
            self._execute_melee(player, game)
        elif atk.attack_type == AttackType.CHARGE:
            self._execute_charge(dt, player, game)
        elif atk.attack_type == AttackType.GROUND_SLAM:
            self._execute_slam(player, game)
        elif atk.attack_type == AttackType.SUMMON:
            self._execute_summon(game)
        
        # Attack finished
        if self.attack_timer >= atk.active_time:
            self.attack_cooldowns[atk.attack_type] = atk.cooldown
            self.current_attack = None
            self._change_state(BossState.IDLE)
    
    def _execute_melee(self, player, game):
        """Melee swipe attack."""
        if self._distance_to(player.x, player.y) < self.current_attack.range:
            self._deal_damage(player, game, self.current_attack.damage)
    
    def _execute_charge(self, dt: float, player, game):
        """Charge attack - dash toward target."""
        if self.attack_target:
            dx = self.attack_target[0] - self.x
            dy = self.attack_target[1] - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist > 0.5:
                charge_speed = self.speed * 4.0
                self.x += (dx / dist) * charge_speed * dt
                self.y += (dy / dist) * charge_speed * dt
            
            # Hit check
            if self._distance_to(player.x, player.y) < self.size:
                self._deal_damage(player, game, self.current_attack.damage)
    
    def _execute_slam(self, player, game):
        """Ground slam AOE attack."""
        if self.attack_timer < 0.1:  # Only on first frame
            dist = self._distance_to(player.x, player.y)
            if dist <= self.current_attack.aoe_radius:
                self._deal_damage(player, game, self.current_attack.damage)
            
            # Visual effect
            if game.renderer:
                game.renderer.camera.add_shake(15.0)
    
    def _execute_summon(self, game):
        """Summon minion enemies."""
        if self.attack_timer < 0.1:  # Only on first frame
            from src.entities.enemy import Enemy
            from src.core.constants import EnemyType
            
            # Spawn 1-2 minions
            for _ in range(random.randint(1, 2)):
                spawn_x = self.x + random.uniform(-3, 3)
                spawn_y = self.y + random.uniform(-3, 3)
                minion = Enemy(spawn_x, spawn_y, EnemyType.PATROL)
                minion.speed *= 0.8  # Slightly slower
                game.enemies.append(minion)
    
    def _deal_damage(self, player, game, damage: int):
        """Deal damage to player."""
        if hasattr(player, 'take_damage'):
            player.take_damage(damage, game)
    
    def _get_parried(self, game):
        """Handle being parried by player."""
        get_logger().debug("Boss parried!")
        self.stun_timer = self.stun_duration
        self._change_state(BossState.STUNNED)
        self.current_attack = None
        self.shake_amount = 5.0
        
        # Record parry for behavior tracker
        if hasattr(game, 'behavior_tracker') and game.behavior_tracker:
            game.behavior_tracker.record_parry(success=True)
    
    def _update_stunned(self, dt: float):
        """Stunned state (after parry)."""
        self.stun_timer -= dt
        if self.stun_timer <= 0:
            self._change_state(BossState.IDLE)
    
    def _update_vulnerable(self, dt: float):
        """Vulnerable state (all buttons pressed)."""
        self.vulnerability_timer -= dt
        if self.vulnerability_timer <= 0:
            self.is_vulnerable = False
            self.buttons_pressed = 0
            self._change_state(BossState.ENRAGED if self.is_enraged else BossState.IDLE)
    
    def _enter_enrage(self):
        """Enter enrage mode at low health."""
        self.is_enraged = True
        self.speed *= 1.3
        self.flash_timer = 1.0
        get_logger().info("Boss enraged!")
    
    def _update_enraged(self, dt: float, player):
        """Enraged behavior - more aggressive."""
        # Same as patrol but faster and more aggressive attacks
        self._update_patrol(dt, player)
    
    def take_damage(self, amount: int, game):
        """Take damage (only when vulnerable or stunned)."""
        if not (self.is_vulnerable or self.state == BossState.STUNNED):
            # Visual feedback - can't damage
            self.flash_timer = 0.2
            return False
        
        self.health -= amount
        self.flash_timer = 0.5
        self.shake_amount = 3.0
        
        if self.health <= 0:
            self._defeat(game)
            return True
        
        return True
    
    def _defeat(self, game):
        """Handle boss defeat."""
        self.is_alive = False
        self.is_defeated = True
        self._change_state(BossState.DEFEATED)
        
        get_logger().info("Boss defeated!")
        
        if game.renderer:
            from src.core.constants import COLORS
            game.renderer.add_notification("BOSS DEFEATED!", COLORS.PLAYER, duration=3.0)
            game.renderer.camera.add_shake(20.0)
    
    def on_button_pressed(self, game):
        """Called when player presses a button in the arena."""
        self.buttons_pressed += 1
        
        if game.renderer:
            from src.core.constants import COLORS
            game.renderer.add_notification(
                f"Buttons: {self.buttons_pressed}/{self.buttons_required}",
                COLORS.KEY, duration=1.5
            )
        
        if self.buttons_pressed >= self.buttons_required:
            self.is_vulnerable = True
            self.vulnerability_timer = self.vulnerability_duration
            self._change_state(BossState.VULNERABLE)
            
            if game.renderer:
                game.renderer.add_notification("BOSS VULNERABLE!", COLORS.PLAYER, duration=2.0)
    
    def _distance_to(self, x: float, y: float) -> float:
        """Calculate distance to position."""
        return math.sqrt((self.x - x)**2 + (self.y - y)**2)
    
    @property
    def pos(self):
        """Position as GridPos for compatibility."""
        return GridPos(self.x, self.y)


@dataclass
class BossButton:
    """Interactive button in boss arena that players must press."""
    x: float
    y: float
    button_id: str
    is_pressed: bool = False
    is_active: bool = True  # Required for GameObjectManager
    reset_timer: float = 0.0
    reset_delay: float = 10.0  # Seconds before button resets
    
    def update(self, dt: float):
        """Update button state."""
        if self.is_pressed:
            self.reset_timer += dt
            if self.reset_timer >= self.reset_delay:
                self.is_pressed = False
                self.reset_timer = 0.0
    
    def on_interact(self, player, game) -> bool:
        """Handle player interaction."""
        if self.is_pressed:
            return False
        
        self.is_pressed = True
        self.reset_timer = 0.0
        
        # Notify boss
        if hasattr(game, 'current_boss') and game.current_boss:
            game.current_boss.on_button_pressed(game)
        
        if hasattr(game, 'audio_manager'):
            game.audio_manager.play_sound("sfx_ui_select", 1.0)
        
        return True
    
    def on_player_enter(self, player, game):
        """Called when player walks onto the button."""
        pass
        
    def on_player_exit(self, player, game):
        """Called when player walks off the button."""
        pass


def create_boss(floor_number: int, arena_center: Tuple[float, float]) -> Boss:
    """Create boss for the given floor."""
    tier = floor_number // 10  # Floor 10 = tier 1, floor 20 = tier 2, etc.
    return Boss(arena_center[0], arena_center[1], boss_tier=tier)


def should_spawn_boss(floor_number: int) -> bool:
    """Check if this floor should have a boss."""
    return floor_number > 0 and floor_number % 10 == 0
