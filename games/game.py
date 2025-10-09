import sys
import sdl3
from sdl3 import SDL_Texture, SDL_FRect, SDL_Renderer
import sdl2.sdlmixer as mixer 
import sdl3.SDL_image as sdlimage
import ctypes
from pyglm import glm
import numpy as np
import random
from gameobject import (
    Animation,
    GameObject,
    ObjectType,
    PlayerState,
    Timer,
    BulletState,
    EnemyState,
)
import tracemalloc

# --- Load SDL3 core and image libraries ---
try:
    # Ensure SDL3 core is loaded
    ctypes.CDLL("libSDL3.so", mode=ctypes.RTLD_GLOBAL)
    ctypes.CDLL("libSDL3_image.so", mode=ctypes.RTLD_GLOBAL)
    ctypes.CDLL("libSDL2_mixer.so", mode=ctypes.RTLD_GLOBAL)
except OSError as e:
    print("Error: SDL library not found.")
    print(e)
    sys.exit(1)


LAYER_IDX_LEVEL = 0
LAYER_IDX_CHARACTERS = 1
# Audio constants
MIX_MAX_VOLUME = 128
MIX_DEFAULT_VOLUME = 64


class Gamestate:
    """Manages the overall state of the game world."""
    def __init__(self, state):
        self.layers = [[], []]
        self.playerIndex = 0
        self.player = None
        self.mapViewport = SDL_FRect(x=0, y=0, w=state.logicalw, h=state.logicalh)
        self.bg2Scroll = 0
        self.bg3Scroll = 0
        self.bg4Scroll = 0
        self.backgroundTiles = []
        self.foregroundTiles = []
        self.bullets = []
        self.debugMode = False
        self.deadEnemy = []
        self.playerDead = False
        #for infity level generation
        self.generated_chunks = 0
        self.last_chunk_end = 0
        self.chunk_width = 20 * Resources.TILE_SIZE


class Resources:
    """Loads and manages all game resources."""
    # Animation IDs for different object states
    ANIM_PLAYER_IDLE = 0
    ANIM_PLAYER_RUN = 1
    ANIM_PLAYER_SLIDE = 2
    ANIM_PLAYER_SHOOT = 3
    ANIM_PLAYER_SLIDE_SHOOT = 4
    MAP_ROWS: int = 5
    MAP_COLS: int = 50
    TILE_SIZE: int = 32
    ANIM_BULLET_MOVING: int = 0
    ANIM_BULLET_HIT: int = 1
    ANIM_ENEMY: int = 0
    ANIM_ENEMY_HIT: int = 1
    ANIM_ENEMY_DIE: int = 2

    # Store animations for the player
    playerAnims = []
    # store animations for bullet
    bulletAnims = []
    # store animations for enemy
    enemyAnims = []

    # sound chunks
    chunkShootHit = None
    chunkShoot = None
    chunkEnemyHit = None
    chunkWallHit = None
    chunkEnemyDie = None
    chunkBackground = None

    # Keep all loaded textures so we can unload them later
    textures = []
    texIdle = None
    texRun = None
    texBrick = None
    texGrass = None
    texGround = None
    texPanel = None
    texslide = None
    texBg1 = None
    texBg2 = None
    texBg3 = None
    texBg4 = None
    texBullet = None
    texBulletHit = None
    texShoot = None
    texRunShoot = None
    texSlideShoot = None
    texEnemy = None
    texEnemyHit = None
    texEnemyDie = None

    @staticmethod
    def load_sound(filepath: str):
        """Loads a sound effect from file."""
        # Mix_LoadWAV is an SDL2_mixer function
        chunk = mixer.Mix_LoadWAV(filepath.encode("utf-8"))
        if not chunk:
            print(f"Failed to load sound: {filepath} – {sdl3.SDL_GetError().decode()}")
        return chunk

    @staticmethod
    def load_music(filepath: str):
        """Loads background music from file."""
        music = mixer.Mix_LoadMUS(filepath.encode("utf-8"))
        if not bool(music):
            print(f"Failed to load music: {filepath} – {mixer.Mix_GetError().decode()}")
            return None
        return music


    @staticmethod
    def load_texture(renderer, filepath: str):
        """Loads a texture from file and stores it in the textures list."""
        tex = sdlimage.IMG_LoadTexture(renderer, filepath.encode("utf-8"))
        if not tex:
            print(f"Failed to load texture: {filepath}")
        sdl3.SDL_SetTextureScaleMode(tex, sdl3.SDL_SCALEMODE_NEAREST)
        Resources.textures.append(tex)
        return tex

    @staticmethod
    def load(state):
        """Load all game resources."""
        # Initialize SDL2_mixer
        if mixer.Mix_Init(mixer.MIX_INIT_MP3) < 0:
            print(
                "SDL_mixer could not initialize! Error:", mixer.Mix_GetError().decode()
            )
            return False
        # Mix_OpenAudio is an SDL2_mixer function, using the SDL2 signature
        if mixer.Mix_OpenAudio(44100, mixer.MIX_DEFAULT_FORMAT, 2, 2048) < 0:
            print("SDL_mixer OpenAudio failed! Error:", mixer.Mix_GetError().decode())
            return False
        
        # Prepare player animations list
        Resources.playerAnims = [None] * 5
        Resources.playerAnims[Resources.ANIM_PLAYER_IDLE] = Animation(8, 1.6)
        # Load idle texture
        Resources.playerAnims[Resources.ANIM_PLAYER_RUN] = Animation(4, 0.5)
        Resources.playerAnims[Resources.ANIM_PLAYER_SLIDE] = Animation(2, 1.0)
        Resources.playerAnims[Resources.ANIM_PLAYER_SHOOT] = Animation(4, 0.5)
        Resources.playerAnims[Resources.ANIM_PLAYER_SLIDE_SHOOT] = Animation(4, 0.5)
        Resources.bulletAnims = [None] * 2
        Resources.bulletAnims[Resources.ANIM_BULLET_MOVING] = Animation(4, 0.05)
        Resources.bulletAnims[Resources.ANIM_BULLET_HIT] = Animation(4, 0.15)
        Resources.enemyAnims = [None] * 3
        Resources.enemyAnims[Resources.ANIM_ENEMY] = Animation(8, 1.0)
        Resources.enemyAnims[Resources.ANIM_ENEMY_HIT] = Animation(8, 1.0)
        Resources.enemyAnims[Resources.ANIM_ENEMY_DIE] = Animation(18, 2.0)
        Resources.texIdle = Resources.load_texture(state.renderer, "idle.png")
        Resources.texRun = Resources.load_texture(state.renderer, "run.png")
        Resources.texslide = Resources.load_texture(state.renderer, "slide.png")
        Resources.texBrick = Resources.load_texture(state.renderer, "tiles/brick.png")
        Resources.texGrass = Resources.load_texture(state.renderer, "tiles/grass.png")
        Resources.texGround = Resources.load_texture(state.renderer, "tiles/ground.png")
        Resources.texPanel = Resources.load_texture(state.renderer, "tiles/panel.png")
        Resources.texBg1 = Resources.load_texture(
            state.renderer, "Backgroung/bg_layer1.png"
        )
        Resources.texBg2 = Resources.load_texture(
            state.renderer, "Backgroung/bg_layer2.png"
        )
        Resources.texBg3 = Resources.load_texture(
            state.renderer, "Backgroung/bg_layer3.png"
        )
        Resources.texBg4 = Resources.load_texture(
            state.renderer, "Backgroung/bg_layer4.png"
        )
        Resources.texBullet = Resources.load_texture(state.renderer, "bullet.png")
        Resources.texBulletHit = Resources.load_texture(
            state.renderer, "bullet_hit.png"
        )
        Resources.texShoot = Resources.load_texture(state.renderer, "shoot.png")
        Resources.texRunShoot = Resources.load_texture(state.renderer, "shoot_run.png")
        Resources.texSlideShoot = Resources.load_texture(
            state.renderer, "slide_shoot.png"
        )
        Resources.texEnemy = Resources.load_texture(state.renderer, "enemy.png")
        Resources.texEnemyHit = Resources.load_texture(state.renderer, "enemy_hit.png")
        Resources.texEnemyDie = Resources.load_texture(state.renderer, "enemy_die.png")
        Resources.chunkShoot = Resources.load_sound("audio/pop1.wav")
        Resources.chunkShootHit = Resources.load_sound("audio/audio_shoot_hit.wav")
        Resources.chunkEnemyHit = Resources.load_sound("audio/audio_enemy_hit.wav")
        Resources.chunkEnemyDie = Resources.load_sound("audio/audio_monster_die.wav")
        Resources.chunkWallHit = Resources.load_sound("audio/audio_wall_hit.wav")
        Resources.chunkBackground = Resources.load_music(
            "audio/bgmusic/converted_theme2.mp3"
        )

        return True

    @staticmethod
    def unload():
        """Unload all loaded resources."""
        # Destroy all loaded textures
        for tex in Resources.textures:
            sdl3.SDL_DestroyTexture(tex)
        Resources.textures.clear()

        # Unload sounds properly
        if Resources.chunkShoot:
            mixer.Mix_FreeChunk(Resources.chunkShoot)
        if Resources.chunkShootHit:
            mixer.Mix_FreeChunk(Resources.chunkShootHit)
        if Resources.chunkEnemyHit:
            mixer.Mix_FreeChunk(Resources.chunkEnemyHit)
        if Resources.chunkEnemyDie:
            mixer.Mix_FreeChunk(Resources.chunkEnemyDie)
        if Resources.chunkWallHit:
            mixer.Mix_FreeChunk(Resources.chunkWallHit)
        if Resources.chunkBackground:
            mixer.Mix_FreeMusic(Resources.chunkBackground)

        # Close audio
        mixer.Mix_CloseAudio()


