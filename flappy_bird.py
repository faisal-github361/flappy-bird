# importing important libraries
import pygame
from sys import exit
import random
import math
import os
import sys

# variables
GAME_WIDTH = 360
GAME_HEIGHT = 640

# keys
FLAP_KEYS = (pygame.K_SPACE, pygame.K_x, pygame.K_UP)
RESTART_KEYS = FLAP_KEYS + (pygame.K_r, pygame.K_RETURN)
RESTART_DELAY = 500  # ms after dying before restart is allowed (so flap-spamming doesn't skip the game over screen)

def resource_path(name):
    """Finds a game file (image/font). Works normally and when packed into an .exe with PyInstaller."""
    folders = []
    if hasattr(sys, "_MEIPASS"):
        folders.append(sys._MEIPASS)                            # where PyInstaller unpacks bundled files
    if getattr(sys, "frozen", False):
        folders.append(os.path.dirname(sys.executable))         # next to the .exe
    folders.append(os.path.dirname(os.path.abspath(__file__)))  # next to the script
    folders.append(os.getcwd())                                 # the folder the game was started from

    for folder in folders:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    return os.path.join(folders[0], name)  # not found anywhere: pygame will show this path in its error

# the best score is saved in a file next to the script (or next to the .exe when packed)
if getattr(sys, "frozen", False):
    save_folder = os.path.dirname(sys.executable)
else:
    save_folder = os.path.dirname(os.path.abspath(__file__))
BEST_SCORE_FILE = os.path.join(save_folder, "best_score.txt")
FONT_FILE = resource_path("PressStart2P-Regular.ttf")

# bird class
bird_x = GAME_WIDTH / 8
bird_y = GAME_HEIGHT / 2
bird_width = 34
bird_height = 24

class Bird(pygame.Rect):
    def __init__(self, img):
        pygame.Rect.__init__(self, bird_x, bird_y, bird_width, bird_height)
        self.img = img

# pipe class
pipe_x = GAME_WIDTH
pipe_y = 0
pipe_width = 64
pipe_height = 512

class Pipe(pygame.Rect):
    def __init__(self, img):
        pygame.Rect.__init__(self, pipe_x, pipe_y, pipe_width, pipe_height)
        self.img = img
        self.passed = False

# game images
background = pygame.image.load(resource_path("flappybirdbg.png"))
bird_image = pygame.image.load(resource_path("flappybird.png"))
bird_image = pygame.transform.scale(bird_image, (bird_width, bird_height))
top_pipe_image = pygame.image.load(resource_path("toppipe.png"))
top_pipe_image = pygame.transform.scale(top_pipe_image, (pipe_width, pipe_height))
bottom_pipe_image = pygame.image.load(resource_path("bottompipe.png"))
bottom_pipe_image = pygame.transform.scale(bottom_pipe_image, (pipe_width, pipe_height))


