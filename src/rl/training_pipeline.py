"""
Maze Bourne - RL Training Pipeline
Train PPO agents using Stable-Baselines3
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stable_baselines3 import PPO, DQN
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import (
    EvalCallback, 
    CheckpointCallback,
    BaseCallback
)
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.env_checker import check_env

from src.rl.gym_env import MazeBourneEnv
from src.core.constants import RL_CONFIG


class TrainingCallback(BaseCallback):
    """Custom callback for logging training progress."""
    
    def __init__(self, log_freq: int = 1000, verbose: int = 1):
        super().__init__(verbose)
        self.log_freq = log_freq
        self.episode_rewards = []
        self.episode_lengths = []
    
    def _on_step(self) -> bool:
        if self.n_calls % self.log_freq == 0:
            if self.verbose > 0:
                print(f"Step: {self.n_calls}, "
                      f"Mean reward: {sum(self.episode_rewards[-100:]) / max(len(self.episode_rewards[-100:]), 1):.2f}")
        return True
    
    def _on_rollout_end(self) -> None:
        # Log episode statistics
        pass


def create_training_env(n_envs: int = 4, level_size: tuple = (15, 15)) -> DummyVecEnv:
    """Create vectorized training environment."""
    def make_env(seed: int):
        def _init():
            env = MazeBourneEnv(level_size=level_size, seed=seed)
            return env
        return _init
    
    envs = [make_env(i) for i in range(n_envs)]
    return DummyVecEnv(envs)


def train_ppo_agent(
    total_timesteps: int = None,
    n_envs: int = 4,
    save_path: str = "models/ppo_maze_bourne",
    level_size: tuple = (15, 15),
    learning_rate: float = 3e-4,
    verbose: int = 1
) -> PPO:
    """
    Train a PPO agent to play Maze Bourne.
    
    Args:
        total_timesteps: Total training steps (default from config)
        n_envs: Number of parallel environments
        save_path: Where to save the trained model
        level_size: Size of training levels
        learning_rate: Learning rate for PPO
        verbose: Verbosity level
    
    Returns:
        Trained PPO model
    """
    total_timesteps = total_timesteps or RL_CONFIG["training_timesteps"]
    
    print(f"[Training] Creating {n_envs} parallel environments...")
    env = create_training_env(n_envs=n_envs, level_size=level_size)
    
    print("[Training] Initializing PPO agent...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=verbose,
        tensorboard_log="./logs/tensorboard/"
    )
    
    # Create save directory
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else "models", exist_ok=True)
    
    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path="./models/checkpoints/",
        name_prefix="ppo_maze"
    )
    
    print(f"[Training] Starting training for {total_timesteps} steps...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, TrainingCallback()],
        progress_bar=True
    )
    
    # Save final model
    model.save(save_path)
    print(f"[Training] Model saved to {save_path}")
    
    env.close()
    return model


def evaluate_agent(
    model_path: str,
    n_episodes: int = 10,
    level_size: tuple = (15, 15),
    render: bool = False
) -> dict:
    """
    Evaluate a trained agent.
    
    Args:
        model_path: Path to saved model
        n_episodes: Number of evaluation episodes
        level_size: Size of evaluation levels
        render: Whether to render episodes
    
    Returns:
        Dictionary with evaluation metrics
    """
    print(f"[Eval] Loading model from {model_path}")
    model = PPO.load(model_path)
    
    env = MazeBourneEnv(
        level_size=level_size, 
        render_mode="human" if render else None
    )
    
    total_rewards = []
    episode_lengths = []
    wins = 0
    
    for ep in range(n_episodes):
        obs, info = env.reset()
        done = False
        ep_reward = 0
        ep_length = 0
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            ep_reward += reward
            ep_length += 1
            
            if render:
                env.render()
        
        total_rewards.append(ep_reward)
        episode_lengths.append(ep_length)
        if terminated and info.get("distance_to_exit", float("inf")) < 1:
            wins += 1
        
        print(f"  Episode {ep + 1}: reward={ep_reward:.2f}, length={ep_length}")
    
    env.close()
    
    results = {
        "mean_reward": sum(total_rewards) / len(total_rewards),
        "std_reward": (sum((r - sum(total_rewards)/len(total_rewards))**2 for r in total_rewards) / len(total_rewards)) ** 0.5,
        "mean_length": sum(episode_lengths) / len(episode_lengths),
        "win_rate": wins / n_episodes,
        "n_episodes": n_episodes
    }
    
    print(f"\n[Eval] Results:")
    print(f"  Mean Reward: {results['mean_reward']:.2f} ± {results['std_reward']:.2f}")
    print(f"  Mean Length: {results['mean_length']:.1f}")
    print(f"  Win Rate: {results['win_rate'] * 100:.1f}%")
    
    return results


def demo_agent(model_path: str, n_episodes: int = 3):
    """Run a visual demo of the trained agent."""
    print(f"[Demo] Loading model from {model_path}")
    model = PPO.load(model_path)
    
    env = MazeBourneEnv(level_size=(20, 20), render_mode="human")
    
    for ep in range(n_episodes):
        print(f"\n=== Episode {ep + 1} ===")
        obs, info = env.reset()
        done = False
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            env.render()
        
        print(f"Episode ended: reward={info.get('total_reward', 0):.2f}")
    
    env.close()


def verify_environment():
    """Verify the RL environment is compatible with SB3."""
    print("[Verify] Checking environment compatibility...")
    env = MazeBourneEnv(level_size=(15, 15))
    
    try:
        check_env(env, warn=True)
        print("[Verify] ✓ Environment passed all checks!")
        return True
    except Exception as e:
        print(f"[Verify] ✗ Environment check failed: {e}")
        return False
    finally:
        env.close()


def quick_train(timesteps: int = 10000):
    """Quick training for testing purposes."""
    print(f"[Quick Train] Training for {timesteps} steps...")
    
    env = create_training_env(n_envs=2, level_size=(12, 12))
    
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=512,
        batch_size=64,
        verbose=1
    )
    
    model.learn(total_timesteps=timesteps)
    model.save("models/quick_ppo")
    
    print("[Quick Train] Done! Model saved to models/quick_ppo")
    env.close()
    return model


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Maze Bourne RL Training")
    parser.add_argument("--mode", choices=["train", "eval", "demo", "verify", "quick"],
                        default="verify", help="Training mode")
    parser.add_argument("--model", type=str, default="models/ppo_maze_bourne",
                        help="Model path")
    parser.add_argument("--timesteps", type=int, default=100000,
                        help="Training timesteps")
    parser.add_argument("--episodes", type=int, default=10,
                        help="Evaluation episodes")
    
    args = parser.parse_args()
    
    if args.mode == "verify":
        verify_environment()
    elif args.mode == "quick":
        quick_train(args.timesteps)
    elif args.mode == "train":
        train_ppo_agent(total_timesteps=args.timesteps, save_path=args.model)
    elif args.mode == "eval":
        evaluate_agent(args.model, n_episodes=args.episodes)
    elif args.mode == "demo":
        demo_agent(args.model, n_episodes=args.episodes)