class SDLstate:
    """Keeps track of SDL window and renderer state."""

    def __init__(self):
        self.window = None
        self.renderer = None
        self.width = None
        self.height = None
        self.logicalw = None
        self.logicalh = None
        # Get keyboard state
        self.keys = sdl3.SDL_GetKeyboardState(None)
        self.fullscreen = False


# helper functions
def play_sound(chunk, volume=128):
    """Play a sound effect with specified volume (0-128)."""
    if chunk:
        mixer.Mix_VolumeChunk(chunk, volume)
        mixer.Mix_PlayChannel(-1, chunk, 0)


def play_music(music, loops=-1):
    """Play background music (loops=-1 for infinite looping)."""
    if music:
        mixer.Mix_PlayMusic(music, loops)


def set_music_volume(volume):
    """Set music volume (0-128)."""
    mixer.Mix_VolumeMusic(volume)


def initialize(state):
    """Initializes SDL window and renderer."""
    state.window = sdl3.SDL_CreateWindow(
        b"SDL3 Demo", 800, 600, sdl3.SDL_WINDOW_RESIZABLE
    )
    if not state.window:
        print("Error creating SDL3 window")
        return False

    # create renderer
    state.renderer = sdl3.SDL_CreateRenderer(state.window, None)
    if not state.renderer:
        print("Error creating SDL3 renderer")
        return False
    sdl3.SDL_SetRenderVSync(state.renderer, 1)

    # Set logical resolution (for scaling)
    sdl3.SDL_SetRenderLogicalPresentation(
        state.renderer,
        state.logicalw,
        state.logicalh,
        sdl3.SDL_LOGICAL_PRESENTATION_LETTERBOX,
    )

    return True


def cleanup(state):
    """Destroys window and renderer, quits SDL."""
    if state.renderer:
        sdl3.SDL_DestroyRenderer(state.renderer)
    if state.window:
        sdl3.SDL_DestroyWindow(state.window)
    sdl3.SDL_Quit()
