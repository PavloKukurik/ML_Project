import pygame
import time
import random

pygame.init()

# Кольори
white = (255, 255, 255)
yellow = (255, 255, 102)
black = (0, 0, 0)
red = (213, 50, 80)
green = (0, 255, 0)
blue = (50, 153, 213)
purple = (138, 43, 226)

# Розміри екрану
dis_width = 800
dis_height = 600

# Створення вікна
dis = pygame.display.set_mode((dis_width, dis_height))
pygame.display.set_caption('Змійка на Python: 2 гравці!')

clock = pygame.time.Clock()
snake_block = 20
snake_speed = 10

# Шрифти
font_style = pygame.font.SysFont("bahnschrift", 25)
score_font = pygame.font.SysFont("comicsansms", 35)

def your_score(score1, score2):
    value1 = score_font.render(f"Змійка 1 (Чорна): {score1}", True, yellow)
    value2 = score_font.render(f"Змійка 2 (Фіолетова): {score2}", True, yellow)
    dis.blit(value1, [10, 10])
    dis.blit(value2, [10, 50])

def draw_snake(color, snake_list):
    for x in snake_list:
        pygame.draw.rect(dis, color, [x[0], x[1], snake_block, snake_block])

def message(msg, color):
    mesg = font_style.render(msg, True, color)
    dis.blit(mesg, [dis_width / 6, dis_height / 3])

def gameLoop():
    game_over = False
    game_close = False

    # Змійка 1 (управління WASD)
    x1 = dis_width / 4
    y1 = dis_height / 2
    x1_change = 0
    y1_change = 0
    snake1_List = []
    Length_of_snake1 = 1

    # Змійка 2 (управління стрілки)
    x2 = dis_width * 3 / 4
    y2 = dis_height / 2
    x2_change = 0
    y2_change = 0
    snake2_List = []
    Length_of_snake2 = 1

    # Їжа
    foodx = round(random.randrange(0, dis_width - snake_block) / 20.0) * 20.0
    foody = round(random.randrange(0, dis_height - snake_block) / 20.0) * 20.0

    while not game_over:

        while game_close:
            dis.fill(blue)
            message("Кінець гри! Натисни 'C' для продовження або 'Q' для виходу", red)
            your_score(Length_of_snake1 - 1, Length_of_snake2 - 1)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        game_close = False
                    if event.key == pygame.K_c:
                        gameLoop()

        # Управління обох гравців
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True

            if event.type == pygame.KEYDOWN:
                # Змійка 1 - WASD
                if event.key == pygame.K_a and x1_change == 0:
                    x1_change = -snake_block
                    y1_change = 0
                elif event.key == pygame.K_d and x1_change == 0:
                    x1_change = snake_block
                    y1_change = 0
                elif event.key == pygame.K_w and y1_change == 0:
                    y1_change = -snake_block
                    x1_change = 0
                elif event.key == pygame.K_s and y1_change == 0:
                    y1_change = snake_block
                    x1_change = 0

                # Змійка 2 - Стрілки
                elif event.key == pygame.K_LEFT and x2_change == 0:
                    x2_change = -snake_block
                    y2_change = 0
                elif event.key == pygame.K_RIGHT and x2_change == 0:
                    x2_change = snake_block
                    y2_change = 0
                elif event.key == pygame.K_UP and y2_change == 0:
                    y2_change = -snake_block
                    x2_change = 0
                elif event.key == pygame.K_DOWN and y2_change == 0:
                    y2_change = snake_block
                    x2_change = 0

        # Оновлюємо позиції
        x1 += x1_change
        y1 += y1_change
        x2 += x2_change
        y2 += y2_change

        # Перевірка виходу за межі
        if x1 >= dis_width or x1 < 0 or y1 >= dis_height or y1 < 0:
            game_close = True
        if x2 >= dis_width or x2 < 0 or y2 >= dis_height or y2 < 0:
            game_close = True

        dis.fill(blue)
        # Малюємо їжу
        pygame.draw.rect(dis, green, [foodx, foody, snake_block, snake_block])

        # Оновлюємо списки змійок
        snake1_Head = [x1, y1]
        snake1_List.append(snake1_Head)
        if len(snake1_List) > Length_of_snake1:
            del snake1_List[0]

        snake2_Head = [x2, y2]
        snake2_List.append(snake2_Head)
        if len(snake2_List) > Length_of_snake2:
            del snake2_List[0]

        # Перевірка зіткнень з власним тілом
        for segment in snake1_List[:-1]:
            if segment == snake1_Head:
                game_close = True
        for segment in snake2_List[:-1]:
            if segment == snake2_Head:
                game_close = True

        # Перевірка зіткнень одна з одною
        if snake1_Head in snake2_List:
            game_close = True
        if snake2_Head in snake1_List:
            game_close = True

        # Малюємо змійок
        draw_snake(black, snake1_List)
        draw_snake(purple, snake2_List)

        your_score(Length_of_snake1 - 1, Length_of_snake2 - 1)

        pygame.display.update()

        # Перевірка чи хтось з'їв їжу
        if x1 == foodx and y1 == foody:
            foodx = round(random.randrange(0, dis_width - snake_block) / 20.0) * 20.0
            foody = round(random.randrange(0, dis_height - snake_block) / 20.0) * 20.0
            Length_of_snake1 += 1

        if x2 == foodx and y2 == foody:
            foodx = round(random.randrange(0, dis_width - snake_block) / 20.0) * 20.0
            foody = round(random.randrange(0, dis_height - snake_block) / 20.0) * 20.0
            Length_of_snake2 += 1

        clock.tick(snake_speed)

    pygame.quit()
    quit()

gameLoop()
