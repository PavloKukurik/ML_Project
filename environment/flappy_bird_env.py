import pygame
import random
import numpy as np
from .flappy_bird_game import Bird, Pipe, WIN_WIDTH, WIN_HEIGHT, FPS
import torch


class FlappyBirdEnv:
    """
    Flappy Bird environment for reinforcement learning.

    This environment allows the agent to interact with the Flappy Bird game. The agent can perform
    two actions: flap (1) or do nothing (0). The environment returns the next state (grayscale image),
    a reward, and a done flag indicating if the game is over.
    """

    def __init__(self):
        """
        Initializes the Flappy Bird environment.
        """
        self.screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.bird = Bird(50, WIN_HEIGHT // 2)
        self.pipes = []
        self.score = 0
        self.pipe_timer = 0
        self.PIPE_SPAWN_INTERVAL = 1500  # ms
        self.running = True

    def reset(self):
        """
        Resets the game environment and returns the initial state.

        :return: The initial game state (grayscale image).
        """
        self.bird = Bird(50, WIN_HEIGHT // 2)
        self.pipes = []
        self.score = 0
        self.pipe_timer = 0
        self.running = True
        return self.get_state()

    def step(self, action):
        """
        Takes an action in the environment and returns the next state, reward, and whether the game is done.

        :param action: The action taken by the agent (0 = Do nothing, 1 = Flap)
        :return: next_state (processed image), reward, done (whether the game is over)
        """
        if action == 1:  # Flap (flap the bird)
            self.bird.flap()

        # Update game state
        self.bird.update()
        self.pipe_timer += self.clock.tick(FPS)

        if self.pipe_timer > self.PIPE_SPAWN_INTERVAL:
            self.pipes.append(Pipe(WIN_WIDTH))
            self.pipe_timer = 0

        for pipe in self.pipes:
            pipe.update()
            if pipe.collide(self.bird):
                return self.get_state(), -1, True  # Collision with pipe, game over

        self.pipes = [pipe for pipe in self.pipes if pipe.x + pipe.width > 0]

        if self.bird.y + self.bird.height >= WIN_HEIGHT or self.bird.y <= 0:
            return self.get_state(), -1, True  # Bird hit ground or ceiling

        reward = 0
        for pipe in self.pipes:
            if not hasattr(pipe, "passed") and pipe.x + pipe.width < self.bird.x:
                pipe.passed = True
                self.score += 1
                reward = 1  # Reward for passing a pipe

        return self.get_state(), reward, False


    def get_state(self):
        """
        Returns the current state of the game as a processed image (grayscale and resized).

        :return: Processed state (grayscale and resized image)
        """
        # Capture the current screen state as an array
        state = pygame.surfarray.array3d(self.screen)

        # Convert to grayscale (just use the red channel)
        state = state[:, :, 0]  # Using the red channel for grayscale

        # Convert the numpy array to a pygame Surface
        state_surface = pygame.surfarray.make_surface(state)

        # Resize the surface to 84x84
        state_resized = pygame.transform.scale(state_surface, (84, 84))

        # Convert the resized surface back to a numpy array
        state_resized_array = pygame.surfarray.array3d(state_resized)

        # Convert it to grayscale by reducing the channels to 1
        state_resized_array = np.mean(state_resized_array, axis=2, keepdims=True)  # Convert to 1 channel (grayscale)

        # Convert the shape to match (batch_size, channels, height, width)
        state_resized_array = np.transpose(state_resized_array, (2, 0, 1))  # (1, 84, 84)

        # Convert to torch tensor
        state_resized_tensor = torch.tensor(state_resized_array, dtype=torch.float32)  # Convert to tensor

        return state_resized_tensor

    def render(self):
        """
        Renders the current game frame to the screen.
        """
        self.screen.fill((255, 255, 255))  # Clear the screen
        self.bird.draw(self.screen)
        for pipe in self.pipes:
            pipe.draw(self.screen)

        font = pygame.font.SysFont(None, 36)
        score_surface = font.render(f"Score: {self.score}", True, (0, 0, 0))
        self.screen.blit(score_surface, (10, 10))

        pygame.display.flip()


if __name__ == "__main__":
    """
    A simple loop to initialize the FlappyBird environment, reset it, 
    and start the environment for testing purposes.
    """
    env = FlappyBirdEnv()
    state = env.reset()  # Initialize the environment
    running = True

    while running:
        action = random.randint(0, 1)  # Example: Random action for testing (0 = Do Nothing, 1 = Flap)
        state, reward, done = env.step(action)  # Step with random action
        env.render()  # Show the game window

        if done:
            running = False

    pygame.quit()