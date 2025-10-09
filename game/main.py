# ------------------------------Imports------------------------------

import os, sys, json, time, argparse, glob
import pygame as pg

# ------------------------------Basic Info------------------------------

# "os" interact with computer files;
# "sys" talk to Python system itself;
# "json" work with Python and JSON files;
# "time" measure and keep track of time;
# "argparse" read arguments written in terminal;
# "glob" search for files that match given pattern;
# "pygame" run game window, draw graphics, and read input - "pg" for short

# M - Module; F - Function; V - Variable
# "def wasd():" F to create F "wasd()"
# "try ... except Exception:" F to run code but in case of an error ["Exception" - general name for errors] it does the "except" part, not crash
# "pass" if try fails, ignores it and jumps to the next command
# "with ... as x" F to create a V "x" to hold the result of what is in [...] and after the end of the block releas the V
# ".." = folder 1 level up

# speed mostly in pixels per second, accseleration in  pixels per second^2, time in seconds

# ------------------------------Config------------------------------

# Graphics
TILE = 16                       # size of one map tile (pixels)
SCREEN_W, SCREEN_H = 480, 270   # internal resolution of game window (pixels)
BG_COLOR = (18, 20, 28)
WALL_COLOR = (70, 80, 100)
NONHANG_WALL_COLOR = (150, 90, 90)  #boundary walls
SPIKE_COLOR = (210, 80, 80)
EXIT_COLOR = (120, 200, 120)
NPC_COLOR = (230, 210, 120)
PLAYER_COLOR = (240, 240, 255)

# Movement
MOVE_ACC = 900
MOVE_DECAY_GROUND = 8.0       # multiplier
MOVE_DECAY_AIR = 2.0          # multiplier
MAX_SPD_X = 150
GRAVITY = 600
JUMP_VEL = -250               # jump starting velocity (negative = up)
COYOTE_TIME = 0.12            # time for jump after leaving ground
MAX_FALL_SPEED = 400
MAX_RISE_SPEED = -300

# Climb
STAMINA_MAX = 5.0
CLIMB_SPEED = 80
ALLOW_EDGE_GRAB = False       # grabbing boundary walls

# Dash
DASH_SPEED = 450
DASH_TIME = 0.105
DASH_COOLDOWN = 0.6
MAX_DASHES = 1

# Camera
CAM_LERP = 0.12               # how quickly camera follows player (0–1, fraction per frame)

# ------------------------------Files------------------------------
 
# ".path" M in "os" to work with paths;
# ".join" F in "path" to connect paths in right order: [os.path.join("C:\\Users", "You", "Desktop", "file.txt") - > (C:\Users\You\Desktop\file.txt)];
# .dirname() F to give the path of a file;
STATS_PATH = os.path.join(os.path.dirname(__file__), "..", "stats.json")
LEVELS_DIR = os.path.join(os.path.dirname(__file__), "..", "levels")

# ------------------------------Helpers------------------------------

# sets allowed range to V
def clamp(v, lo, hi): 
    return lo if v < lo else hi if v > hi else v

# "rect" F in "pg" to create a rectangle object [x from 0; y from 0; width; height] top-left corner in pixels (because of *TILE)
def rect_from_tile(tx, ty):
    return pg.Rect(tx*TILE, ty*TILE, TILE, TILE)

