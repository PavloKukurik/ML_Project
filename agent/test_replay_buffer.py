import gym
import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
from collections import deque

# Гіперпараметри
GAMMA = 0.99
LR = 0.001
BATCH_SIZE = 32
EPSILON_START = 1.0
EPSILON_END = 0.05
EPSILON_DECAY = 500
TARGET_UPDATE = 10
MEMORY_SIZE = 10000
EPISODES = 500

# **1. Створюємо середовище**
env = gym.make("CartPole-v1")
state_dim = env.observation_space.shape[0]
action_dim = env.action_space.n


# **2. Визначаємо нейромережу**
class DQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim)
        )

    def forward(self, x):
        return self.fc(x)


# **3. Ініціалізація мережі та буфера відтворення**
policy_net = DQN(state_dim, action_dim)
target_net = DQN(state_dim, action_dim)
target_net.load_state_dict(policy_net.state_dict())
target_net.eval()

optimizer = optim.Adam(policy_net.parameters(), lr=LR)
memory = deque(maxlen=MEMORY_SIZE)


# **4. Функції вибору дії та навчання**
def select_action(state, epsilon):
    if random.random() < epsilon:
        return env.action_space.sample()  # Випадкова дія (exploration)
    else:
        with torch.no_grad():
            return policy_net(torch.FloatTensor(state)).argmax().item()  # Найкраща дія (exploitation)


def optimize_model():
    if len(memory) < BATCH_SIZE:
        return

    batch = random.sample(memory, BATCH_SIZE)
    states, actions, rewards, next_states, dones = zip(*batch)

    states = torch.FloatTensor(states)
    actions = torch.LongTensor(actions).unsqueeze(1)
    rewards = torch.FloatTensor(rewards)
    next_states = torch.FloatTensor(next_states)
    dones = torch.FloatTensor(dones)

    q_values = policy_net(states).gather(1, actions).squeeze(1)
    next_q_values = target_net(next_states).max(1)[0]
    expected_q_values = rewards + GAMMA * next_q_values * (1 - dones)

    loss = nn.MSELoss()(q_values, expected_q_values.detach())
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()


# **5. Запуск навчання**
epsilon = EPSILON_START
rewards_per_episode = []

for episode in range(EPISODES):
    state = env.reset()[0]
    total_reward = 0

    for t in range(500):
        action = select_action(state, epsilon)
        next_state, reward, done, _, _ = env.step(action)

        memory.append((state, action, reward, next_state, done))
        state = next_state
        total_reward += reward

        optimize_model()

        if done:
            break

    rewards_per_episode.append(total_reward)

    epsilon = max(EPSILON_END, epsilon - (EPSILON_START - EPSILON_END) / EPSILON_DECAY)

    if episode % TARGET_UPDATE == 0:
        target_net.load_state_dict(policy_net.state_dict())

    print(f"Episode {episode}, Total Reward: {total_reward}, Epsilon: {epsilon:.2f}")

env.close()

# **6. Візуалізація результату**
import matplotlib.pyplot as plt

plt.plot(rewards_per_episode)
plt.xlabel("Епізоди")
plt.ylabel("Загальна винагорода")
plt.title("Процес навчання DQN")
plt.show()
