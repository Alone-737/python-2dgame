import sdl3
from pyglm import glm
from Animation import Animation
from TImer import Timer
class PlayerState:
    def __init__(self, weaponCooldown=0.1,hp=100,max_hp=100):
        self.state = "idle"  
        self.weaponTimer = Timer(weaponCooldown)
        self.hp=hp
        self.max_hp=max_hp
        self.damage_cooldown=0
    def TakeDamage(self,amount):
        if self.damage_cooldown <= 0:  
            self.hp -= amount
            if self.hp <= 0:
                self.hp = 0
                self.state = "dead"  
            self.damage_cooldown = 60 
    # Helper properties
    @property
    def idle(self):
        return self.state == "idle"

    
    @property
    def running(self):
        return self.state == "running"
    
    @property
    def jumping(self):
        return self.state == "jumping"
    
    @property
    def sliding(self):
        return self.state == "sliding"

class BulletState:
    def __init__(self, moving=False, colliding=False, inactive=True):
        self.moving = moving
        self.colliding = colliding
        self.inactive = inactive

class EnemyState:
    def __init__(self):
        self.state = "shambling"
        self.damageTimer = Timer(0.5)
        self.hitPoints = 100
        
    # Helper properties 
    @property
    def shambling(self):
        return self.state == "shambling"
    
    @shambling.setter
    def shambling(self, value):
        if value:
            self.state = "shambling"
    
    @property
    def damage(self):
        return self.state == "damage"
    
    @damage.setter
    def damage(self, value):
        if value:
            self.state = "damage"
    
    @property
    def dead(self):
        return self.state == "dead"
    
    @dead.setter
    def dead(self, value):
        if value:
            self.state = "dead"

class ObjectData:
    def __init__(self, player=None, bullet=None,enemy=None):
        self.player = player or PlayerState()
        self.bullet = bullet or BulletState()
        self.enemy=enemy or EnemyState()

class ObjectType:
    def __init__(self, player=False, level=False, enemy=False, bullet=False):
        self.player = player
        self.level = level
        self.enemy = enemy
        self.bullet = bullet

class GameObject:
    def __init__(self):
        self.type = ObjectType(level=True)
        self.data = ObjectData()
        self.direction = 1
        self.maxSpeedX: float = 0.0
        self.position = glm.vec2(0.0, 0.0)
        self.velocity = glm.vec2(0.0, 0.0)
        self.acceleration = glm.vec2(0.0, 0.0)
        self.animations: list[Animation] = []
        self.currentAnimation = -1
        self.texture = None
        self.dynamic = False
        self.grounded = False
        self.collider = sdl3.SDL_FRect(x=0, y=0, w=0, h=0)
        self.flashTimer=Timer(0.05)
        self.shouldFlash=False
        self.spriteframe=1