"""
ClawForge Bot — Main entry point.
Wraps Freqtrade with ClawForge-specific customization.
"""

from pathlib import Path

from dotenv import load_dotenv

from clawforge.strategy import Claw5MSniper

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

__all__ = ["Claw5MSniper"]
