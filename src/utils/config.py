import json
import os
from typing import Any, Dict, Optional

class ConfigManager:
    def __init__(self):
        self.config_path = 'data/config.json'
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default if not exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._create_default_config()
        return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration."""
        config = {
            'is_configured': False,
            'auto_lock_timeout': 300,  # 5 minutes in seconds
            'clipboard_timeout': 30,   # 30 seconds
            'theme': 'light',
            'password_generator': {
                'length': 16,
                'use_uppercase': True,
                'use_lowercase': True,
                'use_numbers': True,
                'use_special': True
            },
            'security': {
                'hash_algorithm': 'argon2id',
                'encryption_algorithm': 'aes-256-gcm'
            }
        }
        self._save_config(config)
        return config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def is_configured(self) -> bool:
        """Check if the application is configured."""
        return self._config.get('is_configured', False)
    
    def set_configured(self, value: bool = True):
        """Set the configured status."""
        self._config['is_configured'] = value
        self._save_config(self._config)
    
    def get_auto_lock_timeout(self) -> int:
        """Get the auto-lock timeout in seconds."""
        return self._config.get('auto_lock_timeout', 300)
    
    def set_auto_lock_timeout(self, timeout: int):
        """Set the auto-lock timeout in seconds."""
        self._config['auto_lock_timeout'] = timeout
        self._save_config(self._config)
    
    def get_clipboard_timeout(self) -> int:
        """Get the clipboard timeout in seconds."""
        return self._config.get('clipboard_timeout', 30)
    
    def set_clipboard_timeout(self, timeout: int):
        """Set the clipboard timeout in seconds."""
        self._config['clipboard_timeout'] = timeout
        self._save_config(self._config)
    
    def get_theme(self) -> str:
        """Get the current theme."""
        return self._config.get('theme', 'light')
    
    def set_theme(self, theme: str):
        """Set the application theme."""
        self._config['theme'] = theme
        self._save_config(self._config)
    
    def get_password_generator_settings(self) -> Dict[str, Any]:
        """Get password generator settings."""
        return self._config.get('password_generator', {
            'length': 16,
            'use_uppercase': True,
            'use_lowercase': True,
            'use_numbers': True,
            'use_special': True
        })
    
    def set_password_generator_settings(self, settings: Dict[str, Any]):
        """Set password generator settings."""
        self._config['password_generator'] = settings
        self._save_config(self._config)
    
    def get_security_settings(self) -> Dict[str, str]:
        """Get security settings."""
        return self._config.get('security', {
            'hash_algorithm': 'argon2id',
            'encryption_algorithm': 'aes-256-gcm'
        })
    
    def set_security_settings(self, settings: Dict[str, str]):
        """Set security settings."""
        self._config['security'] = settings
        self._save_config(self._config)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings."""
        return self._config.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self._config = self._create_default_config()
        self._save_config(self._config) 