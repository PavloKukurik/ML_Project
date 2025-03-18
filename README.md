# 🕹️ RL Agent for Flappy Bird

## 📌 Project Overview
This project builds a **Reinforcement Learning (RL) Agent** to play **Flappy Bird**.  
The agent learns how to play the game by using **Deep Q-Learning (DQN)** and **Convolutional Neural Networks (CNN)**.  
It uses **raw images** from the game screen as input and improves its actions by **trial and error**.  
No rules are programmed — the agent learns by **reward and punishment**.

---

## 🌟 Project Goal
- Teach an agent to **survive** in the Flappy Bird game.
- Use **images** (pixels) from the game as input.
- Train with **Deep Q-Network (DQN)**.
- Evaluate how well the agent learns over time.

---

## ⚙️ Project Structure
```
ML_Project/
🔺️ environment/               
🔺️ 🔺 flappy_bird_game.py       # The game logic with Pygame
🔺️ preprocessing/
🔺️ 🔺 preprocess.py             # Convert raw images for the agent
🔺️ agent/
🔺️ 🔺 cnn_model.py              # CNN model for image processing
🔺️ 🔺 replay_buffer.py          # Memory buffer for past experiences
🔺️ 🔺 dqn_agent.py              # DQN agent logic (policy, learning)
🔺️ train.py                      # Training loop
🔺️ evaluate.py                   # Run the trained agent and see results
🔺️ utils/
🔺️ 🔺 plot_utils.py             # Plotting rewards and metrics
🔺️ outputs/
🔺️ 🔺 logs/                     # Training logs
🔺️ 🔺 models/                   # Saved models
🔺️ 🔺 gameplay_videos/          # Videos of the agent playing
🔺️ README.md                     # Project description and instructions
```

---

## 🚀 How It Works
### 1. Game Environment
- Built with **Pygame**.
- The game gives a **screen image** (frame) as the current state.
- Two actions:
  - `Flap` (go up)
  - `Do nothing` (fall down)

### 2. Data Preprocessing
- Get **frames** from the screen.
- Convert to **grayscale** (black and white).
- **Resize** images to 84x84 pixels.
- **Normalize** pixel values (0 to 1).
- Stack **4 frames** to understand motion (frame stacking).

### 3. RL Agent (Deep Q-Learning)
- Uses a **CNN** to process image inputs.
- Chooses actions with **ε-greedy policy**:
  - Sometimes explore (random action).
  - Sometimes exploit (best known action).
- Learns from experience with **Replay Buffer**.
- Updates action values (Q-values) using **Q-Learning**.

### 4. Training Process
- Agent plays the game.
- Collects experience (state, action, reward, next state).
- Learns from batches of past experiences.
- Gets **rewards**:
  - `+1` for passing a pipe.
  - `-1` for crashing.
- Over time, the agent **improves** its score.

---

## 📊 Results (Expected)
- **Rewards** increase during training.
- The agent learns to **fly longer** and **pass pipes**.
- We track:
  - Rewards per episode.
  - Epsilon decay (less exploration over time).

---

## 💡 Challenges
- **Sparse rewards** (agent gets feedback only when it crashes or passes a pipe).
- Balance **exploration** and **exploitation**.
- Sensitivity to **hyperparameters** (learning rate, gamma, etc.).

---

## ✅ How To Run
### 1. Clone the repository
```bash
git clone https://github.com/yourusername/RL-FlappyBird.git
cd RL-FlappyBird
```

### 2. Install requirements
```bash
pip install -r requirements.txt
```

### 3. Start training
```bash
python train.py
```

### 4. Run the trained agent
```bash
python evaluate.py
```

---

## 🔧 Requirements
- Python 3.8+
- Pygame
- PyTorch
- NumPy
- OpenCV (for preprocessing)
- Matplotlib (for plotting)

---

## 🎥 Progress Video (Interim Report)
The video shows:
1. The **problem statement** and why it’s hard.
2. The **game environment** and **input data** (frames).
3. Preprocessing pipeline and CNN structure.
4. Plans for **training** and next steps.

📌 Link: [Google Drive / YouTube](#)

---

## 🔮 Future Improvements
- Use **LSTM** to remember more steps.
- Try **curiosity-driven exploration**.
- Apply to other games (like **Chrome Dino Game**).

---

## ✨ Authors
- Pavlo Kukurik
- Sviatoslav Sharak