def window_creation():
    """Main SDL loop that creates a window and runs the game."""
    state = SDLstate()
    state.width = 1600
    state.height = 900
    state.logicalw = 640
    state.logicalh = 320

    # Initialize SDL
    if not initialize(state):
        return False

    if sdl3.SDL_Init(sdl3.SDL_INIT_VIDEO | sdl3.SDL_INIT_AUDIO) < 0:
        print("SDL_Init failed:", sdl3.SDL_GetError().decode())
        return False

    # Load resources (textures, animations, etc.)
    if not Resources.load(state):
        print("Failed to load resources. Exiting.")
        return False

    # Setup game state
    gs = Gamestate(state)
    print(f"Failed to load music: {Resources.chunkBackground} – {mixer.Mix_GetError().decode()}")

    gs = Gamestate(state)
    def debug_load_music(filepath, fallback=None):
        music = Resources.load_music(filepath)
        if music:
            print("Music loaded successfully")
            music_type = mixer.Mix_GetMusicType(music)
            music_types = {
                mixer.MUS_NONE: "NONE",
                mixer.MUS_CMD: "CMD",
                mixer.MUS_WAV: "WAV",
                mixer.MUS_MOD: "MOD",
                mixer.MUS_MID: "MID",
                mixer.MUS_OGG: "OGG",
                mixer.MUS_MP3: "MP3",
                mixer.MUS_FLAC: "FLAC",
                mixer.MUS_OPUS: "OPUS"
            }
            print(f"Music type: {music_types.get(music_type, 'UNKNOWN')}")
            return music
        else:
            print(f"Failed to load music file: {filepath}")
            if fallback:
                print(f"Trying fallback: {fallback}")
                return debug_load_music(fallback)
            else:
                print("No fallback music available")
                return None

    Resources.chunkBackground = debug_load_music("audio/bgmusic/converted_theme2.mp3", fallback="audio/bgmusic/fallback.mp3")

    # Generate initial chunks player must be in first chunk
    generateLevelChunk(gs, state, Resources, 0, spawn_player=True)

    assert gs.player is not None, "Player failed to spawn in initial chunk!"

    generateLevelChunk(gs, state, Resources, gs.last_chunk_end)
    generateLevelChunk(gs, state, Resources, gs.last_chunk_end)

    previousTime = sdl3.SDL_GetTicks()
    running = True
    event = sdl3.SDL_Event()
    # Draw player health bar at top of screen
    if gs.player:
        drawPlayerHealthBar(state, gs)

    # swap buffers and present
    sdl3.SDL_RenderPresent(state.renderer)
    set_music_volume(64)
    play_music(Resources.chunkBackground, -1)

    while running:
        nowTime = sdl3.SDL_GetTicks()
        deltaTime = (nowTime - previousTime) / 1000.0

        # --- Handle Events ---
        while sdl3.SDL_PollEvent(event):
            if event.type == sdl3.SDL_EVENT_QUIT:
                running = False

            elif event.type == sdl3.SDL_EVENT_WINDOW_RESIZED:
                state.width = event.window.data1
                state.height = event.window.data2

            elif event.type in (sdl3.SDL_EVENT_KEY_DOWN, sdl3.SDL_EVENT_KEY_UP):
                key_down = event.type == sdl3.SDL_EVENT_KEY_DOWN
                scancode = event.key.scancode

                # Special keys
                if not key_down and scancode == sdl3.SDL_SCANCODE_F12:
                    gs.debugMode = True
                elif not key_down and scancode == sdl3.SDL_SCANCODE_F10:
                    gs.debugMode = False
                elif not key_down and scancode == sdl3.SDL_SCANCODE_F11:
                    state.fullscreen = not state.fullscreen
                    sdl3.SDL_SetWindowFullscreen(state.window, state.fullscreen)

                # Player controls
                if gs.player:
                    handleKeyInputs(state, gs, gs.player, scancode, key_down)

        # --- Generate new level chunks as player moves forward ---
        if gs.player and gs.player.position.x > gs.last_chunk_end - (state.logicalw * 1.5):
            generateLevelChunk(gs, state, Resources, gs.last_chunk_end)

        # --- Update game objects ---
        for layer in gs.layers:
            for obj in layer:
                update(state, gs, Resources, obj, deltaTime)

        for bullet in gs.bullets[:]:  # Safe iteration
            update(state, gs, Resources, bullet, deltaTime)
            if bullet.currentAnimation != -1:
                bullet.animations[bullet.currentAnimation].step(deltaTime)

            if bullet.position.x < -1000 or bullet.position.x > 10000:
                gs.bullets.remove(bullet)

        # --- Viewport scrolling ---
        if gs.player:
            gs.mapViewport.x = (
                gs.player.position.x + Resources.TILE_SIZE / 2
            ) - gs.mapViewport.w / 2

        # --- Clean up far-off objects ---
        if gs.player:
            cleanupDistantObjects(gs, gs.player.position.x - state.logicalw * 2)

        # --- Draw Pass ---
        sdl3.SDL_SetRenderDrawColor(state.renderer, 20, 10, 20, 255)
        sdl3.SDL_RenderClear(state.renderer)

        sdl3.SDL_RenderTexture(state.renderer, Resources.texBg1, None, None)

        if gs.player:
            speed_x = gs.player.velocity.x
        else:
            speed_x = 0

        gs.bg4Scroll = drawParalaxBackground(state.renderer, Resources.texBg4, speed_x, gs.bg4Scroll, 0.075, deltaTime)
        gs.bg3Scroll = drawParalaxBackground(state.renderer, Resources.texBg3, speed_x, gs.bg3Scroll, 0.150, deltaTime)
        gs.bg2Scroll = drawParalaxBackground(state.renderer, Resources.texBg2, speed_x, gs.bg2Scroll, 0.300, deltaTime)

        for obj in gs.backgroundTiles:
            dst = SDL_FRect(
                x=obj.position.x - gs.mapViewport.x,
                y=obj.position.y,
                w=float(get_texture_size(obj.texture)[0]),
                h=float(get_texture_size(obj.texture)[1]),
            )
            sdl3.SDL_RenderTexture(state.renderer, obj.texture, None, dst)

        for layer in gs.layers:
            for obj in layer:
                drawObject(state, gs, obj, Resources.TILE_SIZE, Resources.TILE_SIZE, deltaTime)

        for bullet in gs.bullets:
            if not bullet.data.bullet.inactive:
                drawObject(state, gs, bullet, bullet.collider.w, bullet.collider.h, deltaTime)

        for obj in gs.foregroundTiles:
            dst = SDL_FRect(
                x=obj.position.x - gs.mapViewport.x,
                y=obj.position.y,
                w=float(get_texture_size(obj.texture)[0]),
                h=float(get_texture_size(obj.texture)[1]),
            )
            sdl3.SDL_RenderTexture(state.renderer, obj.texture, None, dst)

        # --- Debug Info ---
        if gs.debugMode and gs.player:
            sdl3.SDL_SetRenderDrawColor(state.renderer, 255, 255, 255, 255)

            player_state = gs.player.data.player
            if player_state.idle:
                state_str = "idle"
            elif player_state.running:
                state_str = "running"
            elif player_state.jumping:
                state_str = "jumping"
            elif player_state.sliding:
                state_str = "sliding"
            else:
                state_str = "unknown"

            text = f"S:{state_str}, B:{len(gs.bullets)}, G:{getattr(gs.player, 'grounded', False)}"
            sdl3.SDL_RenderDebugTextFormat(state.renderer, 5, 5, text.encode("utf-8"))

        # --- Remove dead enemies ---
        for layer in gs.layers:
            layer[:] = [obj for obj in layer if not (obj.type.enemy and obj.data.enemy.hitPoints <= 0)]

        # --- Present ---
        sdl3.SDL_RenderPresent(state.renderer)
        previousTime = nowTime

    # --- Cleanup ---
    Resources.unload()
    cleanup(state)
    return True

