import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 800, 600
BALL_RADIUS = 20
PADDLE_WIDTH, PADDLE_HEIGHT = 20, 100
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Ping Pong')
clock = pygame.time.Clock()


class Ball:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.dx = 5
        self.dy = 5

    def draw(self, screen):
        pygame.draw.circle(screen, WHITE, (self.x, self.y), BALL_RADIUS)

    def move(self):
        self.x += self.dx
        self.y += self.dy

        if self.y + BALL_RADIUS > HEIGHT or self.y - BALL_RADIUS < 0:
            self.dy = -self.dy

        if self.x + BALL_RADIUS > WIDTH:
            self.dx = -self.dx


class Paddle:
    def __init__(self):
        self.y = HEIGHT // 2
        self.speed = 10

    def draw(self, screen):
        pygame.draw.rect(screen, WHITE,
                         (WIDTH - PADDLE_WIDTH, self.y - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT))

    def move(self, dy):
        self.y = max(min(self.y + dy * self.speed, HEIGHT - PADDLE_HEIGHT // 2), PADDLE_HEIGHT // 2)


ball = Ball()
paddle = Paddle()
hits = 0
game_over = False

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    paddle.move(keys[pygame.K_DOWN] - keys[pygame.K_UP])

    if not game_over:
        ball.move()
        if ball.x + BALL_RADIUS > WIDTH - PADDLE_WIDTH and abs(ball.y - paddle.y) < PADDLE_HEIGHT // 2:
            ball.dx = -abs(ball.dx)
            hits += 1
        elif ball.x - BALL_RADIUS < 0:
            game_over = True
    else:
        if keys[pygame.K_SPACE]:
            ball = Ball()
            paddle = Paddle()
            hits = 0
            game_over = False

    screen.fill(BLACK)
    ball.draw(screen)
    paddle.draw(screen)

    font = pygame.font.Font(None, 74)
    text = font.render(str(hits), True, WHITE)
    screen.blit(text, (WIDTH // 2, 10))

    pygame.display.flip()
    clock.tick(60)
