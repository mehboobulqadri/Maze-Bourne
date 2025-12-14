# 🎮 Maze Bourne

A stealth-action maze game with AI and reinforcement learning.

## Prerequisites

- **Python 3.10+**

## Installation

1. Clone the repository (or extract files).
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run the game
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrows | Move |
| Shift | Stealth Mode |
| Space | Dash |
| E | Interact |
| ESC | Pause |
| F3 | Debug Mode |

## Features

- 🕵️ **Stealth Mechanics** - Avoid detection, use hiding spots
- ⚡ **Dash Ability** - Quick burst movement
- 🤖 **4 Enemy Types** - Patrol, Tracker, Sound Hunter, Sight Guard
- 🗺️ **Procedural Levels** - BSP-generated dungeons
- 🧠 **RL Integration** - Gymnasium-compatible environment

## AI Training

```bash
# Verify RL environment
python src/rl/training_pipeline.py --mode verify

# Quick training (10k steps)
python src/rl/training_pipeline.py --mode quick

# Full training
python src/rl/training_pipeline.py --mode train --timesteps 100000
```

## Project Structure

```
├── main.py              # Game entry point
├── src/
│   ├── ai/              # AI Logic
│   ├── core/            # Game engine
│   ├── entities/        # Player, enemies, objects
│   ├── graphics/        # Rendering
│   ├── levels/          # Maze generation
│   └── rl/              # Reinforcement learning
└── venv/                # Virtual environment
```