# --- Draw Object Function ---
def drawObject(
    state: SDLstate,
    gs: Gamestate,
    obj: GameObject,
    width: float,
    height: float,
    deltaTime: float,
):
    # calculate source rectangle based on animation
    srcX = (
        obj.animations[obj.currentAnimation].currentFrame() * width
        if obj.currentAnimation != -1
        else (obj.spriteframe - 1) * width
    )
    scr = SDL_FRect(srcX, 0, width, height)
    dst = SDL_FRect(obj.position.x - gs.mapViewport.x, obj.position.y, width, height)

    # determine flip mode
    flipmode = sdl3.SDL_FLIP_HORIZONTAL if obj.direction == -1 else sdl3.SDL_FLIP_NONE
    if not obj.shouldFlash:
        sdl3.SDL_RenderTextureRotated(
            state.renderer, obj.texture, scr, dst, 0, None, flipmode
        )
    else:
        # flash obj with bules tint
        sdl3.SDL_SetTextureColorModFloat(obj.texture, 1.0, 1.0, 2.55)
        sdl3.SDL_RenderTextureRotated(
            state.renderer, obj.texture, scr, dst, 0, None, flipmode
        )
        sdl3.SDL_SetTextureColorModFloat(obj.texture, 1, 1.0, 1.0)
        if obj.flashTimer.step(deltaTime):
            obj.shouldFlash = False

    # Draw health bar for enemies and player
    if obj.type.enemy or obj.type.player:
        drawHealthBar(state, gs, obj, obj.type.player)

    if gs.debugMode:
        rectA = SDL_FRect(
            x=obj.position.x + obj.collider.x - gs.mapViewport.x,
            y=obj.position.y + obj.collider.y,
            w=obj.collider.w,
            h=obj.collider.h,
        )
        sdl3.SDL_SetRenderDrawBlendMode(state.renderer, sdl3.SDL_BLENDMODE_BLEND)
        sdl3.SDL_SetRenderDrawColor(state.renderer, 255, 0, 0, 100)
        sdl3.SDL_RenderFillRect(state.renderer, rectA)
        sdl3.SDL_SetRenderDrawBlendMode(state.renderer, sdl3.SDL_BLENDMODE_NONE)

