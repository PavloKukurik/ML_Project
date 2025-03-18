import torch
import random
import numpy as np
from agent.dqn_agent import DQNAgent
from agent.replay_buffer import ReplayBuffer
from environment.flappy_bird_env import FlappyBirdEnv
import torch.nn as nn


def train(agent, env, num_episodes=1000, batch_size=32):
    """
    The training loop for the DQN agent. The agent interacts with the environment, stores experiences,
    and updates its Q-network using the ReplayBuffer.

    :param agent: The DQN agent that interacts with the environment.
    :param env: The environment in which the agent operates.
    :param num_episodes: The total number of episodes to run during training.
    :param batch_size: The size of the batch to sample from the ReplayBuffer for each training step.
    """
    for episode in range(num_episodes):
        state = env.reset()  # Reset the environment at the start of each episode
        done = False
        total_reward = 0

        while not done:
            # Get the action from the agent (this is a simple exploration policy right now)
            action = agent.get_action(state)

            # Perform the action in the environment and get the next state and reward
            next_state, reward, done = env.step(action)

            # Store the experience in the replay buffer
            agent.replay_buffer.add(state, action, reward, next_state, done)

            # If there is enough data in the buffer, sample a batch for training
            if agent.replay_buffer.size() > batch_size:
                batch = agent.replay_buffer.sample(batch_size)
                agent.train_step(batch)  # Perform one training step with the batch

            # Update the state to the next state
            state = next_state
            total_reward += reward

        # Decay epsilon to reduce exploration over time
        agent.decay_epsilon()

        # Update the target model every few episodes
        if episode % 10 == 0:
            agent.update_target_model()

        print(f"Episode {episode}, Total Reward: {total_reward}, Epsilon: {agent.epsilon}")


if __name__ == "__main__":
    # Initialize the environment and the agent
    env = FlappyBirdEnv()  # FlappyBirdEnv is the environment we created earlier


    # Підрахунок розмірів вручну
    x = torch.randn(1, 1, 84, 84)  # Вхідне зображення
    x = nn.Conv2d(1, 32, kernel_size=8, stride=4)(x)  # Перший шар
    x = nn.Conv2d(32, 64, kernel_size=4, stride=2)(x)  # Другий шар
    print(x.size())  # Дивимося на розмір після двох Conv2d шарів

    # Використовуємо результат для Linear
    model = nn.Sequential(
        nn.Conv2d(1, 32, kernel_size=8, stride=4),
        nn.ReLU(),
        nn.Conv2d(32, 64, kernel_size=4, stride=2),
        nn.ReLU(),
        nn.Flatten(),
        nn.Linear(64 * 9 * 9, 512),  # Використовуємо 5184 як кількість входів після двох Conv2d
        nn.ReLU(),
        nn.Linear(512, 2)
    )

    target_model = model
    replay_buffer = ReplayBuffer(capacity=10000)

    # Initialize the agent (you can use random actions or start training)
    agent = DQNAgent(model=model, target_model=target_model, replay_buffer=replay_buffer)

    # Start training the agent (for testing purposes we may set a smaller number of episodes)
    train(agent, env, num_episodes=100)
