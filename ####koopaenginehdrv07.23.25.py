 import os
import pygame, sys, math, itertools, random
import io  # Needed for sound buffer

# --- Sound Engine Initialization ---
pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
pygame.init()
pygame.mixer.init()  # Initialize the mixer after pre_init

# --- Constants ---
WIDTH, HEIGHT = 800, 600
TILE = 32
FPS = 60
GRAVITY = 0.55
SCROLL_EDGE = WIDTH // 3

# --- NSMB2-inspired color palette ---
PAL = {
    "sky": (164, 220, 255),
    "cloud_blue": (190, 230, 255),
    "mountain_blue": (120, 190, 240),
    "grass_green": (120, 200, 80),
    "dirt_brown": (150, 110, 70),
    "coin_yellow": (255, 215, 60),
    "mario_red": (220, 60, 60),
    "mario_blue": (80, 140, 240),
    "button_yellow": (255, 220, 80),
    "button_shadow": (200, 160, 50),
    "text_brown": (80, 50, 30),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "brick": (155, 118, 83),
    "player": (234, 92, 68),
    "flag": (255, 255, 255)
}

# --- Sound Generation (OST Style) ---
def generate_tone(frequency, duration_ms, volume=0.2):
    sample_rate = 22050
    n_samples = int(round(duration_ms * sample_rate / 1000.0))
    buf = bytearray()
    max_amplitude = int(32767 * volume)
    for i in range(n_samples):
        t = float(i) / sample_rate
        wave = math.sin(2.0 * math.pi * frequency * t)
        value = int(wave * max_amplitude)
        buf += value.to_bytes(2, byteorder='little', signed=True)
    stereo_buf = bytearray()
    for i in range(0, len(buf), 2):
        sample_bytes = buf[i:i+2]
        stereo_buf += sample_bytes + sample_bytes
    return pygame.mixer.Sound(buffer=stereo_buf)

try:
    SFX_HOVER = generate_tone(660, 100)
    SFX_CLICK = generate_tone(440, 120)
    SFX_COIN_SOUND = generate_tone(1320, 120)
    SFX_JUMP_SOUND = generate_tone(880, 120)

    def create_simple_ost():
        notes = [261.63, 329.63, 392.00, 523.25, 659.25, 783.99, 1046.50, 1318.51]
        note_duration = 150
        music_buffer = bytearray()
        sample_rate = 22050
        max_amplitude = int(32767 * 0.15)
        for freq in notes:
            n_samples = int(round(note_duration * sample_rate / 1000.0))
            for i in range(n_samples):
                t = float(i) / sample_rate
                wave = math.sin(2.0 * math.pi * freq * t)
                value = int(wave * max_amplitude)
                music_buffer += value.to_bytes(2, byteorder='little', signed=True)
        stereo_music_buffer = bytearray()
        for i in range(0, len(music_buffer), 2):
            sample_bytes = music_buffer[i:i+2]
            stereo_music_buffer += sample_bytes + sample_bytes
        sound = pygame.mixer.Sound(buffer=stereo_music_buffer)
        sound.set_volume(0.5)
        return sound

    OST_THEME = create_simple_ost()
except Exception as e:
    print(f"Warning: Error generating sounds: {e}")
    SFX_HOVER = SFX_CLICK = SFX_COIN_SOUND = SFX_JUMP_SOUND = OST_THEME = None

# --- Graphics Helpers ---
def solid(color, w=TILE, h=TILE):
    surf = pygame.Surface((w, h))
    surf.fill(color)
    return surf

def create_tile(color, w=32, h=32):
    surf = pygame.Surface((w, h))
    surf.fill(color)
    return surf

def create_cloud():
    cloud = pygame.Surface((100, 60), pygame.SRCALPHA)
    pygame.draw.circle(cloud, PAL["cloud_blue"], (20, 30), 20)
    pygame.draw.circle(cloud, PAL["cloud_blue"], (40, 20), 25)
    pygame.draw.circle(cloud, PAL["cloud_blue"], (60, 25), 22)
    pygame.draw.circle(cloud, PAL["cloud_blue"], (80, 30), 20)
    return cloud

def create_mountain():
    mountain = pygame.Surface((200, 150), pygame.SRCALPHA)
    pygame.draw.polygon(mountain, PAL["mountain_blue"], [(0, 150), (100, 30), (200, 150)])
    return mountain

def create_coin():
    coin = pygame.Surface((24, 24), pygame.SRCALPHA)
    pygame.draw.circle(coin, PAL["coin_yellow"], (12, 12), 12)
    pygame.draw.circle(coin, (255, 240, 120), (12, 12), 10)
    pygame.draw.circle(coin, (255, 220, 40), (12, 12), 8)
    return coin