def update(
    state: SDLstate, gs: Gamestate, res: Resources, obj: GameObject, deltaTime: float
):
    # Handle player damage cooldown if this is the player object
    if obj.type.player and obj.data.player.damage_cooldown > 0:
        obj.data.player.damage_cooldown -= 1
    
    # Check if player is dead
    if obj.type.player and obj.data.player.hp <= 0:
        # Set player state to dead and stop movement
        obj.data.player.state = "dead"
        obj.velocity = glm.vec2(0, 0)
        gs.playerDead = True
        sdl3.SDL_Quit()
        return 

    def handleshooting(tex_normal, tex_shoot, anim_normal, anim_shoot):
        if state.keys[sdl3.SDL_SCANCODE_J] and obj.data.player.weaponTimer.is_timeout():  
            obj.texture = tex_shoot
            obj.currentAnimation = anim_shoot

            # Count active bullets
            active_bullets = sum(not b.data.bullet.inactive for b in gs.bullets)
            if active_bullets < 6:
                obj.data.player.weaponTimer.reset()

                bullet = GameObject()
                bullet.data.bullet = BulletState()
                bullet.type = ObjectType(bullet=True)
                bullet.direction = obj.direction
                bullet.texture = res.texBullet
                bullet.currentAnimation = res.ANIM_BULLET_MOVING
                bullet.animations = res.bulletAnims

                tw, th = get_texture_size(res.texBullet)
                bullet.collider = sdl3.SDL_FRect(x=0, y=0, w=float(tw), h=float(th))
                bullet.acceleration = glm.vec2(0, 0)

                yVariation = 40
                yVelocity = sdl3.SDL_rand(yVariation) - yVariation / 2.0
                bullet.velocity = glm.vec2(600.0 * obj.direction, yVelocity)
                bullet.maxSpeedX = 999.0

                left = 4
                right = 24
                t = (obj.direction + 1) / 2.0
                xOffset = left + (right - left) * t

                bullet.position = glm.vec2(
                    obj.position.x + xOffset,
                    obj.position.y + res.TILE_SIZE / 2,
                )

                bullet.dynamic = False
                bullet.data.bullet.inactive = False
                bullet.data.bullet.moving = True

                # Reuse or append bullet
                foundInactive = False
                for i in range(len(gs.bullets)):
                    if gs.bullets[i].data.bullet.inactive:
                        gs.bullets[i] = bullet
                        foundInactive = True
                        break
                if not foundInactive:
                    gs.bullets.append(bullet)

                play_sound(res.chunkShoot)
        else:
            obj.texture = tex_normal
            obj.currentAnimation = anim_normal


    # Update all animations
    if obj.currentAnimation != -1:
        obj.animations[obj.currentAnimation].step(deltaTime)

    # Apply gravity to dynamic objects that aren't grounded
    if obj.dynamic and not obj.grounded:
        obj.velocity += glm.vec2(0, 500) * deltaTime

    currentDirection: float = 0.0

    # Handle player-specific logic
    if obj.type.player:
        # Update weapon timer for player
        obj.data.player.weaponTimer.step(deltaTime)

        # Handle input: left/right movement
        if state.keys[sdl3.SDL_SCANCODE_A]:
            currentDirection += -1
            obj.direction = -1
        if state.keys[sdl3.SDL_SCANCODE_D]:
            currentDirection += 1
            obj.direction = 1

        # Get current player state
        player_state = obj.data.player

        # Handle state transitions based on grounded status
        if obj.grounded:
            if player_state.jumping:
                # Landed from jump
                if currentDirection != 0:
                    player_state.state = "running"
                    obj.texture = res.texRun
                    obj.currentAnimation = res.ANIM_PLAYER_RUN
                else:
                    player_state.state = "idle"
                    obj.texture = res.texIdle
                    obj.currentAnimation = res.ANIM_PLAYER_IDLE

        # Handle state-specific behavior
        if player_state.idle:
            if currentDirection != 0:
                player_state.state = "running"
                obj.texture = res.texRun
                obj.currentAnimation = res.ANIM_PLAYER_RUN
            else:
                obj.texture = res.texIdle
                obj.currentAnimation = res.ANIM_PLAYER_IDLE
                if abs(obj.velocity.x) > 0:
                    factor: float = -1.5 if obj.velocity.x > 0 else 1.5
                    amount: float = factor * obj.acceleration.x * deltaTime
                    if abs(obj.velocity.x) < abs(amount):
                        obj.velocity.x = 0
                    else:
                        obj.velocity.x += amount

            # Handle shooting while idle
            handleshooting(
                res.texIdle, res.texShoot, res.ANIM_PLAYER_IDLE, res.ANIM_PLAYER_SHOOT
            )

        elif player_state.running:
            if currentDirection == 0:
                player_state.state = "idle"
                obj.texture = res.texIdle
                obj.currentAnimation = res.ANIM_PLAYER_IDLE
            else:
                obj.velocity += glm.vec2(
                    currentDirection * obj.acceleration.x * deltaTime, 0
                )

            # Handle sliding when turning
            if obj.velocity.x * obj.direction < 0 and obj.grounded:
                handleshooting(
                    res.texslide,
                    res.texSlideShoot,
                    res.ANIM_PLAYER_SLIDE,
                    res.ANIM_PLAYER_SLIDE_SHOOT,
                )
            else:
                handleshooting(
                    res.texRun,
                    res.texRunShoot,
                    res.ANIM_PLAYER_RUN,
                    res.ANIM_PLAYER_RUN,
                )

        elif player_state.jumping:
            handleshooting(
                res.texRun, res.texRunShoot, res.ANIM_PLAYER_RUN, res.ANIM_PLAYER_RUN
            )
            if currentDirection != 0:
                obj.velocity.x += currentDirection * obj.acceleration.x * deltaTime

    # Handle enemy-specific logic
    elif obj.type.enemy:
        # Only process enemy AI if player exists
        if gs.player is not None:
            if obj.data.enemy.shambling:
                playerDir = glm.vec2(gs.player.position - obj.position)
                distance = glm.length(playerDir)

                if distance < 200 and distance > 50:
                    # Check if ground exists ahead
                    sensor_x_offset = (obj.collider.w / 2) * obj.direction
                    sensor = sdl3.SDL_FRect(
                        x=obj.position.x + obj.collider.x + sensor_x_offset,
                        y=obj.position.y + obj.collider.y + obj.collider.h + 1,
                        w=1.0,
                        h=1.0,
                    )

                    is_grounded_ahead = False
                    for layer in gs.layers:
                        for objB in layer:
                            if obj is objB or not objB.type.level:
                                continue
                            rectB = sdl3.SDL_FRect(
                                x=objB.position.x + objB.collider.x,
                                y=objB.position.y + objB.collider.y,
                                w=objB.collider.w,
                                h=objB.collider.h,
                            )
                            if sdl3.SDL_HasRectIntersectionFloat(sensor, rectB):
                                is_grounded_ahead = True
                                break
                        if is_grounded_ahead:
                            break

                    if not is_grounded_ahead:
                        obj.direction *= -1
                    else:
                        obj.direction = 1 if playerDir.x > 0 else -1

                    obj.velocity.x = 50.0 * obj.direction
                else:
                    obj.velocity.x = 0

            elif obj.data.enemy.damage:
                if obj.data.enemy.damageTimer.step(deltaTime):
                    obj.data.enemy.state = "shambling"
                    obj.texture = res.texEnemy
                    obj.currentAnimation = res.ANIM_ENEMY

            elif obj.data.enemy.dead:
                obj.velocity.x = 0
                if (obj.currentAnimation != -1 and 
                    obj.animations[obj.currentAnimation].isDone()):
                    obj.currentAnimation = -1
                    obj.spriteframe = 18
                    obj.data.enemy.hitPoints = 0
        else:
            # If player doesn't exist, enemies just stand still
            obj.velocity.x = 0

    # Handle bullet-specific logic
    elif obj.type.bullet:
        if obj.data.bullet.moving:
            if (obj.position.x - gs.mapViewport.x < 0 or
                obj.position.x - gs.mapViewport.x > state.logicalw or
                obj.position.y - gs.mapViewport.y < 0 or
                obj.position.y - gs.mapViewport.y > state.logicalh):
                obj.data.bullet.inactive = True
        elif obj.data.bullet.colliding:
            if (obj.currentAnimation != -1 and 
                obj.animations[obj.currentAnimation].timeout):
                obj.data.bullet.inactive = True

    # Apply velocity limits
    if hasattr(obj, 'maxSpeedX') and abs(obj.velocity.x) > obj.maxSpeedX:
        obj.velocity.x = np.sign(obj.velocity.x) * obj.maxSpeedX

    obj.position += obj.velocity * deltaTime

    # Check for collisions with solid objects
    if obj.dynamic or obj.type.bullet:
        for layer in gs.layers:
            for other_obj in layer:
                if obj is other_obj:
                    continue
                # Skip dead enemies
                if (other_obj.type.enemy and 
                    hasattr(other_obj.data.enemy, 'hitPoints') and 
                    other_obj.data.enemy.hitPoints <= 0):
                    continue
                # Check against level objects OR enemies
                if other_obj.type.level or other_obj.type.enemy:
                    checkcollision(state, gs, res, obj, other_obj, deltaTime)
                    if obj.type.bullet and obj.data.bullet.colliding:
                        break
            if obj.type.bullet and obj.data.bullet.colliding:
                obj.velocity = glm.vec2(0, 0)
                obj.data.bullet.moving = False
    
    # Only check player-enemy collisions if player exists
    if obj.type.player and gs.player is not None:
        player_rect = sdl3.SDL_FRect(
            x=obj.position.x + obj.collider.x,
            y=obj.position.y + obj.collider.y,
            w=obj.collider.w,
            h=obj.collider.h,
        )

        for layer in gs.layers:
            for enemy in layer:
                if not enemy.type.enemy:
                    continue
                if enemy.data.enemy.hitPoints <= 0:
                    continue

                enemy_rect = sdl3.SDL_FRect(
                    x=enemy.position.x + enemy.collider.x,
                    y=enemy.position.y + enemy.collider.y,
                    w=enemy.collider.w,
                    h=enemy.collider.h,
                )

                if sdl3.SDL_HasRectIntersectionFloat(player_rect, enemy_rect):
                    if obj.data.player.damage_cooldown <= 0:
                        obj.data.player.TakeDamage(10)
                        print(f"Player HP: {obj.data.player.hp}")
                        obj.data.player.damage_cooldown = 1.0  # Cooldown in seconds

                        if obj.data.player.hp <= 0 and obj.data.player.state != "dead":
                            obj.data.player.state = "dead"
                            obj.velocity = glm.vec2(0, 0)
                            print("Player has died!")
                            # Optional: trigger a game-over menu or flag instead of quitting

    # Handle grounded detection
    FoundGround = False
    ground_obj = None

    if obj.type.player:
        player_bottom = obj.position.y + obj.collider.y + obj.collider.h
        sensor = sdl3.SDL_FRect(
            x=obj.position.x + obj.collider.x,
            y=player_bottom + 1.0,
            w=obj.collider.w,
            h=1.0,
        )
    else:
        sensor = sdl3.SDL_FRect(
            x=obj.position.x + obj.collider.x,
            y=obj.position.y + obj.collider.y + obj.collider.h,
            w=obj.collider.w,
            h=1.0,
        )

    for layer in gs.layers:
        for objB in layer:
            if obj is objB:
                continue
            if not objB.type.level:
                continue

            rectB = sdl3.SDL_FRect(
                x=objB.position.x + objB.collider.x,
                y=objB.position.y + objB.collider.y,
                w=objB.collider.w,
                h=objB.collider.h,
            )
            
            if sdl3.SDL_HasRectIntersectionFloat(sensor, rectB):
                FoundGround = True
                ground_obj = objB
                break
        if FoundGround:
            break

    # Update grounded state
    if obj.grounded != FoundGround:
        obj.grounded = FoundGround
        if FoundGround and obj.type.player:
            obj.data.player.state = "running"
            obj.velocity.y = 0
            if ground_obj is not None:
                ground_top = ground_obj.position.y + ground_obj.collider.y
                player_bottom = obj.position.y + obj.collider.y + obj.collider.h
                if player_bottom <= ground_top + 1.0:
                    obj.position.y = ground_top - obj.collider.y - obj.collider.h
    
    # Handle enemy grounded state
    if obj.type.enemy:
        if FoundGround:
            obj.grounded = True
            obj.velocity.y = 0
            if ground_obj is not None:
                ground_top = ground_obj.position.y + ground_obj.collider.y
                obj_bottom = obj.position.y + obj.collider.y + obj.collider.h
                if obj_bottom <= ground_top + 1.0:
                    obj.position.y = ground_top - obj.collider.y - obj.collider.h
        else:
            obj.grounded = False
         
