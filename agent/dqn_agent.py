import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np


class DQNAgent:
    """
    A Deep Q-Network (DQN) agent that uses a CNN to process game frames and learn an optimal policy.

    The agent interacts with an environment and learns using the Q-learning algorithm.
    """

    def __init__(self, model, target_model, replay_buffer, epsilon=1.0, epsilon_min=0.1, epsilon_decay=0.995,
                 gamma=0.99, alpha=0.001):
        """
        Initializes the DQN agent.

        :param model: The Q-network (CNN model) used for predicting Q-values.
        :param target_model: The target Q-network used for calculating target Q-values.
        :param replay_buffer: The replay buffer used to store past experiences.
        :param epsilon: The exploration rate for the epsilon-greedy policy.
        :param epsilon_min: The minimum epsilon value for exploration.
        :param epsilon_decay: The rate at which epsilon decays over time.
        :param gamma: The discount factor for future rewards.
        :param alpha: The learning rate for training the model.
        """
        self.model = model
        self.target_model = target_model
        self.replay_buffer = replay_buffer
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.gamma = gamma
        self.alpha = alpha
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.alpha)

    def get_action(self, state):
        """
        Selects an action based on the epsilon-greedy policy.

        :param state: The current state of the environment.
        :return: The selected action (0 or 1).
        """
        if random.random() < self.epsilon:
            return random.randint(0, 1)  # Random action (exploration)
        else:
            with torch.no_grad():
                q_values = self.model(state)
                return torch.argmax(q_values).item()  # Action with highest Q value (exploitation)

    def decay_epsilon(self):
        """
        Decays epsilon over time to reduce exploration and increase exploitation.
        """
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def train_step(self, batch):
        """
        Performs one training step based on a batch of experiences.

        :param batch: A batch of experiences (state, action, reward, next_state, done).
        """
        states, actions, rewards, next_states, dones = zip(*batch)

        # Convert states and next_states from numpy arrays to torch tensors
        states = torch.tensor(np.array(states), dtype=torch.float32)
        next_states = torch.tensor(np.array(next_states), dtype=torch.float32)

        actions = torch.tensor(actions)
        rewards = torch.tensor(rewards)
        dones = torch.tensor(dones)

        # Get Q values for the current state and next state
        current_q_values = self.model(states)
        next_q_values = self.target_model(next_states)

        # Compute the target Q values using the Bellman equation
        target = rewards + self.gamma * torch.max(next_q_values, dim=1)[0] * (1 - dones.float())

        # Compute the loss
        loss = nn.MSELoss()(current_q_values.gather(1, actions.unsqueeze(1)).squeeze(1), target)

        # Perform backpropagation and update the model
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def update_target_model(self):
        """
        Updates the target model with the weights of the current model.
        """
        self.target_model.load_state_dict(self.model.state_dict())
