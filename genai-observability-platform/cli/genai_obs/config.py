"""
CLI Configuration Management
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


CONFIG_DIR = Path.home() / ".genai-observability"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    """CLI configuration."""
    endpoint: str = "https://api.observability.example.com"
    api_key: str = ""
    default_output: str = "table"
    profile: str = "default"
    timeout: int = 30

    @classmethod
    def load(cls, profile: str = "default") -> "Config":
        """Load configuration from file."""
        if not CONFIG_FILE.exists():
            return cls(profile=profile)

        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)

            profiles = data.get('profiles', {})
            profile_data = profiles.get(profile, {})

            return cls(
                endpoint=profile_data.get('endpoint', cls.endpoint),
                api_key=profile_data.get('api_key', ''),
                default_output=profile_data.get('default_output', 'table'),
                profile=profile,
                timeout=profile_data.get('timeout', 30)
            )
        except Exception:
            return cls(profile=profile)

    def save(self):
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing config
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = {'profiles': {}}

        # Update profile
        data['profiles'][self.profile] = {
            'endpoint': self.endpoint,
            'api_key': self.api_key,
            'default_output': self.default_output,
            'timeout': self.timeout
        }

        # Save
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        # Set restrictive permissions
        CONFIG_FILE.chmod(0o600)


def get_config(profile: str = "default") -> Config:
    """
    Get configuration, checking environment variables first.
    """
    config = Config.load(profile)

    # Override with environment variables
    if os.environ.get('GENAI_OBS_ENDPOINT'):
        config.endpoint = os.environ['GENAI_OBS_ENDPOINT']

    if os.environ.get('GENAI_OBS_API_KEY'):
        config.api_key = os.environ['GENAI_OBS_API_KEY']

    return config