def collisionResponse(
    state: SDLstate,
    gs: Gamestate,
    res: Resources,
    rectA: SDL_FRect,
    rectB: SDL_FRect,
    rectC: SDL_FRect,
    objA: GameObject,
    objB: GameObject,
    deltaTime: float,
):
    """Handles collision resolution between two objects."""

    def generic_response():
        if rectC.w < rectC.h:
            # Horizontal collision
            if objA.velocity.x > 0:  # Going right
                objA.position.x -= rectC.w
            elif objA.velocity.x < 0:  # Going left
                objA.position.x += rectC.w
            objA.velocity.x = 0
        else:
            # Vertical collision
            if objA.velocity.y > 0:  # Going down
                objA.position.y -= rectC.h
                objA.velocity.y = 0
                if objA.type.player:
                    objA.grounded = True
            elif objA.velocity.y < 0:  # Going up
                objA.position.y += rectC.h
                objA.velocity.y = 0

    # Object we are checking
    if objA.type.player:
        if objB.type.level:  # Both ground and panels are level objects
            generic_response()
        if objB.type.enemy:
            if objB.data.enemy.state != "dead":
                objA.velocity = glm.vec2(100, 0) * -objA.direction
    elif objA.type.bullet:
        if objB.type.level:
            objA.data.bullet.moving = False
            objA.data.bullet.colliding = True
            objA.currentAnimation = res.ANIM_BULLET_HIT
            objA.texture = res.texBulletHit
            play_sound(res.chunkWallHit)
        elif objB.type.enemy:
            if not objB.data.enemy.state == "dead":
                # Bullet hit enemy
                objA.data.bullet.moving = False
                objA.data.bullet.colliding = True
                objA.currentAnimation = res.ANIM_BULLET_HIT
                objA.texture = res.texBulletHit
                # Change enemy state, apply damage, and flash
                objB.data.enemy.state = "damage"
                objB.data.enemy.hitPoints -= 1
                objB.direction = -objA.direction
                objB.shouldFlash = True
                objB.flashTimer.reset()
                objB.texture = res.texEnemyHit
                objB.currentAnimation = res.ANIM_ENEMY_HIT
                play_sound(res.chunkEnemyHit)

                if objB.data.enemy.hitPoints <= 0:
                    objB.data.enemy.state = "dead"
                    objB.texture = res.texEnemyDie
                    objB.currentAnimation = res.ANIM_ENEMY_DIE
                    play_sound(res.chunkEnemyDie)


def checkcollision(
    state: SDLstate,
    gs: Gamestate,
    res: Resources,
    a: GameObject,
    b: GameObject,
    deltaTime: float,
):
    # Skip collision if object is a dead enemy
    if (
        a.type.enemy
        and (a.data.enemy.state == "dead" or a.data.enemy.state == "removed")
    ) or (
        b.type.enemy
        and (b.data.enemy.state == "dead" or b.data.enemy.state == "removed")
    ):
        return
    rectA = SDL_FRect(
        x=a.position.x + a.collider.x,
        y=a.position.y + a.collider.y,
        w=a.collider.w,
        h=a.collider.h,
    )
    rectB = SDL_FRect(
        x=b.position.x + b.collider.x,
        y=b.position.y + b.collider.y,
        w=b.collider.w,
        h=b.collider.h,
    )
    rectC = SDL_FRect(0)
    if sdl3.SDL_GetRectIntersectionFloat(rectA, rectB, rectC):
        # found intersection,respond
        collisionResponse(state, gs, res, rectA, rectB, rectC, a, b, deltaTime)
        # Bullet collision with level objects
        if a.type.bullet and b.type.level and a.data.bullet.moving:
            a.data.bullet.moving = False
            a.data.bullet.inactive = True