def create_mario_icon():
    mario = pygame.Surface((40, 50), pygame.SRCALPHA)
    pygame.draw.rect(mario, PAL["mario_red"], (10, 5, 20, 10))
    pygame.draw.rect(mario, PAL["mario_red"], (5, 10, 30, 5))
    pygame.draw.rect(mario, (255, 200, 180), (12, 15, 16, 15))
    pygame.draw.circle(mario, PAL["black"], (17, 20), 2)
    pygame.draw.circle(mario, PAL["black"], (23, 20), 2)
    pygame.draw.rect(mario, PAL["black"], (15, 23, 10, 3))
    pygame.draw.rect(mario, PAL["mario_blue"], (12, 30, 16, 20))
    pygame.draw.rect(mario, PAL["mario_blue"], (8, 35, 8, 10))
    pygame.draw.rect(mario, PAL["mario_blue"], (24, 35, 8, 10))
    pygame.draw.circle(mario, (40, 80, 180), (17, 35), 2)
    pygame.draw.circle(mario, (40, 80, 180), (23, 35), 2)
    return mario

def draw_text(text, size, color, x, y, center=True):
    try:
        font = pygame.font.SysFont('Arial', size, bold=True)
    except:
        font = pygame.font.Font(None, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    return text_surface, text_rect

# --- Game Data ---
IMG = {
    "#": solid(PAL["brick"]),
    "G": solid(PAL["grass_green"]),
    "C": solid(PAL["coin_yellow"]),
    "F": solid(PAL["flag"]),
}

WORLD_DATA = [
  [  # world 1
    [
      "................................................................",
      "................................................................",
      ".......................................................C........",
      ".................................####................########F..",
      "............C...................................................",
      "########.............................#####......................",
      "................................................................",
      "................................................................",
      "################################################################"
    ],
    [
      "........................................................................",
      "..C....................................................C...............F",
      "..........####......................#####...............................",
      "........................................................................",
      "...............#####....................................................",
      "..........................................#####........................",
      "#######################################################################"
    ],
    [
      "............................................................F..........",
      ".............C...............................................###.......",
      "........##########....................................................",
      ".....................................................#####............",
      "......................#####.................................C..........",
      "#######################################################################"
    ],
  ],
]

def auto_worlds(base_worlds, worlds=5, levels_each=3, length=60):
    while len(base_worlds) < worlds:
        w = []
        for _ in range(levels_each):
            rows = []
            for y in range(9):
                if y == 8:
                    rows.append("#"*length)
                elif y == 7:
                    row = list("."*length)
                    for i in range(random.randint(3, 7)):
                        pos = random.randint(0, length-4)
                        width = random.randint(3, 8)
                        for j in range(width):
                            if pos+j < length:
                                row[pos+j] = "#"
                    rows.append("".join(row))
                else:
                    row = list("."*length)
                    if random.random() < 0.4:
                        for i in range(random.randint(2, 5)):
                            pos = random.randint(0, length-1)
                            row[pos] = "C"
                    rows.append("".join(row))
            flag_row = list(rows[7])
            flag_row[-2] = "F"
            rows[7] = "".join(flag_row)
            w.append(rows)
        base_worlds.append(w)
auto_worlds(WORLD_DATA, worlds=5)

# --- Menu Classes ---
class Button:
    def __init__(self, x, y, width, height, text, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hovered = False
        self.pressed = False
        self.original_y = y
        self.hover_offset = 0
        self.last_hover_state = False

    def draw(self, screen):
        if self.hovered:
            self.hover_offset = min(self.hover_offset + 0.5, 5)
        else:
            self.hover_offset = max(self.hover_offset - 0.5, 0)
        draw_y = self.original_y - self.hover_offset
        shadow_rect = pygame.Rect(self.rect.x + 3, draw_y + 3, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, PAL["button_shadow"], shadow_rect, border_radius=10)
        button_color = PAL["button_yellow"]
        pygame.draw.rect(screen, button_color, (self.rect.x, draw_y, self.rect.width, self.rect.height), border_radius=10)
        pygame.draw.rect(screen, PAL["text_brown"], (self.rect.x, draw_y, self.rect.width, self.rect.height), 3, border_radius=10)
        text_color = PAL["text_brown"]
        text_surf, text_rect = draw_text(self.text, 28, text_color, self.rect.centerx, draw_y + self.rect.height//2)
        screen.blit(text_surf, text_rect)

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        if self.hovered and not self.last_hover_state and SFX_HOVER:
            SFX_HOVER.play()
        self.last_hover_state = self.hovered
        return self.hovered

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                self.pressed = True
                if SFX_CLICK: SFX_CLICK.play()
                if self.action:
                    self.action()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pressed = False
        return None

class Particle:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT//2)
        self.size = random.randint(2, 5)
        self.speed = random.uniform(0.5, 2)
        self.color = random.choice([
            (255, 255, 255, 150),
            (255, 215, 60, 150),
            (164, 220, 255, 150)
        ])
        self.alpha = random.randint(100, 200)
        self.sway = random.uniform(0.2, 0.8)
        self.sway_offset = random.uniform(0, 2 * math.pi)
    def update(self):
        self.y += self.speed
        self.x += math.sin(pygame.time.get_ticks() * 0.001 + self.sway_offset) * self.sway
        self.alpha -= 0.5
        if self.y > HEIGHT or self.alpha <= 0:
            self.__init__()
    def draw(self, screen):
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], int(self.alpha)), (self.size, self.size), self.size)
        screen.blit(s, (self.x, self.y))

