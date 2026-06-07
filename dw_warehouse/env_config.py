"""Configuration management for the warehouse.

Loads environment variables from .env file if it exists.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(env_file: Path | str | None = None) -> None:
    """Load environment variables from a .env file.
    
    Args:
        env_file: Path to .env file. If None, uses .env in current directory.
    """
    if env_file is None:
        env_file = Path(".env")
    else:
        env_file = Path(env_file)
    
    if not env_file.exists():
        return
    
    with env_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Parse KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value


# Auto-load .env on module import
try:
    load_env_file()
except Exception:
    pass