def generateLevelChunk(gs: Gamestate, state: SDLstate, res: Resources, start_x: int, spawn_player: bool = False):
    """Generates a random level chunk starting at start_x"""
    chunk_width = 20  # Width in tiles
    rows, cols = res.MAP_ROWS, chunk_width
    
    # Create empty chunk arrays
    tile_map = np.zeros((rows, cols), dtype=int)
    foreground = np.zeros((rows, cols), dtype=int)
    background = np.zeros((rows, cols), dtype=int)
    
    # Always have ground at the bottom
    tile_map[4, :] = 1
    if spawn_player:
        tile_map[3, 1] = 4
    # Generate platforms
    platform_types = [
        (1, 4, 6),   # (row, min_length, max_length)
        (2, 3, 5),
        (3, 2, 4)
    ]
    
    x_pos = 0
    while x_pos < cols:
        # Randomly decide if we place a platform
        if random.random() < 0.7 and x_pos < cols - 3:  # 70% chance to place platform
            platform_type = random.choice(platform_types)
            row, min_len, max_len = platform_type
            length = random.randint(min_len, max_len)
            
            # Make sure platform fits
            if x_pos + length >= cols:
                length = cols - x_pos - 1
                
            # Place the platform
            tile_map[row, x_pos:x_pos+length] = 2
            
            # Maybe add an enemy on the platform
            if random.random() < 0.4 and length > 2:  # 40% chance
                enemy_pos = x_pos + random.randint(1, length-1)
                tile_map[row-1, enemy_pos] = 3  # Enemy on platform
            
            x_pos += length + random.randint(1, 3)  # Skip some space
        else:
            x_pos += 1
            
    # Add decorative elements
    for x in range(cols):
        # Add some grass on ground
        if random.random() < 0.2 and tile_map[3, x] == 0:  # 20% chance
            foreground[3, x] = 5
            
        # Add some background bricks
        if random.random() < 0.1 and x % 2 == 0:  # 10% chance
            background[random.randint(0, 2), x] = 6
    
    # Convert tile positions to actual game objects
    def createObject(r, c, tex, obj_type, x_offset=0):
        o = GameObject()
        o.type = obj_type
        o.position = glm.vec2(
            start_x + c * Resources.TILE_SIZE,
            state.logicalh - (Resources.MAP_ROWS - r) * Resources.TILE_SIZE,
        )
        o.texture = tex
        o.collider = SDL_FRect(x=0, y=0, w=Resources.TILE_SIZE, h=Resources.TILE_SIZE)
        return o

    # Create objects from the generated chunk
    for r in range(rows):
        for c in range(cols):
            tile = tile_map[r][c]
            if tile == 1:  # ground - SOLID
                gs.layers[LAYER_IDX_LEVEL].append(
                    createObject(r, c, Resources.texGround, ObjectType(level=True))
                )
            elif tile == 2:  # panel - SOLID
                gs.layers[LAYER_IDX_LEVEL].append(
                    createObject(r, c, Resources.texPanel, ObjectType(level=True))
                )
            elif tile == 3:  # enemy
                o = GameObject()
                o.type = ObjectType(enemy=True)
                o.position = glm.vec2(
                    start_x + c * Resources.TILE_SIZE,
                    state.logicalh - (Resources.MAP_ROWS - r) * Resources.TILE_SIZE,
                )
                o.texture = Resources.texEnemy
                o.data.enemy.state = "shambling"
                o.maxSpeedX = 15
                o.dynamic = True
                o.animations = Resources.enemyAnims
                o.collider = SDL_FRect(x=10, y=4, w=12, h=20)
                o.data.enemy.hitPoints = 30
                gs.layers[LAYER_IDX_CHARACTERS].append(o)
            elif tile == 4:  # player 
                if gs.player is None:
                    player = GameObject()
                    player.type = ObjectType(player=True)
                    player.position = glm.vec2(
                        start_x + c * Resources.TILE_SIZE,
                        state.logicalh - (Resources.MAP_ROWS - r) * Resources.TILE_SIZE,
                    )
                    player.texture = Resources.texIdle
                    player.animations = Resources.playerAnims
                    player.currentAnimation = Resources.ANIM_PLAYER_IDLE
                    player.acceleration = glm.vec2(300, 0)
                    player.maxSpeedX = 100
                    player.dynamic = True
                    player.collider = SDL_FRect(x=11, y=6, w=10, h=26)
                    gs.player = player
                    gs.layers[LAYER_IDX_CHARACTERS].append(player)
                    gs.playerIndex = len(gs.layers[LAYER_IDX_CHARACTERS]) - 1
    
    # Add decorative tiles
    for r in range(rows):
        for c in range(cols):
            tile = foreground[r][c]
            if tile == 5:  # grass - decoration
                o = createObject(r, c, Resources.texGrass, ObjectType(level=False))
                gs.foregroundTiles.append(o)
                
            tile = background[r][c]
            if tile == 6:  # bricks - decoration
                o = createObject(r, c, Resources.texBrick, ObjectType(level=False))
                gs.backgroundTiles.append(o)
    
    # Update the last chunk position
    gs.last_chunk_end = start_x + cols * Resources.TILE_SIZE
    gs.generated_chunks += 1
   
def handleKeyInputs(
    state: SDLstate, gs: Gamestate, obj: GameObject, key: sdl3.SDL_Scancode, keydown
):
    JUMP_FORCE: float = -200.0

    if obj.type.player:
        player_state = obj.data.player

        if key == sdl3.SDL_SCANCODE_K and keydown:
            if obj.grounded and player_state.state != "jumping":
                # Start jumping
                player_state.state = "jumping"
                obj.velocity.y = JUMP_FORCE
                # Use running texture for jump animation
                obj.texture = Resources.texRun
                obj.currentAnimation = Resources.ANIM_PLAYER_RUN


sdl3.SDL_GetTextureSize.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
]
sdl3.SDL_GetTextureSize.restype = None


def get_texture_size(texture: SDL_Texture):
    if not texture:
        raise ValueError("Texture is NULL or invalid!")

    w = ctypes.c_float()
    h = ctypes.c_float()
    sdl3.SDL_GetTextureSize(texture, ctypes.byref(w), ctypes.byref(h))
    return w.value, h.value