# best score methods
def load_best_score():
    """Reads the best score from the file (0 if there isn't one yet)."""
    try:
        with open(BEST_SCORE_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_best_score(value):
    """Writes the best score to the file."""
    try:
        with open(BEST_SCORE_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        pass  # couldn't write the file (read-only folder?) - the game still works


# game logic
bird = Bird(bird_image)
pipes = []
velocity_x = -2  # moves pipe to the left speed (simulating bird moving right)
velocity_y = 0   # moves bird up/down speed
gravity = 0.4
score = 0
best_score = load_best_score()
new_best = False        # True when this run beat the old best score
game_over = False
game_over_time = 0      # when the bird died (ms), used for the restart delay
game_started = False


def draw_text(text, font, y, color='white'):
    """Draws pixel text with a black outline, centered horizontally."""
    render = font.render(text, False, color)
    outline = font.render(text, False, 'black')
    rect = render.get_rect(midtop=(GAME_WIDTH // 2, y))
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            if dx or dy:
                window.blit(outline, rect.move(dx, dy))
    window.blit(render, rect)


def draw_start_screen():
    window.blit(background, (0, 0))

    # bird bobs up and down
    bob = math.sin(pygame.time.get_ticks() / 250) * 8
    window.blit(bird.img, (bird.x, int(GAME_HEIGHT / 2 + bob)))

    draw_text("FLAPPY", title_font, 140)
    draw_text("BIRD", title_font, 190)

    # blinking prompt (on for 0.5s, off for 0.5s)
    if (pygame.time.get_ticks() // 500) % 2 == 0:
        draw_text("PRESS SPACE", small_font, 400)

    if best_score > 0:
        draw_text("BEST: " + str(best_score), small_font, 470)


def draw():
    window.blit(background, (0, 0))
    window.blit(bird.img, bird)

    for pipe in pipes:
        window.blit(pipe.img, pipe)

    if not game_over:
        draw_text(str(int(score)), text_font, 10)


def draw_game_over():
    window.blit(overlay, (0, 0))  # dims the frozen game behind the text

    draw_text("GAME OVER", game_over_font, 170)
    draw_text("SCORE: " + str(int(score)), small_font, 250)
    draw_text("BEST: " + str(best_score), small_font, 285)
    if new_best:
        draw_text("NEW BEST!", small_font, 335, 'yellow')

    # blinking restart prompt, only shown once restarting is allowed
    now = pygame.time.get_ticks()
    if now - game_over_time > RESTART_DELAY and (now // 500) % 2 == 0:
        draw_text("R TO RESTART", small_font, 420)


def move():
    global velocity_y, score
    velocity_y += gravity
    bird.y += velocity_y
    bird.y = max(bird.y, 0)

    if bird.y > GAME_HEIGHT:
        end_game()
        return

    for pipe in pipes:
        pipe.x += velocity_x

        if not pipe.passed and bird.x > pipe.x + pipe.width:
            score += 0.5
            pipe.passed = True

        if bird.colliderect(pipe):
            end_game()
            return

    # remove pipes that left the screen
    # (done outside the for loop so the list isn't changed while looping over it)
    while len(pipes) > 0 and pipes[0].x < -pipe_width:
        pipes.pop(0)


def create_pipes():
    random_pipe_y = pipe_y - pipe_height / 4 - random.random() * (pipe_height / 2)  # 0-h/2
    opening_space = GAME_HEIGHT / 4

    top_pipe = Pipe(top_pipe_image)
    top_pipe.y = random_pipe_y
    pipes.append(top_pipe)

    bottom_pipe = Pipe(bottom_pipe_image)
    bottom_pipe.y = top_pipe.y + top_pipe.height + opening_space
    pipes.append(bottom_pipe)


def end_game():
    """Called when the bird dies. Updates and saves the best score."""
    global game_over, game_over_time, best_score, new_best
    game_over = True
    game_over_time = pygame.time.get_ticks()

    if int(score) > best_score:
        best_score = int(score)
        new_best = True
        save_best_score(best_score)


def reset_game():
    global velocity_y, score, game_over, new_best
    bird.y = bird_y
    velocity_y = 0
    pipes.clear()
    score = 0
    game_over = False
    new_best = False
    pygame.time.set_timer(create_pipes_timer, 1500)  # restart timer so the first pipe isn't random


pygame.init()

# window icon: the bird centered on a square canvas so it doesn't get squished
icon = pygame.Surface((32, 32), pygame.SRCALPHA)
icon.blit(bird_image, bird_image.get_rect(center=(16, 16)))
pygame.display.set_icon(icon)

title_font = pygame.font.Font(FONT_FILE, 40)
game_over_font = pygame.font.Font(FONT_FILE, 32)
text_font = pygame.font.Font(FONT_FILE, 25)
small_font = pygame.font.Font(FONT_FILE, 20)
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("flappy bird | by faicode")
clock = pygame.time.Clock()

# dark see-through layer drawn over the game on the game over screen
overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
overlay.fill((0, 0, 0, 120))

# the pipe timer starts when the player presses the first key
create_pipes_timer = pygame.USEREVENT + 0

while True:  # loop
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

        if event.type == create_pipes_timer and game_started and not game_over:
            create_pipes()

        if event.type == pygame.KEYDOWN:
            if not game_started:
                if event.key in FLAP_KEYS:
                    game_started = True
                    pygame.time.set_timer(create_pipes_timer, 1500)  # makes a pipe every 1.5 seconds
                    velocity_y = -6

            elif game_over:
                # restart (R / Enter / flap keys) once the short delay has passed
                if event.key in RESTART_KEYS and pygame.time.get_ticks() - game_over_time > RESTART_DELAY:
                    reset_game()
                    if event.key in FLAP_KEYS:
                        velocity_y = -6

            elif event.key in FLAP_KEYS:
                velocity_y = -6

    if not game_started:
        draw_start_screen()
    else:
        if not game_over:
            move()
        draw()
        if game_over:
            draw_game_over()

    pygame.display.update()
    clock.tick(60)  # 60 fps