# detects which tiles could be overlapped depending on rect position
# x0 is left pixel of rect floor-divided by tile size to get tile index; -1 expands search for safety
# returns list of (x, y) pairs [tile coordinates] to be checked for collisions
def tiles_overlapping(rect):
    x0 = int(rect.left // TILE) - 1
    y0 = int(rect.top // TILE) - 1
    x1 = int(rect.right // TILE) + 1    
    y1 = int(rect.bottom // TILE) + 1
    return [(x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)]

# gives a number between a and b depending on t in range from 0 to 1 [10 + (20 - 10) * 0,3 = 13 —> 30% of the way from 10 to 20]
# used for smooth camera following 
def lerp(a, b, t): return a + (b - a) * t

# open()" F to open a file [on "STATS_PATH" path, to "r" read in "encoding" format "utf-8"];
# ".load" F in "json" to read JSON and return Python dictionary;
# "return" F to send a V to F that called it [(def wasd(a, b): return a + b) so if (x = wasd 2 + 3) then (x = 5)]
def load_stats():
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
    
# ".dump" F in "json" to write Python data in JSON format [writes "stats" text over "f" file with parting lines and "2" spaces before branches]
def save_stats(stats):
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception:
        pass

# ------------------------------Input------------------------------

KEY = {
    "left":  [pg.K_a],
    "right": [pg.K_d],
    "up":    [pg.K_w],
    "down":  [pg.K_s],
    "jump":  [pg.K_j],
    "dash":  [pg.K_k],
    "grab":  [pg.K_l],

    # optional secondary (arrow + z/x/c)
    "left_alt":  [pg.K_LEFT],  "right_alt": [pg.K_RIGHT],
    "up_alt":    [pg.K_UP],    "down_alt":  [pg.K_DOWN],
    "jump_alt":  [pg.K_c],     "dash_alt":  [pg.K_x],
    "grab_alt":  [pg.K_z],
    "confirm":   [pg.K_RETURN, pg.K_SPACE],
    "back":      [pg.K_ESCAPE],
}

def is_pressed(keys, names):
    for n in names:
        for k in KEY.get(n, []):
            if keys[k]: return True
    return False

# ------------------------------Level------------------------------

class Level:
    def __init__(self, lines):
        self.lines = lines
        self.h = len(lines)
        self.w = max(len(l) for l in lines)
        self.walls = set()
        self.boundary = set()
        self.spikes = set()
        self.npcs = set()
        self.exit = None
        self.spawn = (2*TILE, 2*TILE)
        self._parse()

    def _parse(self):
        for y, row in enumerate(self.lines):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((x, y))
                elif ch == "^":
                    self.spikes.add((x, y))
                elif ch == "S":
                    self.spawn = (x*TILE, y*TILE)
                elif ch == "E":
                    self.exit = (x*TILE, y*TILE)
                elif ch == "N":
                    self.npcs.add((x, y))

        # boundary columns considered "visible walls" (if present)
        for y in range(self.h):
            if (0, y) in self.walls: self.boundary.add((0, y))
            if (self.w-1, y) in self.walls: self.boundary.add((self.w-1, y))

    @classmethod
    def from_file(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f.readlines()]
        return cls(lines)

    def death_y(self):
        return self.h * TILE + 8  # a bit below the bottom

# ------------------------------Player------------------------------

class Player:
    def __init__(self, pos):
        self.size = pg.Vector2(12, 14)
        self.pos = pg.Vector2(pos)
        self.vel = pg.Vector2(0, 0)
        self.on_ground = False
        self.facing = 1
        self.coyote = 0.0
        
        # grabbing
        self.grabbing = False
        self.stamina = STAMINA_MAX

        # dash
        self.dashing = False
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.dashes_left = MAX_DASHES

        # meta
        self.spawn = pg.Vector2(pos)
        self.dead = False
        self.win = False

    @property
    def rect(self):
        return pg.Rect(int(self.pos.x), int(self.pos.y), int(self.size.x), int(self.size.y))

    def kill_and_respawn(self, level):
        self.pos.update(level.spawn)
        self.vel.update(0, 0)
        self.on_ground = False
        self.grabbing = False
        self.stamina = STAMINA_MAX
        self.dashing = False
        self.dash_t = 0
        self.dash_cd = 0
        self.dashes_left = MAX_DASHES
        self.dead = False
        self.win = False

    def touching_wall_side(self, level):
        r = self.rect
        # Expand a tiny bit left/right to detect adjacency
        left_probe = r.move(-1, 0)
        right_probe = r.move(1, 0)
        touching_left = touching_right = None
        for tx, ty in tiles_overlapping(left_probe):
            if (tx, ty) in level.walls and left_probe.colliderect(rect_from_tile(tx,ty)):
                touching_left = (tx, ty)
                break
        for tx, ty in tiles_overlapping(right_probe):
            if (tx, ty) in level.walls and right_probe.colliderect(rect_from_tile(tx,ty)):
                touching_right = (tx, ty)
                break
        return touching_left, touching_right


    def update(self, dt, level, keys):
        # ---- timers ----
        self.coyote = max(0.0, self.coyote - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)

        # ---- input axes ----
        x_axis = (1 if is_pressed(keys, ["right","right_alt"]) else 0) - (1 if is_pressed(keys, ["left","left_alt"]) else 0)
        y_up   = (1 if is_pressed(keys, ["up","up_alt"]) else 0)
        y_down = (1 if is_pressed(keys, ["down","down_alt"]) else 0)
        if x_axis != 0:
            self.facing = x_axis

        # ---- grab key ----
        grab_held = is_pressed(keys, ["grab","grab_alt"])

        # ---- dash start (direction from WASD only; no diagonals; horizontal priority) ----
        if is_pressed(keys, ["dash","dash_alt"]) and not self.dashing and self.dash_cd == 0 and self.dashes_left > 0:
            dx = (1 if is_pressed(keys, ["right","right_alt"]) else 0) - (1 if is_pressed(keys, ["left","left_alt"]) else 0)
            dy = (1 if is_pressed(keys, ["down","down_alt"]) else 0) - (1 if is_pressed(keys, ["up","up_alt"]) else 0)
            # cancel opposites
            if (is_pressed(keys, ["left","left_alt"]) and is_pressed(keys, ["right","right_alt"])): dx = 0
            if (is_pressed(keys, ["up","up_alt"]) and is_pressed(keys, ["down","down_alt"])): dy = 0
            # forbid diagonals: prefer horizontal
            if dx != 0 and dy != 0:
                dy = 0
            if dx != 0 or dy != 0:
                v = pg.Vector2(dx, dy)
                self.dashing = True
                self.dash_t = DASH_TIME
                self.dash_cd = DASH_COOLDOWN
                self.vel = v * DASH_SPEED
                self.dashes_left -= 1

        # ---- dash tick ----
        if self.dashing:
            self.dash_t -= dt
            if self.dash_t <= 0:
                self.dashing = False
                self.vel = pg.Vector2(0, 0)   # stop after dash, all directions equal


        # ---- touching walls (for grab logic) ----
        left_tile, right_tile = self.touching_wall_side(level)
        can_grab_left  = (left_tile  is not None) and (left_tile  not in level.boundary or not ALLOW_EDGE_GRAB) and (left_tile  not in level.spikes)
        can_grab_right = (right_tile is not None) and (right_tile not in level.boundary or not ALLOW_EDGE_GRAB) and (right_tile not in level.spikes)

        want_grab = grab_held and (can_grab_left or can_grab_right) and self.stamina > 0 and not self.on_ground

        if want_grab:
            self.grabbing = True
            self.vel.x = 0
            self.vel.y = 0
            # stick to the wall
            if can_grab_left:
                self.facing = -1
                self.pos.x = rect_from_tile(*left_tile).right
            elif can_grab_right:
                self.facing = 1
                self.pos.x = rect_from_tile(*right_tile).left - self.size.x

            # climb using collision-safe movement
            if y_up:
                self.move_and_collide(0, -CLIMB_SPEED * dt, level)
            if y_down:
                self.move_and_collide(0,  CLIMB_SPEED * dt, level)

            # stamina drain while holding
            self.stamina = max(0.0, self.stamina - dt)

            # wall jump while grabbing: C/JUMP + (W/A/D). No S.
            if is_pressed(keys, ["jump","jump_alt"]):
                dir_x = (1 if is_pressed(keys, ["right","right_alt"]) else 0) - (1 if is_pressed(keys, ["left","left_alt"]) else 0)
                dir_up = (1 if is_pressed(keys, ["up","up_alt"]) else 0)
                if dir_x != 0 or dir_up:
                    v = pg.Vector2(dir_x, -1 if dir_up else 0)
                    if v.length_squared() > 0:
                        v = v.normalize()
                        self.vel = v * 300  # tuned wall-jump speed
                        self.grabbing = False
        else:
            self.grabbing = False

        # ---- horizontal movement (disabled while dashing or actively grabbing) ----
        if not self.dashing and not (self.grabbing and grab_held):
            ax = MOVE_ACC * x_axis
            self.vel.x += ax * dt
            decay = MOVE_DECAY_GROUND if self.on_ground else MOVE_DECAY_AIR
            self.vel.x -= self.vel.x * decay * dt
            self.vel.x = clamp(self.vel.x, -MAX_SPD_X, MAX_SPD_X)

        # ---- gravity (disabled during dash; held at 0 while grabbing) ----
        if not self.dashing:
            if not (self.grabbing and grab_held):
                self.vel.y += GRAVITY * dt
            else:
                self.vel.y = 0

        self.vel.y = clamp(self.vel.y, MAX_RISE_SPEED, MAX_FALL_SPEED)


        # ---- ground jump (no buffer) ----
        if is_pressed(keys, ["jump","jump_alt"]) and self.coyote > 0:
            self.vel.y = JUMP_VEL
            self.on_ground = False
            self.coyote = 0.0

        # ---- integrate & collide ----
        self.move_and_collide(self.vel.x * dt, 0, level)
        self.move_and_collide(0, self.vel.y * dt, level)

        # ---- ground reset & dash refill ----
        if self.on_ground:
            self.stamina = STAMINA_MAX
            self.dashes_left = MAX_DASHES

        # ---- death/reset & win ----
        if self.pos.y > level.death_y():
            self.dead = True
            return
        if level.exit is not None:
            er = pg.Rect(level.exit[0], level.exit[1], TILE, TILE)
            if self.rect.colliderect(er):
                self.win = True
    def move_and_collide(self, dx, dy, level):
        if dx == 0 and dy == 0: return
        self.pos.x += dx
        self.pos.y += dy
        r = self.rect
        if dy != 0: self.on_ground = False

        # Walls
        for tx, ty in tiles_overlapping(r):
            if (tx, ty) in level.walls:
                tile = rect_from_tile(tx, ty)
                if r.colliderect(tile):
                    if dx > 0:
                        self.pos.x = tile.left - self.size.x
                        self.vel.x = 0
                    if dx < 0:
                        self.pos.x = tile.right
                        self.vel.x = 0
                    if dy > 0:
                        self.pos.y = tile.top - self.size.y
                        self.vel.y = 0
                        self.on_ground = True
                        self.coyote = COYOTE_TIME
                    if dy < 0:
                        self.pos.y = tile.bottom
                        self.vel.y = 0

        # Spikes kill
        for tx, ty in tiles_overlapping(r):
            if (tx, ty) in level.spikes:
                if self.rect.colliderect(rect_from_tile(tx, ty)):
                    self.dead = True
                    return

# ------------------------------Drawing------------------------------

def draw_parallax(surface, cam):
    w, h = surface.get_size()
    surface.fill(BG_COLOR)
    # Far sky gradient bands
    for i in range(8):
        alpha = int(255 * (i/8)*0.15)
        color = (30+i*2, 34+i*2, 50+i*3)
        pg.draw.rect(surface, color, pg.Rect(0, int(h*(i/8)), w, int(h/8)))
    # Far mountains
    for i in range(-3, 4):
        base_x = i * 320 - int(cam.x * 0.25) % 320
        pg.draw.polygon(surface, (35, 45, 64),
                        [(base_x, h), (base_x+160, h-90), (base_x+320, h)])
    # Near hills
    for i in range(-3, 4):
        base_x = i * 260 - int(cam.x * 0.5) % 260
        pg.draw.ellipse(surface, (46, 56, 78), pg.Rect(base_x, h-70, 320, 120))

def draw_level(surf, level, cam):
    # walls
    for (tx, ty) in level.walls:
        col = NONHANG_WALL_COLOR if (tx, ty) in level.boundary else WALL_COLOR
        pg.draw.rect(surf, col, pg.Rect(tx*TILE - cam.x, ty*TILE - cam.y, TILE, TILE))
    # spikes
    for (tx, ty) in level.spikes:
        r = pg.Rect(tx*TILE - cam.x, ty*TILE - cam.y, TILE, TILE)
        pg.draw.polygon(surf, SPIKE_COLOR, [(r.left, r.bottom), (r.centerx, r.top), (r.right, r.bottom)])
    # exit
    if level.exit is not None:
        er = pg.Rect(level.exit[0]-cam.x, level.exit[1]-cam.y, TILE, TILE)
        pg.draw.rect(surf, EXIT_COLOR, er)
    # NPCs
    for (tx, ty) in level.npcs:
        pg.draw.rect(surf, NPC_COLOR, pg.Rect(tx*TILE - cam.x + 2, ty*TILE - cam.y + 2, TILE-4, TILE-4))

def draw_player(surf, player, cam, t):
    r = player.rect.move(-cam.x, -cam.y)
    # dash trail
    if player.dashing and int(t*30)%2==0:
        pg.draw.rect(surf, (180,180,220), r.inflate(4,4), border_radius=4)
    color = PLAYER_COLOR
    pg.draw.rect(surf, color, r, border_radius=3)
    # stamina bar (small)
    bar_w = 40
    filled = int(bar_w * (player.stamina / STAMINA_MAX))
    pg.draw.rect(surf, (40,40,50), pg.Rect(6, 22, bar_w, 6), border_radius=2)
    pg.draw.rect(surf, (120,220,220), pg.Rect(6, 22, filled, 6), border_radius=2)

# ------------------------------UI helpers------------------------------

def draw_text_left(surface, text, x, y, font, color=(230,230,240)):
    surf = font.render(text, True, color)
    surface.blit(surf, (x, y))

def draw_text_center(surface, text, cx, y, font, color=(230,230,240)):
    surf = font.render(text, True, color)
    surface.blit(surf, (cx - surf.get_width()//2, y))

# ------------------------------Game loop / stats------------------------------

class Game:
    def __init__(self, args):
        pg.init()
        pg.display.set_caption("Celest-ish Homework")
        self.window = pg.display.set_mode((SCREEN_W*args.scale, SCREEN_H*args.scale))
        self.screen = pg.Surface((SCREEN_W, SCREEN_H))
        self.clock = pg.time.Clock()
        self.font = pg.font.SysFont("consolas", 14)

        self.level_paths = sorted(glob.glob(os.path.join(LEVELS_DIR, "*.txt")))
        if not self.level_paths:
            raise SystemExit("No levels found in 'levels/'")

        self.stats = load_stats()
        self.state = "MENU"  # MENU -> LEVEL_SELECT -> PLAYING -> POST
        self.menu_idx = 0
        self.level_idx = 0

        self.level = None
        self.player = None
        self.cam = pg.Vector2(0, 0)

        self.deaths = 0
        self.level_start_time = None
        self.level_time = 0
        self.t = 0.0

        self.npc_message = ""  # for simple NPC dialog
        self.npc_timer = 0.0

    def start_level(self, idx):
        self.level_idx = idx
        self.level = Level.from_file(self.level_paths[idx])
        self.player = Player(self.level.spawn)
        self.deaths = 0
        self.level_start_time = time.time()
        self.level_time = 0
        self.cam.update(0,0)

    def run(self):
        running = True
        while running:
            dt = min(1/30, self.clock.tick(60)/1000.0)  # clamp
            self.t += dt
            keys = pg.key.get_pressed()

            for e in pg.event.get():
                if e.type == pg.QUIT:
                    running = False
                if e.type == pg.KEYDOWN:
                    if e.key in KEY["back"] and self.state in ("MENU","LEVEL_SELECT"):
                        running = False
                    if self.state == "MENU":
                        if e.key in KEY["confirm"]:
                            if self.menu_idx == 0: self.state = "LEVEL_SELECT"
                            else: running = False
                        elif e.key == pg.K_UP or e.key == pg.K_w:
                            self.menu_idx = (self.menu_idx - 1) % 2
                        elif e.key == pg.K_DOWN or e.key == pg.K_s:
                            self.menu_idx = (self.menu_idx + 1) % 2
                    elif self.state == "LEVEL_SELECT":
                        if e.key in KEY["back"]:
                            self.state = "MENU"
                        elif e.key in KEY["confirm"]:
                            self.start_level(self.level_idx)
                            self.state = "PLAYING"
                        elif e.key == pg.K_LEFT or e.key == pg.K_a:
                            self.level_idx = (self.level_idx - 1) % len(self.level_paths)
                        elif e.key == pg.K_RIGHT or e.key == pg.K_d:
                            self.level_idx = (self.level_idx + 1) % len(self.level_paths)
                        elif e.key in (pg.K_1, pg.K_2, pg.K_3, pg.K_4, pg.K_5):
                            n = e.key - pg.K_1
                            if n < len(self.level_paths):
                                self.level_idx = n
                    elif self.state == "PLAYING":
                        if e.key in KEY["back"]:
                            # restart level on ESC
                            self.start_level(self.level_idx)
                        if e.key == pg.K_e:
                            # interact with NPC if close
                            if self.close_to_npc():
                                self.trigger_npc_dialog()
                    elif self.state == "POST":
                        if e.key in KEY["confirm"]:
                            # Next or Exit
                            next_idx = self.level_idx + 1
                            if next_idx < len(self.level_paths):
                                self.start_level(next_idx)
                                self.state = "PLAYING"
                            else:
                                self.state = "MENU"
                        elif e.key in KEY["back"]:
                            self.state = "MENU"

            # Update states
            if self.state == "PLAYING":
                self.player.update(dt, self.level, keys)
                if self.player.dead:
                    self.deaths += 1
                    self.player.kill_and_respawn(self.level)
                if self.player.win:
                    self.level_time = time.time() - self.level_start_time
                    self.update_stats()
                    self.state = "POST"

                # Camera follow
                target = pg.Vector2(self.player.pos.x + self.player.size.x/2 - SCREEN_W/2,
                                    self.player.pos.y + self.player.size.y/2 - SCREEN_H/2)
                self.cam.x = lerp(self.cam.x, target.x, CAM_LERP)
                self.cam.y = lerp(self.cam.y, target.y, CAM_LERP)

                # NPC message timer
                if self.npc_timer > 0:
                    self.npc_timer -= dt
                    if self.npc_timer <= 0: self.npc_message = ""

            # Draw
            self.screen.fill((0,0,0))
            if self.state in ("PLAYING","POST"):
                draw_parallax(self.screen, self.cam)
                draw_level(self.screen, self.level, self.cam)
                draw_player(self.screen, self.player, self.cam, self.t)
                # HUD
                elapsed = int(time.time() - self.level_start_time) if self.state=="PLAYING" else int(self.level_time)
                draw_text_left(self.screen, f"Time {elapsed:>3}s   Deaths {self.deaths}", 6, 6, self.font)
                # NPC prompt
                if self.close_to_npc():
                    draw_text_left(self.screen, "Press E to talk", 6, SCREEN_H-20, self.font, (220,220,180))
                if self.npc_message:
                    self.draw_dialog(self.npc_message)

            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "LEVEL_SELECT":
                self.draw_level_select()
            elif self.state == "POST":
                self.draw_post()

            # Present upscale
            pg.transform.scale(self.screen, self.window.get_size(), self.window)
            pg.display.flip()

        save_stats(self.stats)
        pg.quit()

    # ---- UI renderers ----
    def draw_menu(self):
        draw_parallax(self.screen, self.cam)
        draw_text_center(self.screen, "Celest-ish Homework", SCREEN_W//2, 40, self.font, (255,255,255))
        opts = ["Play", "Exit"]
        for i, opt in enumerate(opts):
            color = (255,255,255) if i==self.menu_idx else (180,180,190)
            draw_text_center(self.screen, ("> " if i==self.menu_idx else "  ")+opt, SCREEN_W//2, 90 + i*20, self.font, color)
        draw_text_center(self.screen, "Enter = select, Esc = quit", SCREEN_W//2, SCREEN_H-22, self.font, (170,170,180))

    def draw_level_select(self):
        draw_parallax(self.screen, self.cam)
        draw_text_center(self.screen, "Select Level", SCREEN_W//2, 40, self.font, (255,255,255))
        # show list horizontally
        x0 = SCREEN_W//2 - (len(self.level_paths)*40)//2
        for i, p in enumerate(self.level_paths):
            name = os.path.splitext(os.path.basename(p))[0]
            color = (255,255,255) if i==self.level_idx else (160,170,180)
            draw_text_left(self.screen, f"[{i+1}] {name}", x0, 90 + i*18, self.font, color)
        draw_text_center(self.screen, "Enter = start  •  ←/→ or A/D = change  •  Esc = back", SCREEN_W//2, SCREEN_H-22, self.font, (170,170,180))

    def draw_post(self):
        draw_parallax(self.screen, self.cam)
        draw_text_center(self.screen, "Level Complete!", SCREEN_W//2, 40, self.font, (255,255,255))
        draw_text_center(self.screen, f"Time: {self.level_time:.1f}s   Deaths: {self.deaths}", SCREEN_W//2, 80, self.font)
        # bests
        name = os.path.splitext(os.path.basename(self.level_paths[self.level_idx]))[0]
        s = self.stats.get(name, {})
        if s:
            bt = s.get("best_time", self.level_time)
            bd = s.get("best_deaths", self.deaths)
            draw_text_center(self.screen, f"Best Time: {bt:.1f}s   Best Deaths: {bd}", SCREEN_W//2, 100, self.font, (200,220,200))
        draw_text_center(self.screen, "Enter = Next • Esc = Menu", SCREEN_W//2, SCREEN_H-22, self.font, (170,170,180))

    def draw_dialog(self, text):
        # simple dialog box
        margin = 8
        box = pg.Rect(20, SCREEN_H-80, SCREEN_W-40, 60)
        pg.draw.rect(self.screen, (20,20,28), box)
        pg.draw.rect(self.screen, (80,80,120), box, 2)
        draw_text_left(self.screen, text, box.left+margin, box.top+margin, self.font)

    def close_to_npc(self):
        if not self.level: return False
        pr = self.player.rect
        for (tx, ty) in self.level.npcs:
            nr = rect_from_tile(tx, ty)
            if pr.colliderect(nr.inflate(8,8)):
                return True
        return False

    def trigger_npc_dialog(self):
        # Basic tutorial / ending lines depending on level index
        if self.level_idx == 0:
            self.npc_message = "Welcome! A/D to move, J=jump, K=dash, L=grab. Reach the green exit."
        else:
            self.npc_message = "Nice! Use J/K/L together: jump, grab/climb, dash when needed."
        self.npc_timer = 3.0

    def update_stats(self):
        name = os.path.splitext(os.path.basename(self.level_paths[self.level_idx]))[0]
        prev = self.stats.get(name, {})
        best_time = min(prev.get("best_time", 1e9), self.level_time)
        best_deaths = min(prev.get("best_deaths", 1e9), self.deaths)
        self.stats[name] = {"best_time": best_time, "best_deaths": int(best_deaths)}
        save_stats(self.stats)

# ------------------------------Entrypoint------------------------------

def run():
    parser = argparse.ArgumentParser(description="Celest-ish Homework (terminal launch)")
    parser.add_argument("--scale", type=int, default=3, help="window scale (pixels upscaled)")
    args = parser.parse_args()
    game = Game(args)
    game.run()

if __name__ == "__main__":
    run()