def drawParalaxBackground(
    renderer: SDL_Renderer,
    texture: SDL_Texture,
    xVelocity: float,
    scrollposition: float,
    scrollFactor: float,
    deltaTime: float,
):
    # get width/height once per call
    texture_w, texture_h = get_texture_size(texture)

    # update scroll
    scrollposition -= xVelocity * scrollFactor * deltaTime
    # wrap-around behavior: keep in range [-texture_w, 0]
    if scrollposition <= -texture_w:
        scrollposition += texture_w
    if scrollposition >= texture_w:
        scrollposition -= texture_w

    # draw first copy
    dst = SDL_FRect(x=scrollposition, y=30, w=float(texture_w), h=float(texture_h))
    sdl3.SDL_RenderTexture(renderer, texture, None, dst)
    # draw second copy (tile horizontally)
    dst2 = SDL_FRect(
        x=scrollposition + float(texture_w),
        y=30,
        w=float(texture_w),
        h=float(texture_h),
    )
    sdl3.SDL_RenderTexture(renderer, texture, None, dst2)

    # return updated scroll so caller can store it
    return scrollposition
def cleanupDistantObjects(gs: Gamestate, min_x: float):
    """Remove objects that are far behind the player to save memory"""
    # Clean up level objects
    for layer in gs.layers:
        i = 0
        while i < len(layer):
            obj = layer[i]
            if obj.position.x + obj.collider.w < min_x:
                layer.pop(i)
            else:
                i += 1
                
    # Clean up background tiles
    i = 0
    while i < len(gs.backgroundTiles):
        obj = gs.backgroundTiles[i]
        if obj.position.x + Resources.TILE_SIZE < min_x:
            gs.backgroundTiles.pop(i)
        else:
            i += 1
            
    # Clean up foreground tiles
    i = 0
    while i < len(gs.foregroundTiles):
        obj = gs.foregroundTiles[i]
        if obj.position.x + Resources.TILE_SIZE < min_x:
            gs.foregroundTiles.pop(i)
        else:
            i += 1

def drawHealthBar(state: SDLstate, gs: Gamestate, obj: GameObject, is_player: bool = False):
    """Draws a health bar above an object with color coding"""
    if not obj or not hasattr(obj, 'data'):
        return
    
    # Get health information based on object type
    if is_player and hasattr(obj.data, 'player'):
        current_hp = obj.data.player.hp
        max_hp = 100  # Player max HP
    elif hasattr(obj.data, 'enemy'):
        current_hp = obj.data.enemy.hitPoints
        max_hp = 30   # Enemy max HP
    else:
        return
    
    # Don't draw full health bars or for dead entities
    if current_hp >= max_hp or current_hp <= 0:
        return
    
    # Calculate health bar dimensions
    bar_width = obj.collider.w
    bar_height = 4
    health_percentage = current_hp / max_hp
    
    # Calculate position (above the object)
    bar_x = obj.position.x + obj.collider.x - gs.mapViewport.x
    bar_y = obj.position.y + obj.collider.y - 8  # 8 pixels above the object
    
    # Draw background (red)
    bg_rect = SDL_FRect(x=bar_x, y=bar_y, w=bar_width, h=bar_height)
    sdl3.SDL_SetRenderDrawColor(state.renderer, 255, 0, 0, 255)
    sdl3.SDL_RenderFillRect(state.renderer, bg_rect)
    
    # Determine health bar color based on percentage
    if health_percentage > 0.6:
        color = (0, 255, 0)  # Green for high health
    elif health_percentage > 0.3:
        color = (255, 165, 0)  # Orange for medium health
    else:
        color = (255, 0, 0)  # Red for low health
    
    # Draw health
    health_width = bar_width * health_percentage
    health_rect = SDL_FRect(x=bar_x, y=bar_y, w=health_width, h=bar_height)
    sdl3.SDL_SetRenderDrawColor(state.renderer, color[0], color[1], color[2], 255)
    sdl3.SDL_RenderFillRect(state.renderer, health_rect)
    
    # Draw border
    sdl3.SDL_SetRenderDrawColor(state.renderer, 0, 0, 0, 255)
    sdl3.SDL_RenderRect(state.renderer, bg_rect)

def drawPlayerHealthBar(state: SDLstate, gs: Gamestate):
    """Draws a permanent health bar at the top of the screen for the player"""
    if not gs.player or not hasattr(gs.player.data, 'player'):
        return
    
    current_hp = gs.player.data.player.hp
    max_hp = 100
    
    # Health bar dimensions and position
    bar_width = 200
    bar_height = 20
    bar_x = 20
    bar_y = 20
    health_percentage = current_hp / max_hp
    
    # Draw background
    bg_rect = SDL_FRect(x=bar_x, y=bar_y, w=bar_width, h=bar_height)
    sdl3.SDL_SetRenderDrawColor(state.renderer, 50, 50, 50, 255)
    sdl3.SDL_RenderFillRect(state.renderer, bg_rect)
    
    # Draw health with color coding
    health_width = bar_width * health_percentage
    health_rect = SDL_FRect(x=bar_x, y=bar_y, w=health_width, h=bar_height)
    
    if health_percentage > 0.6:
        color = (0, 255, 0)  # Green
    elif health_percentage > 0.3:
        color = (255, 165, 0)  # Orange
    else:
        color = (255, 0, 0)  # Red
    
    sdl3.SDL_SetRenderDrawColor(state.renderer, color[0], color[1], color[2], 255)
    sdl3.SDL_RenderFillRect(state.renderer, health_rect)
    
    # Draw border and text
    sdl3.SDL_SetRenderDrawColor(state.renderer, 255, 255, 255, 255)
    sdl3.SDL_RenderRect(state.renderer, bg_rect)
    
    # Draw HP text
    hp_text = f"HP: {current_hp}/{max_hp}"
    sdl3.SDL_RenderDebugTextFormat(state.renderer, bar_x + 5, bar_y + 5, hp_text.encode("utf-8"))

# memory leaks might be real or can be stable not growing


# --- Run the game ---
if __name__ == "__main__":
    # tracemalloc.start()  # Start tracking memory
    # snapshot1 = tracemalloc.take_snapshot()  # Take first snapshot

    window_creation()  # Run the game

    # snapshot2 = tracemalloc.take_snapshot()  # Take second snapshot after game

    # top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    # for stat in top_stats[:10]:
    #     print(stat)
