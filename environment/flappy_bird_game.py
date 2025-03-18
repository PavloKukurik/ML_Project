import pygame
import sys
import random

# Основні параметри
WIN_WIDTH = 400
WIN_HEIGHT = 600
FPS = 60

# Колір
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (200, 0, 0)

# Ініціалізація
pygame.init()
screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()

# Параметри пташки
GRAVITY = 0.5
FLAP_STRENGTH = -10
MAX_DROP_SPEED = 10


class Bird:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 34
        self.height = 24
        self.velocity = 0
        self.color = GREEN

    def update(self):
        # Прискорення вниз через гравітацію
        self.velocity += GRAVITY
        # Обмеження максимальної швидкості падіння
        if self.velocity > MAX_DROP_SPEED:
            self.velocity = MAX_DROP_SPEED
        # Оновлення позиції
        self.y += self.velocity

        # Межі
        if self.y < 0:
            self.y = 0
            self.velocity = 0
        if self.y + self.height > WIN_HEIGHT:
            self.y = WIN_HEIGHT - self.height
            self.velocity = 0

    def flap(self):
        self.velocity = FLAP_STRENGTH

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, (self.x, self.y, self.width, self.height))


class Pipe:
    def __init__(self, x):
        self.x = x
        self.width = 60
        self.gap = 150
        self.speed = 3

        self.top_height = random.randint(50, WIN_HEIGHT - self.gap - 50)
        self.bottom_y = self.top_height + self.gap

    def update(self):
        self.x -= self.speed

    def draw(self, surface):
        pygame.draw.rect(surface, RED, (self.x, 0, self.width, self.top_height))
        pygame.draw.rect(surface, RED, (self.x, self.bottom_y, self.width, WIN_HEIGHT - self.bottom_y))

    def collide(self, bird):
        bird_rect = pygame.Rect(bird.x, bird.y, bird.width, bird.height)
        top_pipe_rect = pygame.Rect(self.x, 0, self.width, self.top_height)
        bottom_pipe_rect = pygame.Rect(self.x, self.bottom_y, self.width, WIN_HEIGHT - self.bottom_y)

        return bird_rect.colliderect(top_pipe_rect) or bird_rect.colliderect(bottom_pipe_rect)


def main():
    bird = Bird(50, WIN_HEIGHT // 2)
    pipes = []
    score = 0
    running = True
    pipe_timer = 0
    PIPE_SPAWN_INTERVAL = 1500  # мс

    while running:
        dt = clock.tick(FPS)
        screen.fill(WHITE)

        # --- Event handler ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Основне управління flap'ом
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bird.flap()

        # --- Оновлення об'єктів ---
        bird.update()

        # Створення нових труб
        pipe_timer += dt
        if pipe_timer > PIPE_SPAWN_INTERVAL:
            pipes.append(Pipe(WIN_WIDTH))
            pipe_timer = 0

        # Оновлення труб і перевірка на зіткнення
        for pipe in pipes:
            pipe.update()
            if pipe.collide(bird):
                print(f"Game Over! Score: {score}")
                running = False

        # Видалення труб, що вийшли за межі
        pipes = [pipe for pipe in pipes if pipe.x + pipe.width > 0]

        # --- Рендер ---
        bird.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)

        # Відображення рахунку
        font = pygame.font.SysFont(None, 36)
        score_surface = font.render(f"Score: {score}", True, BLACK)
        screen.blit(score_surface, (10, 10))

        pygame.display.flip()

        # Підрахунок очок (коли пташка успішно пролетіла трубу)
        for pipe in pipes:
            if not hasattr(pipe, "passed") and pipe.x + pipe.width < bird.x:
                pipe.passed = True
                score += 1

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
