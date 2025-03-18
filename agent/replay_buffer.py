import random
from collections import deque


class ReplayBuffer:
    """
    A class to store the agent's experiences for training.

    The ReplayBuffer stores state-action-reward-next_state tuples and allows
    for random sampling to break correlations between consecutive experiences.
    """

    def __init__(self, capacity):
        """
        Initializes the ReplayBuffer.
        :param capacity: The maximum number of experiences to store in the buffer.
        """
        self.buffer = deque(maxlen=capacity)

    def add(self, state, action, reward, next_state, done):
        """
        Adds a new experience to the buffer.
        :param state: The current state of the agent.
        :param action: The action taken by the agent.
        :param reward: The reward received after taking the action.
        :param next_state: The state of the environment after taking the action.
        :param done: A boolean indicating if the episode has finished.
        """
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        """
        Samples a random batch of experiences from the buffer.
        :param batch_size: The number of experiences to sample.
        :return: A list of experiences randomly selected from the buffer.
        """
        return random.sample(self.buffer, batch_size)

    def size(self):
        """
        Returns the current size of the buffer.
        :return: The number of experiences stored in the buffer.
        """
        return len(self.buffer)

    def clear(self):
        """
        Clears the buffer by removing all stored experiences.
        """
        self.buffer.clear()