class MainMenu:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("NSMB2 Koopa Engine")
        self.clock = pygame.time.Clock()
        self.running = True
        self.showing_options = False
        self.result = None
        if OST_THEME and not pygame.mixer.get_busy():
            OST_THEME.play(loops=-1)
        button_width, button_height = 220, 60
        start_x = WIDTH // 2 - button_width // 2
        start_y = HEIGHT // 2 + 30
        self.buttons = [
            Button(start_x, start_y, button_width, button_height, "START GAME", self.action_start),
            Button(start_x, start_y + 80, button_width, button_height, "OPTIONS", self.action_options),
            Button(start_x, start_y + 160, button_width, button_height, "QUIT GAME", self.action_quit)
        ]
        self.options_buttons = [
            Button(start_x, start_y + 80, button_width, button_height, "BACK", self.action_back)
        ]
        self.clouds = [(create_cloud(), random.randint(-50, WIDTH), random.randint(50, 200)) for _ in range(5)]
        self.mountains = [(create_mountain(), random.randint(-100, WIDTH), HEIGHT - 150) for _ in range(3)]
        self.ground_tiles = [pygame.Rect(x * 32, HEIGHT - 32, 32, 32) for x in range(WIDTH // 32 + 1)]
        self.particles = [Particle() for _ in range(40)]
        self.coin = create_coin()
        self.mario = create_mario_icon()
        self.title_y = -100
        self.title_target_y = 100
        self.mario_x = -100
        self.mario_target_x = WIDTH // 2
        self.coin_angle = 0
    def action_start(self):
        if SFX_COIN_SOUND: SFX_COIN_SOUND.play()
        self.result = "game"
        self.running = False
    def action_options(self):
        self.showing_options = True
    def action_back(self):
        self.showing_options = False
    def action_quit(self):
        pygame.quit()
        sys.exit()
    def run(self):
        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                btns = self.options_buttons if self.showing_options else self.buttons
                for button in btns:
                    button.handle_event(event)
            # Animations
            if self.title_y < self.title_target_y:
                self.title_y += 3
            else:
                self.title_y = self.title_target_y
            if self.mario_x < self.mario_target_x:
                self.mario_x += 5
            else:
                self.mario_x = self.mario_target_x
            self.coin_angle += 0.05
            for particle in self.particles:
                particle.update()
            for button in (self.options_buttons if self.showing_options else self.buttons):
                button.check_hover(mouse_pos)
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        return self.result
    def draw(self):
        self.screen.fill(PAL["sky"])
        for mountain, x, y in self.mountains:
            self.screen.blit(mountain, (x, y))
        for cloud, x, y in self.clouds:
            self.screen.blit(cloud, (x, y))
        for particle in self.particles:
            particle.draw(self.screen)
        title_text = "KOOPA ENGINE"
        title_surf, title_rect = draw_text(title_text, 72, PAL["text_brown"], WIDTH//2, self.title_y)
        shadow_surf, shadow_rect = draw_text(title_text, 72, (0, 0, 0), WIDTH//2 + 4, self.title_y + 4)
        self.screen.blit(shadow_surf, shadow_rect)
        self.screen.blit(title_surf, title_rect)
        subtitle_surf, subtitle_rect = draw_text("New Super Mario Bros. 2 Style", 28, PAL["text_brown"], WIDTH//2, self.title_y + 70)
        self.screen.blit(subtitle_surf, subtitle_rect)
        coin_y = math.sin(self.coin_angle) * 10
        self.screen.blit(self.coin, (WIDTH//2 + 150, self.title_y + 30 + coin_y))
        self.screen.blit(self.mario, (self.mario_x - 20, self.title_y + 20))
        for tile in self.ground_tiles:
            pygame.draw.rect(self.screen, PAL["dirt_brown"], tile)
            pygame.draw.line(self.screen, (120, 80, 50), (tile.left, tile.top), (tile.right, tile.top), 2)
        for i in range(len(self.ground_tiles)):
            if i % 2 == 0:
                pygame.draw.line(self.screen, PAL["grass_green"], (i*32, HEIGHT-32), (i*32+32, HEIGHT-32), 3)
        btns = self.options_buttons if self.showing_options else self.buttons
        for button in btns:
            button.draw(self.screen)
        if self.showing_options:
            s, r = draw_text("OPTIONS (not implemented)", 34, PAL["text_brown"], WIDTH//2, HEIGHT//2-100)
            self.screen.blit(s, r)

# --- Game Classes ---
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = solid(PAL["player"])
        self.rect = self.image.get_rect(topleft=pos)
        self.vel = pygame.Vector2(0,0)
        self.on_ground = False
    def update(self, tiles):
        keys = pygame.key.get_pressed()
        self.vel.x = (keys[pygame.K_RIGHT]-keys[pygame.K_LEFT])*4
        if keys[pygame.K_z] and self.on_ground:
            self.vel.y = -10
            if SFX_JUMP_SOUND: SFX_JUMP_SOUND.play()
        self.vel.y += GRAVITY
        self.rect.x += self.vel.x
        self.collide(tiles,'x')
        self.rect.y += self.vel.y
        self.on_ground=False
        self.collide(tiles,'y')
    def collide(self,tiles,dir):
        for t in tiles:
            if self.rect.colliderect(t):
                if dir=='x':
                    self.rect.x = t.right if self.vel.x<0 else t.left-self.rect.width
                else:
                    if self.vel.y>0:
                        self.rect.bottom = t.top
                        self.on_ground=True
                    else:
                        self.rect.top = t.bottom
                    self.vel.y=0

class Level:
    def __init__(self, grid):
        self.grid = grid
        self.w = len(grid[0])
        self.h = len(grid)
        self.tiles=[]
        self.coins=[]
        self.flag=None
        for y,row in enumerate(grid):
            for x,ch in enumerate(row):
                if ch=="#":
                    self.tiles.append(pygame.Rect(x*TILE,y*TILE,TILE,TILE))
                elif ch=="C":
                    self.coins.append(pygame.Rect(x*TILE+8,y*TILE+8,16,16))
                elif ch=="F":
                    self.flag = pygame.Rect(x*TILE,y*TILE,32,64)
    def draw(self,screen,camera):
        for rect in self.tiles:
            screen.blit(IMG["#"],camera.apply(rect))
        for rect in self.coins:
            screen.blit(IMG["C"],camera.apply(rect))
        if self.flag:
            screen.blit(IMG["F"],camera.apply(self.flag))

class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0,0)
    def follow(self, player):
        target_x = player.rect.centerx - SCROLL_EDGE
        if target_x>self.offset.x:
            self.offset.x = target_x
    def apply(self, rect):
        return rect.move(-int(self.offset.x), -int(self.offset.y))

class GameEngine:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH,HEIGHT))
        pygame.display.set_caption("Python Mario Vibes")
        self.clock = pygame.time.Clock()
        self.world = 0
        self.level = 0
        self.load_level()
    def load_level(self):
        grid = WORLD_DATA[self.world][self.level]
        self.level_obj = Level(grid)
        spawn_x, spawn_y = TILE*2, HEIGHT-3*TILE
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch in "#G":
                    spawn_x, spawn_y = x*TILE, (y-1)*TILE
                    break
            if spawn_x != TILE*2 or spawn_y != HEIGHT-3*TILE:
                break
        self.player = Player((spawn_x, spawn_y))
        self.camera = Camera()
        self.coins = 0
    def advance(self):
        self.level += 1
        if self.level >= len(WORLD_DATA[self.world]):
            self.level = 0
            self.world = (self.world + 1) % len(WORLD_DATA)
        self.load_level()
    def run(self):
        running = True
        while running:
            for e in pygame.event.get():
                if e.type==pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE:
                    running = False
            self.player.update(self.level_obj.tiles)
            self.camera.follow(self.player)
            for c in self.level_obj.coins[:]:
                if self.player.rect.colliderect(c):
                    self.level_obj.coins.remove(c)
                    self.coins+=1
                    if SFX_COIN_SOUND: SFX_COIN_SOUND.play()
            if self.level_obj.flag and self.player.rect.colliderect(self.level_obj.flag):
                self.advance()
            self.screen.fill(PAL["sky"])
            self.level_obj.draw(self.screen,self.camera)
            self.screen.blit(self.player.image,self.camera.apply(self.player.rect))
            pygame.display.set_caption(f"W{self.world+1}-{self.level+1}  Coins:{self.coins}")
            pygame.display.flip()
            self.clock.tick(FPS)
        return "menu"

# --- Main Execution ---
if __name__ == "__main__":
    current_state = "menu"
    while True:
        if current_state == "menu":
            menu = MainMenu()
            current_state = menu.run()
        elif current_state == "game":
            if OST_THEME:
                OST_THEME.stop()
            game = GameEngine()
            current_state = game.run()
        else:
            break
    if OST_THEME:
        OST_THEME.stop()
    pygame.quit()
    sys.exit()
